## Why

Hermes 的飞书交互体验落后于 cc-connect：AskUser/clarify 退化为纯文本编号列表，流式输出无卡片预览，缺少通用卡片抽象层导致扩展困难。升级飞书交互卡片系统可以显著提升用户体验——用户无需手打数字即可完成选择，实时看到 agent 思考和工具调用过程，且后续新卡片类型可快速扩展。

## What Changes

- 引入平台无关的 `InteractiveCard` 抽象模型，支持 Markdown、Divider、Actions（按钮组）、ListItem、Select、Note 等元素类型
- 飞书适配器 override `send_clarify`，将 AskUser/clarify 渲染为蓝色交互卡片（ListItem 布局 + 按钮选择），点击后原地替换为绿色确认卡
- 引入流式进度卡片，使用飞书 Card Schema 2.0 的 `streaming_mode` + CardKit v1 API 实现打字机效果，tool 调用显示在可折叠面板中
- 升级现有审批卡（`send_exec_approval`）使用新的卡片抽象层，消除硬编码 JSON
- 在 `BasePlatformAdapter` 中定义 `CardSender` 协议，使其他平台适配器也可复用卡片逻辑

## Capabilities

### New Capabilities
- `interactive-card-model`: 平台无关的交互卡片数据模型和 builder API（元素类型、按钮回调路由、卡片原地更新协议）
- `feishu-askuser-card`: 飞书平台的 AskUser/clarify 交互卡片实现（蓝色卡片 + ListItem 选项 + 点击回调 + 确认替换）
- `feishu-streaming-progress`: 飞书平台的流式进度卡片（Card 2.0 streaming_mode、可折叠面板、状态头颜色变化、CardKit v1 增量更新）

### Modified Capabilities
（无现有 spec 需要修改——审批卡重构是内部实现变化，不改变外部行为）

## Impact

- `plugins/platforms/feishu/adapter.py` — 主要改动文件：override send_clarify、新增流式卡片发送、重构审批卡
- `gateway/platforms/base.py` — 新增 CardSender 协议和 InteractiveCard 模型
- 飞书 API 依赖 — 需要 CardKit v1 API（`/open-apis/cardkit/v1/cards`）权限，需确认应用权限配置
- `lark-oapi` SDK — 需确认版本支持 Card Schema 2.0 和 streaming_mode
- 卡片回调路由 — `_on_card_action_trigger` 需要扩展以处理新的 action 前缀（`askq:`、`nav:`）
