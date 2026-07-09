## Context

The `multi-tenant-profile-isolation` change (already merged to main) established Docker-container-per-tenant isolation, a `TenantRegistry`, skill allow-lists, and synchronous HTTP message forwarding. It is a sound foundation but has four gaps that block production use:

1. **No `~/.claude/` persistence** — SkillGateway and MemoryWatcher write symlinks and files to `~/.claude/` and `~/.agents/` inside the container, but these paths are ephemeral (no volume mount). Claude Code SDK sessions therefore cannot persist skills, memory, or settings across container restarts.
2. **Streaming entirely lost for tenant sessions** — `forward_message()` in `TenantRouter` is a synchronous `POST /v1/chat/completions`. The host gateway receives a single final string. All `GatewayEventDispatcher` events (text chunks, tool start/end, clarify requests) are swallowed. Feishu stream cards and AskUserQuestion are silently non-functional for tenants.
3. **No shared personality** — Each tenant's system prompt is built entirely from their own `CLAUDE.md`. There is no mechanism to enforce platform-wide behaviour rules, safety policies, or persona across all tenants.
4. **No skill governance** — Skills are pushed from superuser to tenants via a flat allowlist. There is no way for a tenant to propose a skill improvement, no concept of ownership, and no collaborative propagation policy.

Stakeholders: platform operator (superuser), tenant users, future tenant contributors.

## Goals / Non-Goals

**Goals:**
- Every tenant has a durable, host-resident `~/.claude/` directory (under their profile folder) that survives container restarts.
- Tenant sessions stream text chunks, tool progress, and clarify events to the host gateway with the same fidelity as superuser sessions.
- AskUserQuestion / clarify works end-to-end for tenant-routed Feishu DMs.
- A single `SOUL.md` file is injected read-only at the bottom of every tenant's system prompt.
- Skills carry governance metadata (`owner`, `group`, `propagate_to`, `approval_policy`); the sync engine enforces approval quorums before cross-tenant propagation.
- Slash commands (`/model`, `/new`, `/reset`, `/stop`, `/claude-code-runtime`) reach the correct tenant container rather than modifying host config.

**Non-Goals:**
- Real-time bi-directional skill sync via git (file-system proposal/approval is sufficient for now).
- Multi-platform streaming (only Feishu stream card in scope; Slack/Telegram are future work).
- Tenant-to-tenant direct communication channels.
- UID-level Unix isolation between tenants (Docker namespace isolation is sufficient for the internal team use-case).
- GUI admin panel (CLI + slash commands are the operator surface).

## Decisions

### D1: SSE over WebSocket for tenant streaming

**Choice**: Server-Sent Events (`text/event-stream`) from container to host.

**Rationale**: SSE is unidirectional server-push over a single HTTP connection — exactly the shape of an agent turn (one request, many events, terminal response). It requires no upgrade handshake, works through standard reverse proxies, and `httpx` supports it natively with `stream()`. WebSocket would add bidirectional complexity for a use-case that is 95% server-to-client.

