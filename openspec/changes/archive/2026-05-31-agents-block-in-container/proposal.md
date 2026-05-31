## Why

Agents 页面保留 Card 容器（改名为 "Mercedes-Benz Agents"），但内部的三个 Agent 从列表行条目改为独立的 block 块，每个 block 有更明显的卡片感（padding、边框、独立视觉空间）。

## What Changes

- Card 标题从 "OpenStar Agents" 改为 "Mercedes-Benz Agents"（i18n）
- CardContent 内部的 agent 列表从紧凑行改为 block 布局：每个 agent 独立成块，使用更大的 padding 和更明显的视觉分隔
- 布局仍在 Card 容器内，不破坏外层结构

## Capabilities

### New Capabilities
- `agents-block-style`: Agent 条目从行样式改为 block 样式，容器标题改为 "Mercedes-Benz Agents"

### Modified Capabilities
<!-- None -->

## Impact

- `web/src/pages/AgentsPage.tsx` — block 样式调整
- `web/src/i18n/en.ts` + `zh.ts` — 标题 key 值更改
