## Why

OpenStar 需要将三个业务专属 Agent（MB-REQ Agent、MB-Test Agent、MB-Arch Agent）作为独立的可视化入口展示在 Hermes Dashboard 中。这些 Agent 是企业级数字员工的核心能力，用户需要能直观地看到它们、了解其状态，并快速进入对话。与普通 Skills 不同，这些 Agent 需要独立审批流程来管理 Skill 和 Memory 的更新，因此需要一个专属的独立页面而非混在 Sessions 中。

## What Changes

- 在 Dashboard 侧边栏菜单中新增一个 "Agents" 导航项，位置在 Sessions 下方
- 新增独立的 Agents 页面（`/agents` 路由），展示三个业务 Agent（MB-REQ、MB-Test、MB-Arch）
- 每个 Agent 卡片显示名称、描述、状态指示器、最近活跃时间
- 页面样式保持与 Hermes 现有 Dashboard 风格一致（使用 `@nous-research/ui` 组件库，保持暗色主题、mondwest 字体等）
- Agent 卡片可点击，进入该 Agent 的对话界面
- Agent 数据通过后端 API 获取，包含 Agent 元数据和状态信息

## Capabilities

### New Capabilities
- `openstar-agents-page`: Dashboard 独立的 Agents 页面，包含侧边栏导航项和页面路由，展示 OpenStar 三个业务 Agent 的状态、描述和快捷入口
- `openstar-agents-api`: 后端 API 端点提供 OpenStar Agent 的元数据和运行状态信息

### Modified Capabilities
<!-- No existing capabilities are being modified at the spec level -->

## Impact

- **前端路由**: `web/src/App.tsx` — 新增 `/agents` 路由和侧边栏导航项（在 Sessions 之后）
- **前端页面**: 新增 `web/src/pages/AgentsPage.tsx`
- **后端 API**: 新增 `/api/openstar/agents` 端点返回 Agent 列表和状态
- **国际化**: `web/src/i18n/` 中新增相关翻译 key
- **依赖**: 无新外部依赖，复用现有 `@nous-research/ui` 组件库
