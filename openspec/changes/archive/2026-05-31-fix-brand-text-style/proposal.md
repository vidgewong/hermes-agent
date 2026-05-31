## Why

Dashboard 侧边栏左上角品牌名当前显示为 "Open\nStar"（带换行且全大写 `uppercase`），需要改为单行显示 "OpenStar"，不使用全大写。

## What Changes

- 移除品牌文字中的 `<br />`，改为单行 "OpenStar"
- 移除 Typography 组件上的 `uppercase` class，保留原始大小写

## Capabilities

### New Capabilities
- `fix-brand-display`: 修正侧边栏品牌文字为单行非全大写的 "OpenStar"

### Modified Capabilities
<!-- None -->

## Impact

- **前端**: `web/src/App.tsx` — 侧边栏品牌 Typography 组件
