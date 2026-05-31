## Why

Agents 页面当前使用垂直列表布局（一行一个 Agent），视觉上不够突出。改为 block/card grid 布局，每个 Agent 占据一个独立的块，更直观地展示信息。

## What Changes

- 将 AgentsPage 中 CardContent 内的 Agent 列表从 `grid gap-3`（单列垂直列表）改为响应式网格布局（如 `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`）
- 每个 Agent 以独立的 Card block 形式呈现，而非行条目
- 移除外层包裹的 Card 容器，让每个 Agent 自己就是一个 Card
- 保持展开详情面板的交互不变

## Capabilities

### New Capabilities
- `agents-block-layout`: Agents 页面从列表布局改为网格 block 布局

### Modified Capabilities
<!-- None -->

## Impact

- **前端**: `web/src/pages/AgentsPage.tsx` — 布局结构调整
