## 1. Dashboard Rebrand — i18n Files

- [x] 1.1 Update `web/src/i18n/en.ts`: change `brand` to "OpenStar", `brandShort` to "OS", `updateHermes` to "Update OpenStar", `updatingHermes` to "Updating OpenStar…"
- [x] 1.2 Update `web/src/i18n/zh.ts`: change `brand` to "OpenStar", `brandShort` to "OS", `updateHermes` to "更新 OpenStar", `updatingHermes` to "正在更新 OpenStar…"
- [x] 1.3 Update all other locale files (de, es, fr, it, ja, ko, pt, ru, tr, uk, af, ga, hu, zh-hant): change `brand` to "OpenStar", `brandShort` to "OS", update updateHermes/updatingHermes labels

## 2. Dashboard Rebrand — Hardcoded Text

- [x] 2.1 In `web/src/App.tsx`, change the sidebar brand text from "Hermes\nAgent" to "Open\nStar"

## 3. Backend API Extension

- [x] 3.1 Extend `_OPENSTAR_AGENTS` in `hermes_cli/web_server.py` to include `model` field for each agent (fixed config: e.g., "claude-sonnet-4-6")
- [x] 3.2 Extend the `/api/openstar/agents` response to include `current_task` (null for V1) and `recent_actions` (empty array for V1) per agent
- [x] 3.3 Update `OpenStarAgent` TypeScript interface in `web/src/lib/api.ts` to add `model: string`, `current_task: string | null`, `recent_actions: string[]`

## 4. Agent Detail Panel — Frontend

- [x] 4.1 Refactor AgentsPage to support expand/collapse state per agent (track `expandedId`, toggle on click)
- [x] 4.2 Create agent detail panel UI inside the expanded area: show model, status, current_task, recent_actions
- [x] 4.3 Style the detail panel with border-t, bg-background/50, consistent with SessionsPage expanded rows
- [x] 4.4 Show empty states for current_task ("No active task") and recent_actions ("No recent activity")
- [x] 4.5 Remove the direct `/chat?agent=<id>` navigation on card click (replace with expand/collapse)

## 5. Chat Button with Slash Command

- [x] 5.1 Add "Start Chat" button in the agent detail panel that navigates to `/chat?command=/<agent-id>`
- [x] 5.2 In ChatPage, read the `command` URL query parameter on mount
- [x] 5.3 If `command` parameter exists, pre-fill it into the chat input (investigate ChatPage input mechanism — if PTY-based, write to terminal; if input state, set value)

## 6. Internationalization for New Strings

- [x] 6.1 Add i18n keys for agent detail: "model", "currentTask", "recentActions", "noActiveTask", "noRecentActivity", "startChat"
- [x] 6.2 Add Chinese (zh) translations for all new keys
- [x] 6.3 Add English fallback translations to all other locale files

## 7. Verification

- [x] 7.1 Verify sidebar and mobile header show "OpenStar" branding
- [x] 7.2 Verify "Update OpenStar" label in system actions
- [x] 7.3 Verify agent card click expands/collapses detail panel
- [x] 7.4 Verify detail panel shows model, status, current_task, recent_actions
- [x] 7.5 Verify "Start Chat" button navigates to `/chat?command=/<agent-id>`
- [x] 7.6 Verify chat input is pre-filled with the slash command from URL
