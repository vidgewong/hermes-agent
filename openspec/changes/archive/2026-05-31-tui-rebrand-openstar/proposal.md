## Why

TUI（终端界面）中多处仍显示 "Hermes" 品牌名，需要统一切换为 "OpenStar"，保持与 Dashboard 品牌一致。用户在终端中使用时看到的应该是 OpenStar 而非 Hermes。

## What Changes

- TUI 启动 ASCII art banner 从 "HERMES AGENT" 换为 "OPENSTAR" 样式
- Theme 中 `brand.name` 从 "Hermes Agent" 改为 "OpenStar"
- 终端标题 fallback 从 "Hermes" 改为 "OpenStar"
- Slash command help 文本中 "Hermes Agent" → "OpenStar"
- 对话历史标签 "Hermes #N" → "OpenStar #N"
- Setup 提示文本 "Hermes needs a model provider" → "OpenStar needs a model provider"

## Capabilities

### New Capabilities
- `tui-rebrand`: 将 TUI 中所有用户可见的 "Hermes" 品牌文字替换为 "OpenStar"

### Modified Capabilities
<!-- None -->

## Impact

- **TUI**: `ui-tui/src/banner.ts` — ASCII art logo
- **TUI**: `ui-tui/src/theme.ts` — brand name
- **TUI**: `ui-tui/src/app/useMainApp.ts` — terminal title
- **TUI**: `ui-tui/src/app/slash/commands/core.ts` — help text + history labels
- **TUI**: `ui-tui/src/content/setup.ts` — setup prompt
- **不修改**: CLI Python 代码中的 "Hermes" 引用（大多为内部注释或 auth 消息，后续单独处理）
