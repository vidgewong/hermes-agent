## Context

当前 AgentsPage 用一个 Card 包裹所有 Agent，CardContent 内用 `grid gap-3` 做垂直列表。要改为每个 Agent 独立成 block。

## Goals / Non-Goals

**Goals:**
- 每个 Agent 独立为一个 block/card，不再共享外层 Card
- 响应式网格：移动端 1 列，中等屏幕 2 列，大屏 3 列
- 展开详情时 block 扩展为全宽（跨列），保持内容可读性

**Non-Goals:**
- 不改变详情面板内容

## Decisions

移除外层 `<Card><CardHeader><CardContent>` 包裹，改为直接在页面 div 中用 `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` 布局。每个 agent block 使用现有的 border + transition 样式。展开时加 `sm:col-span-2 lg:col-span-3` 全宽。