**Clarify round-trip**: The one client→server message (user's clarify choice) travels on a separate `POST /clarify/{session_id}` request. This keeps the SSE channel clean and allows the host to fire the clarify POST at any time without message ordering concerns.

**Alternative considered**: gRPC bidirectional streaming — rejected due to additional protobuf dependency and container startup overhead.

### D2: SOUL.md as read-only bind mount, not a config field

**Choice**: `HERMES_HOME/SOUL.md` → `/home/hermes/.hermes/SOUL.md:ro` in docker-compose.

**Rationale**: A bind mount guarantees the tenant cannot modify the file (`:ro` at Docker layer, not just POSIX permission). The system prompt builder reads it at turn start, so hot-updates to SOUL.md take effect on the next turn without restarting containers. Storing the path in config would introduce a config-schema dependency; the file-system presence is sufficient.

**Loading order**: `SOUL.md` content is prepended before `CLAUDE.md` in the system prompt builder. If `SOUL.md` does not exist the step is silently skipped (operator opt-in).

### D3: Skill governance via filesystem, not a database

**Choice**: Proposals stored as files under `skills/<name>/_proposals/<tenant>/<hash>/diff.md`; approvals as `_approvals/<tenant>.approve`; quorum check runs in `sync_all_tenant_skills()`.

**Rationale**: The entire Hermes state-of-record already lives in the filesystem (`config.yaml`, `state.db`, `skills/`). Adding a proposals directory keeps the same operational model (backup = copy the skills dir). A separate DB would require schema migrations and a running process to query. The proposal volume is low (skill changes are infrequent).

**Quorum trigger**: After any approval file is written, a `_check_quorum()` helper counts `_approvals/*.approve` files. If count ≥ group size (or `approval_policy: owner_only` is set), `_promote_proposal()` copies the proposed SKILL.md to the canonical location and calls `sync_tenant_skills()` for all tenants in `propagate_to`.

### D4: `~/.claude/` path under profile dir, not a separate registry entry

**Choice**: `{profile_dir}/.claude` (e.g., `~/.hermes/profiles/alice/.claude`) mounted to `/home/hermes/.claude`.

**Rationale**: Keeps all tenant state co-located under their profile directory. Backup, migration, and deletion of a tenant is a single `rm -rf profiles/alice/`. The path is predictable and requires no additional config field.

**SkillGateway / MemoryWatcher**: These already use `Path.home()` which resolves to `/home/hermes` inside the container. Once `~/.claude/` is mounted, they work without code changes — they write to `/home/hermes/.claude/skills/` which is the durable volume.

### D5: Slash command forwarding via `POST /v1/slash`

**Choice**: Host gateway detects slash prefix in DM messages, extracts the command, and POSTs `{"command": "/model claude-opus-4-8", "session_id": "..."}` to the tenant container's `/v1/slash` endpoint before or instead of starting a full SSE turn.

**Rationale**: Slash commands mutate agent state (model selection, session reset) inside the tenant process. Forwarding them as a side-channel message (not an SSE turn) is cleaner than encoding them as chat turns and filtering on the container side. The container's slash handler already exists (`_handle_slash_command` in `gateway/run.py`); wrapping it behind an HTTP endpoint is low-effort.

## Risks / Trade-offs

**[Risk] SSE connection drops mid-turn** → The host gateway retries with a `Last-Event-ID` header; the container buffers the last N events in memory per session (ring buffer, 200 events max). If the container restarts during a turn the turn is lost (same as current synchronous model). Mitigation: containers use `restart: unless-stopped`; the host sends a user-facing "reconnecting…" card update.

**[Risk] `.claude/` volume creation on fresh provision** → `provision_tenant()` must `mkdir -p {profile_dir}/.claude` before the container starts, or Docker will create it as root. Mitigation: add explicit mkdir to provisioning code path.

**[Risk] Quorum deadlock if a group member is offboarded** → If a group member is removed from the registry, their pending approval files are never written, blocking quorum forever. Mitigation: `approval_policy: majority` counts approvals against current group size at check time; orphaned `_proposals/` directories are GC'd after 30 days by a cron task.

**[Risk] SOUL.md content conflicts with tenant CLAUDE.md** → If SOUL.md and a tenant's CLAUDE.md contain contradictory instructions, model behaviour is undefined. Mitigation: SOUL.md should contain only additive platform-level rules (persona, safety, output format constraints), never tool-specific or domain-specific instructions.

**[Trade-off] SSE client adds `httpx` dependency** → `httpx[http2]` is ~1MB. The existing codebase uses `requests` and `aiohttp`. We add `httpx` specifically for the SSE streaming client because neither `requests` nor `aiohttp` has clean built-in SSE support. This is a single additional dependency for a well-maintained library.

## Migration Plan

1. **Phase 1 (non-breaking)**: Add `.claude/` mkdir to `provision_tenant()`; add volume mount to `generate_tenant_compose()`; regenerate compose. Existing running containers are unaffected until restarted.
2. **Phase 2**: Add `SOUL.md` volume mount to compose; create `SOUL.md` in superuser HERMES_HOME. System prompt builder reads it if present (opt-in).
3. **Phase 3**: Add `GET /v1/stream`, `POST /clarify/{session_id}`, `POST /v1/slash` to `api_server.py`; update `TenantRouter` to use SSE client. Feature-flagged behind `tenant_routing.streaming: true` in config.
4. **Phase 4**: Add SKILL.md frontmatter parsing; implement proposal/approval filesystem; update `sync_all_tenant_skills()`. Old skills without frontmatter continue to work (defaults: `owner: superuser`, `group: []`, `propagate_to: all`, `approval_policy: owner_only`).

Rollback: revert `tenant_routing.streaming` to `false` to fall back to synchronous forwarding at any time.

## Open Questions

- **Q1**: Should `SOUL.md` be versioned (git-tracked) separately from the rest of HERMES_HOME, or is operator discipline sufficient?
- **Q2**: What is the maximum skill proposal retention period before auto-GC? 30 days is a guess.
- **Q3**: Should tenant containers expose `/v1/stream` only when `HERMES_SINGLE_PROFILE=true`, or always? (Currently the API server runs in all gateway modes.)
- **Q4**: Is `httpx` acceptable as a new dependency, or should we implement a minimal SSE client over `urllib`?
