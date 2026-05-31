## Context

TUI 是 `ui-tui/src/` 下的 TypeScript/Ink 应用。品牌文字散布在 banner（ASCII art）、theme 配置、terminal title、slash commands、setup 页面中。

## Goals / Non-Goals

**Goals:**
- 替换 TUI 中所有用户直接可见的 "Hermes" → "OpenStar"
- ASCII art banner 替换为 "OPENSTAR" 字样
- 保持 externalCli.ts 中的 `resolveHermesBin`/`launchHermesCommand` 不变（这些是 CLI 命令名调用，不影响用户可见文字）

**Non-Goals:**
- 不改 Python CLI 中的 Hermes 引用（auth messages 等），范围太大且与 TUI 无关
- 不改文件名/模块名中的 hermes
- 不改 test 文件中的 mock 数据（留给后续统一处理）

## Decisions

### 1. ASCII Art Banner — 生成新的 "OPENSTAR" figlet

**决定**: 将 `LOGO_ART` 数组替换为 "OPENSTAR" 的 block art（使用类似风格的 Unicode box-drawing 字符）。

**理由**: banner 是用户启动 TUI 后首先看到的品牌元素，必须替换。

### 2. 代码中的字符串替换 — 直接 sed/edit

**决定**: 对 theme.ts、useMainApp.ts、core.ts、setup.ts 中的 "Hermes" 字符串逐一替换为 "OpenStar"。

**理由**: 每处引用语境不同，需逐一确认替换不破坏逻辑。

## Risks / Trade-offs

- **[Test 文件可能断]** → test 中有 "Hermes" 字符串断言，需同步更新
- **[ASCII art 宽度]** → "OPENSTAR" 比 "HERMES AGENT" 短，可能影响布局对齐。LOGO_WIDTH export 会自动重新计算。
