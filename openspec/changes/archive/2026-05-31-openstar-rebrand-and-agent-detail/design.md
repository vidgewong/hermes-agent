## Context

当前 Dashboard 品牌为 "Hermes Agent"，在侧边栏、移动端 header、系统操作按钮中显示。项目正向 OpenStar 转型。同时，已实现的 AgentsPage 当前是简单卡片列表，点击直接跳转 Chat。需要改为展开详情 + 明确的 Chat 入口。

技术栈不变：React + TypeScript, `@nous-research/ui`, react-router-dom, FastAPI backend。

## Goals / Non-Goals

**Goals:**
- 将所有用户可见的 "Hermes" 替换为 "OpenStar"（i18n keys + 硬编码文字）
- AgentsPage 中点击 Agent 展开详情面板（inline expand，类似 SessionsPage 展开消息的模式）
- Agent 详情展示: model、status、current_task、recent_actions
- 详情面板中提供 "Start Chat" 按钮，跳转到 `/chat?command=/<agent-slash-command>`
- Chat 页面读取 `command` URL 参数后自动在输入框中预填该 slash command
- 后端 `/api/openstar/agents` 扩展返回更多字段

**Non-Goals:**
- 不修改底层 CLI 的 "hermes" 命令名称（仅改 Dashboard UI 文字）
- 不修改文件路径或 Python 模块名中的 "hermes"
- 不实现 Agent 的实时 WebSocket 状态推送
- 不修改 Chat 组件的核心逻辑（仅添加 URL 参数预填）

## Decisions

### 1. 品牌切换范围 — 仅限 Dashboard UI 文字

**决定**: 只修改 i18n 文件中的 `brand`、`brandShort`、`updateHermes`、`updatingHermes` 以及 App.tsx 中硬编码的 "Hermes\nAgent" 文字。不改动文件路径、模块名、CLI 命令名。

**理由**: 逐步切换策略。文件路径和 CLI 命令的重命名是破坏性变更，需要单独的迁移计划。用户面向的 UI 文字可以先切换。

### 2. Agent 详情视图 — Inline Expand 模式

**决定**: 在 AgentsPage 中，点击 Agent 卡片后在卡片下方展开详情面板（与 SessionsPage 的 `SessionRow` 展开消息模式一致）。不使用独立的详情页路由。

**理由**: 三个 Agent 固定数量，不需要独立路由。Inline expand 保持页面简洁，且用户一个人内就能看完所有 Agent 状态。复用已建立的交互模式，降低学习成本。

**替代方案**: 独立 `/agents/:id` 路由 — 对于仅 3 个 Agent 过于复杂。

### 3. Slash Command 预填 — URL 参数传递

**决定**: Agent 详情中的 "Start Chat" 按钮导航到 `/chat?command=/mb-req`（举例）。ChatPage 读取 `command` 参数后设置到输入框中（不自动发送，让用户确认后发送）。

**理由**: 预填但不自动发送，给用户追加上下文的机会。slash command 格式与现有 skill 派发机制一致。

**Slash command 映射**:
- MB-REQ Agent → `/mb-req`
- MB-Test Agent → `/mb-test`
- MB-Arch Agent → `/mb-arch`

### 4. 后端 API 扩展 — 增加运行时字段

**决定**: `/api/openstar/agents` 每个 agent 对象新增 `model`、`current_task`、`recent_actions` 字段。V1 阶段 model 为固定配置值，current_task 和 recent_actions 默认为空。

**理由**: 为 UI 提供展示数据。V1 阶段先返回静态/空值，后续迭代接入真实 Agent 运行时数据时只需修改数据源。

## Risks / Trade-offs

- **[ChatPage command 预填]** → 需要了解 ChatPage 的输入框 API。如果 embedded chat 使用 xterm/PTY，预填可能需要通过 WebSocket 写入。若太复杂则降级为 URL 参数跳转后在 Chat 上方显示提示文案。
- **[品牌不完全一致]** → CLI 仍叫 "hermes"，Dashboard 已叫 "OpenStar"。短期内可接受，后续统一。
- **[Agent 详情数据为空]** → V1 current_task/recent_actions 为空，UI 需优雅处理空状态。
