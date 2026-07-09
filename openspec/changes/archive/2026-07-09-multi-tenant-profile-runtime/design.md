## Context

Hermes already has two powerful isolation primitives:
1. **Profiles** (`hermes_cli/profiles.py`) — fully independent HERMES_HOME directories with their own config, memory, skills, sessions, workspace, and .claude configuration.
2. **Docker environment** (`tools/environments/docker.py`) — hardened container sandbox with capability dropping, cgroup limits, bind mounts, and label-based lifecycle management.

The failed first attempt at multi-tenancy built a parallel system: containers ran their own gateway, duplicating routing and command handling. This caused session bugs, configuration drift, and an unmaintainable split-brain architecture.

The new design composes profiles + docker_env directly: each tenant IS a profile, the host gateway does all routing, and containers are pure agent execution sandboxes with profile content mounted in.

Additionally, a user registry is needed to map IM identities (Feishu open_id, Telegram user_id) to users, and users to profiles. The gateway resolves identity at message arrival, scopes to the correct profile, and dispatches into the container.

## Goals / Non-Goals

**Goals:**
- Each tenant gets full isolation: own config.yaml, .env, skills, memory, workspace, .claude
- Host gateway handles ALL routing, slash commands, cron, and configuration
- Containers run only the agent loop (AIAgent + tools + terminal)
- Users are identified by IM identity and auto-registered when messaging for the first time
- Admin agents can manage user records via tools/skills
- Existing single-user Hermes deployments are unaffected (opt-in via `gateway.multi_tenant.enabled`)
- Leverage existing `_profile_runtime_scope()` and multiplex_profiles infrastructure

**Non-Goals:**
- Group chat routing (DMs only for now)
- Billing, quotas, or usage tracking per tenant
- Container orchestration beyond single-host Docker (no K8s)
- SSO/OIDC (users are internal, auto-registered from IM)
- Running multiple containers per user (one profile = one container)
- Replacing the existing profile system — we build ON it

## Decisions

### D1: Tenant = Profile (no new abstraction)

A tenant is a Hermes profile. We reuse `profiles.py` creation/deletion/export and `get_hermes_home()` scoping. No new "tenant" model in code — just a profile with a user record pointing to it.

**Rationale**: Profiles already give us everything a tenant needs. Adding a layer on top would duplicate isolation logic and create sync bugs between "tenant state" and "profile state."

**Alternative considered**: Separate tenant model with profile as an implementation detail. Rejected because it adds indirection without capability — every tenant operation would just proxy to a profile operation.

### D2: PostgreSQL user registry (new service)

A new `UserRegistry` service backed by PostgreSQL stores:
- `users` table: id (UUID), username, display_name, email, wiw_id, roles, responsibilities, created_at
- `im_identities` table: id, user_id (FK), platform (enum), platform_user_id, metadata (JSONB), linked_at
- `user_profiles` table: user_id (FK), profile_name, is_primary, provisioned_at

**Rationale**: SQLite (used for sessions) doesn't suit a shared registry accessed by the gateway + admin API + admin agent concurrently. PostgreSQL supports concurrent writes, JSONB for flexible metadata, and is already deployed on the openstar server.

**Alternative considered**: Extend existing SQLite state.db. Rejected because the gateway's SQLite is per-profile (each profile has its own state.db), but the user registry must be global across all profiles.

### D3: Identity resolution at gateway message entry

In `_handle_message()`, before session resolution, a new `_resolve_user()` step:
1. Extract platform + platform_user_id from the MessageEvent
2. Query `im_identities` table for a matching record
3. If found → load user → get their profile_name → scope via `_profile_runtime_scope()`
4. If not found → auto-register: create user record, provision profile (via `profiles.py`), link IM identity, then proceed

This runs BEFORE the existing authorization check, replacing it for multi-tenant mode.

**Rationale**: The gateway already has `_profile_runtime_scope()` for per-profile scoping in multiplex mode. We're adding a resolution layer that feeds into the same mechanism.

**Alternative considered**: Resolve at the platform adapter level. Rejected because it would require changes to every adapter; the gateway runner is the single dispatch point.

### D4: Extended docker_env as tenant container runtime

