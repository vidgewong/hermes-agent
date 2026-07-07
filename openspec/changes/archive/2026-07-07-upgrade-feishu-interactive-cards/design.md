## Context

Hermes 飞书适配器当前的交互能力：
- **审批卡**: 有交互卡片（硬编码 JSON），支持按钮点击和原地替换
- **Clarify/AskUser**: 使用 `BasePlatformAdapter.send_clarify` 的文本回退实现——编号列表，用户手打数字回复
- **进度**: emoji reaction（Typing → 完成/失败），无流式内容预览
- **卡片架构**: 无抽象层，`send_exec_approval` 直接拼接 JSON dict

参考对象 [cc-connect](https://github.com/chenhg5/cc-connect)（Go）的关键模式：
- 平台无关的 `core.Card` 数据模型 + fluent builder
- Feishu 渲染层把 Card IR 转为 Schema 1.0 interactive card JSON
- 流式卡片使用 Schema 2.0 + CardKit v1 API（`/open-apis/cardkit/v1/cards`）
- 按钮 value 用前缀路由（`perm:allow`、`askq:0:1`、`nav:/path`、`cmd:/command`）
- 回调后原地替换卡片为确认状态

## Goals / Non-Goals

**Goals:**
- AskUser/Clarify 用飞书交互卡片渲染（蓝色头 + ListItem 选项按钮 + 点击后原地确认）
- 流式进度卡片，显示 agent 正在做什么（tool 调用面板、流式文本输出、状态头颜色）
- 引入轻量卡片抽象层，使现有审批卡和新卡片共享构建逻辑
- 不破坏现有文本回退路径——非飞书平台继续用基类文本实现

**Non-Goals:**
- 不实现表单能力（checker 多选 + submit）——后续迭代
- 不实现导航/命令卡片（`nav:`/`cmd:` 路由）——当前无使用场景
- 不重写 Telegram/Discord 适配器——只改飞书
- 不改变 clarify 协议本身——只改渲染层

## Decisions

### 1. 卡片数据模型：Python dataclass IR（参考 cc-connect 的 `core.Card`）

引入 `gateway/cards.py`，定义平台无关的卡片中间表示：

```python
@dataclass
class InteractiveCard:
    header: CardHeader
    elements: list[CardElement]

@dataclass
class CardHeader:
    title: str
    color: str  # blue, green, red, orange, ...

# 元素类型（Union / tagged）
CardElement = CardMarkdown | CardDivider | CardActions | CardListItem | CardNote

@dataclass
class CardButton:
    text: str
    type: str  # "primary" | "default" | "danger"
    value: str  # 回调 action 标识，如 "askq:0:1"
    extra: dict[str, str] | None = None
```

提供 builder 方法链（类似 cc-connect 的 `NewCard().Title(...).Markdown(...).Build()`）。

**Rationale**: 直接复用 cc-connect 验证过的数据模型，Python dataclass 比 dict 有类型安全，builder 对构建复杂卡片更自然。不做完全泛型的平台抽象——目前只有飞书需要卡片渲染。

### 2. 飞书卡片渲染器：Card IR → Feishu JSON

在飞书适配器内新增 `_render_card_to_feishu(card: InteractiveCard, session_key: str) -> dict`：

- `CardMarkdown` → `{"tag": "markdown", "content": ...}`
- `CardDivider` → `{"tag": "hr"}`
- `CardActions` (row) → `{"tag": "action", "actions": [buttons]}`
- `CardActions` (equal_columns) → `{"tag": "column_set", "flex_mode": "bisect", ...}`
- `CardListItem` → `{"tag": "column_set", columns: [text_col(weight:5), btn_col(auto)]}`
- `CardNote` → `{"tag": "note", "elements": [...]}`
- 每个按钮的 `value` 字段注入 `session_key` 用于回调路由

**Rationale**: 渲染逻辑内聚在飞书适配器中，card IR 保持平台无关。session_key 注入解决回调归属问题（cc-connect 同样做法）。

### 3. AskUser 卡片：override `send_clarify`

飞书适配器 override `send_clarify`：
- **单选**: 蓝色头 + question markdown + ListItem（每个 option 一行，描述+按钮）+ Note
- **开放式**: 蓝色头 + question markdown + Note（"请直接回复"）
- 按钮 value: `clarify:{clarify_id}:{choice_index}`（对齐 cc-connect 的 `askq:qIdx:optIdx`）
- 点击后通过 `_on_card_action_trigger` 路由，调用 `resolve_gateway_clarify(clarify_id, response)` 并原地替换为绿色确认卡

回调路由在 `_on_card_action_trigger` 中增加 `clarify:` 前缀分支（和已有的 `hermes_action` 并存）。

### 4. 流式进度卡片：Schema 2.0 + CardKit v1

引入 `FeishuStreamCard` 状态机（参考 cc-connect 的 `feishuPreviewHandle`）：

```python
class FeishuStreamCard:
    card_id: str | None      # CardKit v1 创建后获得
    message_id: str | None   # 消息发送后获得
    sequence: int            # 流式更新单调递增
    status: CardStatus       # thinking → working → done/error
    element_id: str = "main_text"  # 流式文本锚点
```

生命周期：
1. Agent turn 开始 → 创建 Schema 2.0 卡片（`streaming_mode: true`），`POST /cardkit/v1/cards` 获取 card_id
2. 发送消息（card_id 引用）
3. 流式更新：`PUT /cardkit/v1/cards/{card_id}/elements/{element_id}/content`（节流：1.5s 间隔或 30 字符增量）
4. Tool 调用 → 更新 collapsible_panel 内容（通过 PATCH card JSON）
5. Turn 结束 → header 变绿，最终内容固定

**Rationale**: CardKit v1 是飞书官方的流式卡片方案，cc-connect 已验证可行。节流参数取 cc-connect 默认值（1500ms / 30 chars）。卡片大小上限 28KB（cc-connect 经验值），超限时降级为纯 markdown 卡片。

### 5. 回调 action 前缀路由

统一 `_on_card_action_trigger` 的分发逻辑：

| 前缀 | 处理 |
|------|------|
| `hermes_action` (legacy key) | 现有审批流程 |
| `perm:` | 新式审批（迁移后） |
| `clarify:` | AskUser 选项选择 |
| `stream:` | 流式卡片内交互（如"停止生成"） |

保持向后兼容：现有 `hermes_action` key 继续工作，新卡片使用 `action` key + 前缀。

### 6. 审批卡迁移

`send_exec_approval` 改为使用 Card IR builder：

```python
card = InteractiveCard.builder() \
    .title("⚠️ Command Approval Required", "orange") \
    .markdown(f"```\n{cmd_preview}\n```\n**Reason:** {description}") \
    .actions_equal([allow_btn, deny_btn]) \
    .actions([session_btn, always_btn]) \
    .note("Reply allow/deny or click a button") \
    .build()
```

功能不变，只是消除硬编码 JSON。

## Risks / Trade-offs

- **CardKit v1 API 权限** → 需要确认飞书应用已开通 `cardkit:card` 权限范围。Mitigation: 流式卡片作为可选能力，缺权限时降级为普通 interactive card + 定时 PATCH 更新。
- **lark-oapi 版本** → CardKit v1 可能需要较新版本的 SDK。Mitigation: 如 SDK 不支持，直接用 HTTP client 调用 REST API（cc-connect 也是裸 HTTP 调用）。
- **卡片大小 28KB 限制** → 长对话流式卡片可能超限。Mitigation: 采用 cc-connect 的渐进压缩策略（缩减 tool panel 条目数 → 截断文本 → 降级纯文本卡片）。
- **回调超时** → 飞书卡片回调要求 3s 内响应。Mitigation: 回调处理保持轻量（resolve + 返回替换卡片 JSON），不做异步等待。
- **向后兼容** → 现有 `hermes_action` 字段的审批卡可能还有未消费的 pending 消息。Mitigation: `_on_card_action_trigger` 同时支持旧格式和新前缀格式，平滑过渡。
