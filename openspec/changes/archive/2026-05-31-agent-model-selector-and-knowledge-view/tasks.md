## 1. Backend API — Model Selector Data

- [x] 1.1 Add `available_models` field to each agent in `_OPENSTAR_AGENTS` containing mock model list: ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5"]
- [x] 1.2 Include `available_models` in the API response alongside existing fields

## 2. Backend API — Knowledge Layer Data

- [x] 2.1 Add mock `knowledge` data structure for MB-REQ Agent: skills=[requirement-generation (L0 summary, L1 architecture/aspice/writing-rules, L2 audio/adas/health-monitor), dng-integration, clarification-protocol], memory_summary
- [x] 2.2 Add mock `knowledge` data for MB-Test Agent: skills=[test-generation (L0, L1 test-framework/aspice, L2 audio/adas), starc-integration], memory_summary
- [x] 2.3 Add mock `knowledge` data for MB-Arch Agent: skills=[architecture-review (L0, L1 quality-standards/design-patterns, L2 audio/adas), code-review], memory_summary
- [x] 2.4 Include `knowledge` in the API response for each agent

## 3. Frontend Types

- [x] 3.1 Add `available_models: string[]` to `OpenStarAgent` interface in `web/src/lib/api.ts`
- [x] 3.2 Add `knowledge: AgentKnowledge` interface with `skills: AgentSkill[]` and `memory_summary: string`
- [x] 3.3 Add `AgentSkill` interface with `name`, `l0_summary`, `l1: { categories: {name, files}[] }`, `l2: { modules: {name, files}[] }`

## 4. Frontend — Model Selector

- [x] 4.1 Replace the plain text model display in AgentDetailPanel with a `<select>` dropdown (or @nous-research/ui Select if available)
- [x] 4.2 Populate the dropdown options from `agent.available_models`, set current value to `agent.model`
- [x] 4.3 Add onChange handler that shows toast "Model switch not yet implemented" and logs to console

## 5. Frontend — Knowledge Layer View

- [x] 5.1 Add a "Knowledge" section in AgentDetailPanel below the existing info
- [x] 5.2 Render skills as collapsible entries (click to expand/collapse, track per-skill expand state)
- [x] 5.3 When skill expanded, show L0 with primary-colored "L0" badge and summary text
- [x] 5.4 When skill expanded, show L1 with warning-colored "L1" badge and category/file tree
- [x] 5.5 When skill expanded, show L2 with success-colored "L2" badge and module/file tree
- [x] 5.6 Render Memory summary below skills list with a "Memory" badge

## 6. Internationalization

- [x] 6.1 Add i18n keys: "knowledge", "skills", "memory", "modelSwitchNotImplemented", "l0Label", "l1Label", "l2Label", "memoryLabel"
- [x] 6.2 Add Chinese (zh) translations
- [x] 6.3 Add fallback English translations to all other locale files

## 7. Verification

- [x] 7.1 Verify model dropdown displays with available options
- [x] 7.2 Verify selecting a model shows toast notification
- [x] 7.3 Verify Knowledge section shows all skills with correct L0/L1/L2 structure
- [x] 7.4 Verify color-coded badges distinguish layers correctly
- [x] 7.5 Verify skill expand/collapse works independently for each skill
