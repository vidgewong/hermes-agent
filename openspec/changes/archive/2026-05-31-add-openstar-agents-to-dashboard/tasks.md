## 1. Backend API

- [x] 1.1 Create `/api/openstar/agents` endpoint handler returning the three fixed agents (mb-req, mb-test, mb-arch) with id, name, description, status, icon, last_active fields
- [x] 1.2 Implement agent status logic: check session store for active sessions matching agent profiles, return "online"/"busy"/"offline" accordingly; default to "offline" in V1
- [x] 1.3 Register the endpoint in the API router with existing session authentication middleware

## 2. Frontend API Layer

- [x] 2.1 Add `OpenStarAgent` TypeScript interface in `web/src/lib/api.ts` with fields: id, name, description, status, icon, last_active
- [x] 2.2 Add `getOpenStarAgents()` method to the `api` object returning `Promise<{ agents: OpenStarAgent[] }>`

## 3. Sidebar Navigation

- [x] 3.1 Add `Bot` icon import from lucide-react in `web/src/App.tsx`
- [x] 3.2 Add Agents nav item to `BUILTIN_NAV_REST` array, positioned immediately after the Sessions entry, with path `/agents`, labelKey `agents`, and Bot icon

## 4. Agents Page

- [x] 4.1 Create `web/src/pages/AgentsPage.tsx` with page structure: heading + agent cards grid
- [x] 4.2 Implement data fetching with `api.getOpenStarAgents()` on mount and 5s polling interval (useEffect + setInterval pattern matching SessionsPage)
- [x] 4.3 Implement agent cards using Card/CardContent from `@nous-research/ui`, showing icon, name, description, status badge, and last_active time
- [x] 4.4 Implement status badges: online = success tone + pulse dot, busy = warning tone, offline = outline tone
- [x] 4.5 Add click handler on agent cards: navigate to `/chat?agent=<agent-id>` when embedded chat is enabled; no-op otherwise
- [x] 4.6 Handle loading state (Spinner) and error state (graceful message)

## 5. Route Registration

- [x] 5.1 Import AgentsPage in `web/src/App.tsx`
- [x] 5.2 Add `"/agents": AgentsPage` to `BUILTIN_ROUTES_CORE` object

## 6. Internationalization

- [x] 6.1 Add i18n keys: nav label "agents", page title, agent names, agent descriptions, status labels (online/busy/offline)
- [x] 6.2 Add Chinese (zh) translations for all new keys
- [x] 6.3 Use `useI18n()` in AgentsPage for all user-visible text

## 7. Verification

- [x] 7.1 Verify "Agents" nav item appears in sidebar below Sessions with Bot icon
- [x] 7.2 Verify `/agents` route renders the page with three agent cards
- [x] 7.3 Verify agent status badges display correct tones for each state
- [x] 7.4 Verify clicking an agent card navigates to `/chat?agent=<id>`
- [x] 7.5 Verify data refreshes on 5s interval without UI flicker
