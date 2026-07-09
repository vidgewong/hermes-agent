## Why

The current multi-tenant container implementation provides process isolation but leaves four critical gaps: tenant containers lack persistent `~/.claude/` storage (breaking Claude ecosystem integration), streaming progress cards and `AskUserQuestion`/clarify interactions are silently dropped for forwarded messages, skills have no ownership or governance model (only a flat allow/deny list), and there is no platform-wide `SOUL.md` personality layer shared across all tenants. These gaps mean tenants receive a degraded experience compared to the superuser, and the platform cannot grow collaboratively.

## What Changes

- **Persistent `.claude/` per tenant**: Each tenant profile directory gains a `.claude/` subdirectory that is bind-mounted into the container, replacing the ephemeral in-container `~/.claude/`. This makes `CLAUDE.md`, `settings.json`, `skills/`, and memory all durable across restarts.
- **SSE streaming proxy**: The tenant container's `api_server` exposes a new `GET /v1/stream` SSE endpoint. The host gateway replaces synchronous `forward_message()` with a streaming SSE client, reconnecting stream card hooks and clarify/AskUserQuestion callbacks for tenant sessions.
- **Clarify round-trip over SSE**: Containers emit `event: clarify` on the SSE stream; the host renders Feishu interactive cards. User button clicks POST to a new `POST /clarify/{session_id}` endpoint on the container, unblocking the in-container agent.
- **SOUL.md global personality layer**: A single `SOUL.md` in the superuser's `HERMES_HOME` is bind-mounted read-only into every tenant container at `~/.hermes/SOUL.md`. The system prompt builder prepends SOUL.md before tenant CLAUDE.md.
- **Skill governance: owner/group/propagation metadata**: SKILL.md gains a frontmatter block with `owner`, `group`, `propagate_to`, and `approval_policy` fields. The skill sync engine enforces these: group members can propose changes; full-group approval triggers automatic propagation to `propagate_to` tenants. Owners bypass approval.
- **Slash command passthrough for tenant sessions**: `/model`, `/new`, `/reset`, `/stop`, `/claude-code-runtime` are forwarded to the tenant container via a new `POST /v1/slash` endpoint rather than operating on the host config.

## Capabilities

### New Capabilities

- `tenant-claude-persistence`: Per-tenant `~/.claude/` directory mounted from host profile dir; SkillGateway and MemoryWatcher operate on durable paths inside the container.
- `tenant-sse-streaming`: SSE-based streaming proxy between host gateway and tenant containers; replaces synchronous HTTP forwarding for DM sessions.
- `tenant-clarify-roundtrip`: SSE `clarify` event + `POST /clarify/{session_id}` endpoint enabling AskUserQuestion and Feishu interactive cards to work for tenant-routed sessions.
- `soul-md-layer`: Global read-only `SOUL.md` personality file shared across all tenants via bind mount; system prompt composition order: SOUL → tenant CLAUDE.md → session context.
- `skill-governance`: SKILL.md frontmatter schema with `owner`, `group`, `propagate_to`, `approval_policy`; proposal/approval filesystem under `skills/<name>/_proposals/`; owner direct-commit bypass; automatic propagation on full-group approval.
- `tenant-slash-passthrough`: `POST /v1/slash` endpoint on tenant containers; host gateway forwards slash commands to the target tenant container instead of modifying host config.

### Modified Capabilities

- `tenant-container-runtime`: Adds `.claude/` and SOUL.md volume mounts to compose generation; updates health check and restart policy.
- `skill-propagation`: Extends sync logic to read frontmatter governance metadata; adds proposal/approval tracking.
- `gateway-tenant-routing`: Replaces `forward_message()` synchronous HTTP call with SSE streaming client; adds slash command forwarding path.

## Impact

- `hermes_cli/tenant_compose.py`: Add `.claude/` and `SOUL.md` volume entries per tenant service.
- `gateway/tenant_router.py`: Replace `forward_message()` with `stream_message()` using `httpx` SSE client; add `forward_slash()` method.
- `gateway/platforms/api_server.py`: Add `GET /v1/stream` SSE endpoint, `POST /clarify/{session_id}` endpoint, `POST /v1/slash` endpoint.
- `gateway/run.py`: Wire tenant SSE events into existing `GatewayEventDispatcher` → `FeishuStreamCard` pipeline; handle `clarify` SSE events by calling `adapter.send_clarify()`.
- `hermes_cli/tenant_skills_sync.py`: Parse SKILL.md frontmatter; implement proposal/approval filesystem; auto-propagate on approval quorum.
- `agent/claude_code_session.py`: Read `SOUL.md` path from `HERMES_HOME`; inject into session system prompt before tenant CLAUDE.md.
- `hermes_state.py`: Add `skill_proposals` table for tracking per-skill approval state.
- New dependency: `httpx[http2]` for async SSE client in `requirements.txt`.
