## Context

`web/src/App.tsx` 中侧边栏品牌文字当前为：
```tsx
<Typography className="... uppercase">
  Open
  <br />
  Star
</Typography>
```

需要改为单行且不全大写。

## Goals / Non-Goals

**Goals:**
- 品牌文字显示为 "OpenStar" 单行
- 移除 `uppercase` 使文字保持原始大小写

**Non-Goals:**
- 不修改移动端 header 中的品牌（那里用的是 `t.app.brand`）

## Decisions

直接修改 App.tsx 中的 Typography 内容和 className。
