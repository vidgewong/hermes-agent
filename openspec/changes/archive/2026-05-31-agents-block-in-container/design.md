## Context

当前 AgentsPage 有 Card 包裹，CardContent 内用 `grid gap-3` 做列表，每个 agent 是一行。需要改为 block 样式。

## Goals / Non-Goals

**Goals:**
- 容器标题改为 "Mercedes-Benz Agents"
- CardContent 内改为 grid 网格布局（`grid-cols-1 sm:grid-cols-3 gap-4`），每个 agent 是一个独立 block
- 每个 block 有更丰富的内容展示（图标居中/更大、名称突出）
- 展开时 block 跨满整行

**Non-Goals:**
- 不改外层 Card 容器结构
- 不改详情面板内容
