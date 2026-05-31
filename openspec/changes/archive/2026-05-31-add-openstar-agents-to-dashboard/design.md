## Context

Hermes Dashboard 侧边栏当前有 Sessions、Analytics、Models、Logs 等导航项。我们需要在 Sessions 下方新增一个独立的 "Agents" 导航项，点击后进入一个专属的 Agents 页面，展示三个 OpenStar 业务 Agent。

现有技术栈：
- 前端: React + TypeScript, `@nous-research/ui` 组件库, Tailwind CSS, lucide-react 图标
- 路由: react-router-dom，路由定义在 `App.tsx` 的 `BUILTIN_ROUTES_CORE` 和 `BUILTIN_NAV_REST`
- API 模式: `web/src/lib/api.ts` 中的 `fetchJSON` 封装
- 页面模式: 各页面在 `web/src/pages/` 下，通过路由表注册
- 国际化: `useI18n()` hook

## Goals / Non-Goals

**Goals:**
- 在侧边栏新增 "Agents" 导航项，位置在 Sessions 之后
- 新增 `/agents` 路由对应独立的 AgentsPage
- 页面内展示 MB-REQ、MB-Test、MB-Arch 三个 Agent 卡片
- 提供 Agent 状态信息（online/busy/offline）
- 点击 Agent 卡片可进入对话
- 后端 API 提供 Agent 元数据

**Non-Goals:**
- 不实现 Skill/Memory 的审批流程 UI（后续迭代）
- 不实现 Agent 的详细配置管理界面
- 不实现 Agent 的创建/删除功能（三个 Agent 为固定配置）
- 不修改现有 Sessions 页面

## Decisions

### 1. 路由和导航注册 — 在 App.tsx 中 Sessions 后插入

**决定**: 在 `BUILTIN_ROUTES_CORE` 中添加 `"/agents": AgentsPage`，在 `BUILTIN_NAV_REST` 中 Sessions 项之后插入 Agents 导航项。

**理由**: 遵循现有模式，所有内置页面都在这两个常量中注册。位置在 Sessions 后面符合业务逻辑（Agent 是核心功能，仅次于会话管理）。

**替代方案**: 用 plugin 机制注入 — 但三个固定 Agent 是平台核心功能而非插件扩展，不应走插件注册路径。

### 2. 页面组件 — 独立 AgentsPage.tsx

**决定**: 创建 `web/src/pages/AgentsPage.tsx`，采用与 SessionsPage Overview 类似的卡片布局风格。

**理由**: 独立页面给 Agent 更大的展示空间，且与 Sessions 页面解耦，未来可独立扩展（如加入审批、配置等功能）。

### 3. Agent 图标 — 使用 lucide-react 中的 Bot 图标作为导航图标

**决定**: 导航项使用 `Bot` 图标（lucide-react），各 Agent 卡片内使用不同颜色区分。

**理由**: `Bot` 图标直观表达 "智能体" 概念，lucide-react 已在项目中广泛使用。

### 4. 数据获取 — `/api/openstar/agents` + 页面内轮询

**决定**: AgentsPage 内部发起 API 请求获取 agents 数据，5s 轮询刷新状态。

**理由**: 与 SessionsPage 的 overview 数据加载模式一致，Agent 状态需要实时反映。

### 5. 点击交互 — 导航到 Chat 页面

**决定**: 点击 Agent 卡片导航到 `/chat?agent=<agent-id>`。若 embedded chat 未开启则不可点击。

**理由**: 复用现有 embedded chat 基础设施。

## Risks / Trade-offs

- **[Agent 进程管理未实现]** → V1 阶段 Agent 状态可能为静态配置返回，后续迭代连接真实 Agent 进程
- **[硬编码三个 Agent]** → 后端 API 返回固定列表，后续支持动态注册时只需修改数据源，API 接口不变
- **[Chat 页面 Agent 切换]** → 依赖 embedded chat 功能已开启，若未开启则点击无效果
- **[侧边栏空间]** → 新增一个导航项增加侧边栏密度，但 Agents 是核心功能，值得占据独立位置