Each tenant's agent runs in a Docker container managed by the existing `DockerEnvironment` class. Extensions:
- **Profile mount**: bind-mount `$PROFILE_HOME/workspace` → `/workspace`, `$PROFILE_HOME/skills` → `/skills` (read-only), `$PROFILE_HOME/memories` → `/memories`, `$PROFILE_HOME/.claude` → `/home/agent/.claude` (read-only)
- **Container labeling**: `hermes-tenant=<username>`, `hermes-profile=<profile_name>` for lifecycle management
- **Persistent container**: container stays alive between turns (like current docker_env behavior with `sleep infinity`), commands dispatched via `docker exec`
- **No gateway inside**: container image has no gateway code, just agent runtime + tools

The gateway calls into the container's agent via the existing `run_conversation()` interface, passing user message + system prompt + conversation history. The agent loop runs inside the container; tool calls that need the terminal execute in the container's sandboxed environment.

**Rationale**: docker_env already handles container creation, capability dropping, cgroup limits, bind mounts, exec dispatch, and orphan reaping. We're configuring it, not rewriting it.

**Alternative considered**: New container orchestration layer. Rejected — docker_env already does everything we need. The only addition is profile-specific mount configuration.

### D5: Agent on host, ALL filesystem I/O in container

The host gateway does NOT start an AIAgent inside the container process. Instead:
- The gateway creates an AIAgent instance on the host (as it does today in multiplex mode)
- The agent's terminal environment is configured as `DockerEnvironment` pointing to the tenant's container
- **ALL file/terminal tools execute inside the container via `docker exec`**: terminal, read_file, write_file, patch, search_files
- Other tools (web_search, browser, memory, delegation, LLM calls) run on the host, scoped to the tenant's profile

Tool routing in multi-tenant mode:
```
Agent Loop (host)
├── LLM API call              → host 直发 (API key from profile .env)
├── memory_store/search()     → host, scoped to profile dir
├── web_search/browser        → host
├── terminal("ls")            → docker exec container
├── read_file("/workspace/x") → docker exec cat (container)
├── write_file(...)           → docker exec tee (container)
├── patch(...)                → docker exec sed/patch (container)
└── search_files(...)         → docker exec grep/find (container)
```

The container can only see its own mounted files — physical isolation, no path validation needed. This is the same model as Claude Code's sandbox: orchestration outside, execution inside.

**Rationale**: Path-based validation (allowlisting `$PROFILE_HOME/workspace/`) is fragile — one missed check or `../` escape = data leak across tenants. Running ALL I/O tools in the container makes isolation a physical guarantee (Docker mount boundary), not a code-level assumption. `docker exec` is the only communication mechanism — already fully supported by docker_env.

**Alternative considered**: Path validation in file tool handlers. Rejected — defense-in-depth says enforcement should be at the namespace boundary (container), not at the application level.

### D6: Web API for user management

A new set of REST endpoints on the existing gateway API server (`gateway/platforms/api_server.py`):
- `GET/POST /api/users` — list/create users
- `GET/PATCH/DELETE /api/users/:id` — user CRUD
- `POST /api/users/:id/identities` — link IM identity
- `DELETE /api/users/:id/identities/:identity_id` — unlink
- `POST /api/users/:id/provision` — trigger profile provisioning

Protected by the existing API server auth (bearer token).

**Rationale**: The gateway already serves an API (`api_server.py`). Adding user management endpoints avoids a separate service.

### D7: Admin tools exposed to admin agent profile

An "admin" profile gets a `tenant_admin` toolset with tools:
- `user_list`, `user_get`, `user_create`, `user_update` — CRUD via the registry
- `user_provision` — provision/deprovision profile for a user
- `user_link_identity` — link an IM identity to a user

These are service-gated tools (`check_fn` verifies the current profile is in the admin list in config). They appear only for admin profiles.

**Rationale**: Footprint Ladder rung 3 — service-gated tools that only appear when configured. Zero schema footprint for non-admin profiles.

## Risks / Trade-offs

