## Why

项目正在从 Hermes 逐步转型为面向企业的数字员工平台 OpenStar。Dashboard 中所有面向用户的品牌标识需要统一切换为 "OpenStar"。同时，Agents 页面当前的点击交互（直接跳转 Chat）过于简单，用户需要先查看 Agent 的详细信息（模型、状态、当前任务等），再通过明确的操作进入与 Agent 的对话，且对话中需自动派发任务给对应的 sub agent。

## What Changes

- Dashboard 品牌从 "Hermes Agent" 切换为 "OpenStar"（侧边栏标题、移动端 header、页面标题等）
- "Update Hermes" 系统操作更名为 "Update OpenStar"
- Agents 页面中 Agent 卡片点击改为展开/跳转到 Agent 详情视图，展示：
  - 当前使用的 Model
  - Agent 状态（online/busy/offline）
  - 当前正在执行的任务/操作
  - 最近活动历史
- Agent 详情视图中提供 "Chat" 按钮，点击跳转到 `/chat`，并自动在输入框中预填 `/<agent-command>` 格式的 slash command，用于明确派发任务给对应 sub agent
- 后端 API 扩展，返回更丰富的 Agent 运行时信息（model、current_task 等）

## Capabilities

### New Capabilities
- `dashboard-rebrand-openstar`: 将 Dashboard 中所有用户可见的 "Hermes" 品牌切换为 "OpenStar"
- `agent-detail-view`: Agents 页面的 Agent 详情视图，展示模型、状态、当前任务，以及带 slash command 预填的 Chat 入口

### Modified Capabilities
<!-- No existing specs are being modified -->

## Impact

- **前端品牌**: `web/src/i18n/*.ts` 中 `brand`、`updateHermes` 等 key，`web/src/App.tsx` 中硬编码的 "Hermes" 文字
- **前端页面**: `web/src/pages/AgentsPage.tsx` — 从简单列表改为带详情展开/面板的视图
- **后端 API**: `/api/openstar/agents` — 扩展返回字段（model、current_task、recent_actions）
- **Chat 集成**: Chat 页面需支持通过 URL 参数预填 slash command
- **国际化**: 所有 locale 文件中的品牌相关文本
