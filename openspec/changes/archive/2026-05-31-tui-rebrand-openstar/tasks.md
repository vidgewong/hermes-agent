## 1. ASCII Art Banner

- [x] 1.1 Replace `LOGO_ART` in `ui-tui/src/banner.ts` with "OPENSTAR" ASCII block art (same Unicode box-drawing style)
- [x] 1.2 Update `LOGO_GRADIENT` array length to match new art line count

## 2. Theme Brand Name

- [x] 2.1 In `ui-tui/src/theme.ts`, change `name: 'Hermes Agent'` to `name: 'OpenStar'`

## 3. Terminal Title

- [x] 3.1 In `ui-tui/src/app/useMainApp.ts`, change the fallback title `'Hermes'` to `'OpenStar'`

## 4. Slash Commands

- [x] 4.1 In `ui-tui/src/app/slash/commands/core.ts`, change `/update` help text from "update Hermes Agent" to "update OpenStar"
- [x] 4.2 In `ui-tui/src/app/slash/commands/core.ts`, change history label from `Hermes #${i + 1}` to `OpenStar #${i + 1}`

## 5. Setup Content

- [x] 5.1 In `ui-tui/src/content/setup.ts`, change "Hermes needs a model provider" to "OpenStar needs a model provider"

## 6. Tests

- [x] 6.1 Update `ui-tui/src/__tests__/theme.test.ts` assertion from `'Hermes Agent'` to `'OpenStar'`
- [x] 6.2 Update `ui-tui/src/__tests__/createSlashHandler.test.ts` "Hermes" references to "OpenStar" if they test user-visible output