- **[PostgreSQL dependency]** → Mitigation: Only required when `gateway.multi_tenant.enabled: true`. Single-user deployments have zero new deps. Document Docker Compose setup for the DB.
- **[Container startup latency on first message]** → Mitigation: Containers are persistent (sleep infinity pattern). First message provisions and starts; subsequent messages hit the running container. Add a warm-up on profile provisioning.
- **[Profile explosion with many users]** → Mitigation: Profiles are lightweight directories. 100 profiles = 100 dirs. Container idle timeout can stop containers for inactive tenants (existing docker_env reaping).
- **[Auto-registration spam]** → Mitigation: Config option `gateway.multi_tenant.auto_register: true|false`. When false, unrecognized IM users get a "not registered" reply. Allowlist by domain/IM-group membership.
- **[Breaking change: removing old tenant code]** → Mitigation: The old code is unreleased and broken. No users depend on it.

## Migration Plan

1. Remove all existing tenant files (clean slate)
2. Add PostgreSQL user registry as an optional dependency
3. Implement identity resolution in gateway (behind feature flag)
4. Extend docker_env with profile mount configuration
5. Add admin API endpoints and admin toolset
6. Update CLI with `hermes tenant` convenience commands
7. Document setup in a tenant-onboarding skill

Rollback: Disable `gateway.multi_tenant.enabled` — reverts to existing single-profile or manual multiplex behavior.

### D8: Claude Agent SDK options for per-tenant logical isolation

When the Hermes+Claude ecosystem integration (Claude Agent SDK) is active, each tenant's agent session SHALL be configured with tenant-scoped SDK options:

```python
options = ClaudeAgentOptions(
    cwd=tenant_workspace_dir,         # tenant's workspace as SDK working directory
    setting_sources=[],               # disable host settings contamination
    env={
        "CLAUDE_CONFIG_DIR": tenant_claude_dir,      # per-tenant .claude (CLAUDE.md, project instructions)
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",      # Hermes owns memory at profile level
    }
)
```

This provides two complementary isolation layers:
- **Physical isolation (Docker)**: file I/O tools execute in container, can't escape mount boundary
- **Logical isolation (SDK options)**: settings, CLAUDE.md, memory, and working directory context are per-tenant

Claude Code's native file tools (`Bash`, `Read`, `Write`, `Edit`) are already in `disallowed_tools` per the tool-routing spec — replaced by Hermes MCP equivalents that route through docker exec. The `cwd` here primarily affects SDK-internal path resolution and CLAUDE.md/AGENTS.md discovery.

**Rationale**: Even though Docker provides file isolation, the SDK itself has its own settings/config/memory discovery paths that run on the host. Without these options, one tenant's CLAUDE.md or settings could bleed into another's session.

### D9: Per-user dashboard (self-service profile editing)

The existing Hermes dashboard (port 9119) will serve as the per-user self-service UI. Each user accesses their own profile's configuration: config.yaml editing, skills management, memory browsing, workspace files. The dashboard scopes to the authenticated user's profile.

**Current phase**: No auth enforcement — all endpoints are open. The architecture supports adding per-user JWT auth later (user registry already stores user records).

**Future**: Each user gets a dashboard session scoped to their profile. Admin users can switch between profiles. Regular users see only their own.

**Rationale**: Reusing the existing dashboard avoids building a new frontend. The dashboard already reads from HERMES_HOME, so scoping it to a profile directory gives per-user views for free.

### D10: Dockerfile.tenant reused as-is (entrypoint change only)

The existing `docker/Dockerfile.tenant` is structurally correct: correct base image, proxy config, UID/GID 1000 matching host, PYTHONPATH for mounted code, and user creation. The only change needed is the ENTRYPOINT — from `gateway run` (wrong: container should not run a gateway) to `sleep infinity` (correct: container is an exec target for docker_env commands).

The hermes-agent code is bind-mounted at `/opt/hermes-agent` (read-only); the tenant profile at `/home/openstar/.hermes/`. This aligns with the design decision D4/D5 where the container is a terminal sandbox, not an autonomous service.

## Open Questions

- Should container images be pre-built (one standard image) or per-tenant (custom tooling)?
  → One standard image (Dockerfile.tenant) with tooling mounted from profile.
- Should admin profiles be configurable or hardcoded to the "default" profile?
  → Configurable via `gateway.multi_tenant.admin_profiles: ["default"]`.
- How to handle container resource limits per tenant? Uniform or configurable?
  → Start uniform, add per-user config later if needed.
- Dashboard auth scoping — when to implement per-user JWT?
  → Phase 2. Current phase: open access, one dashboard instance per profile.
