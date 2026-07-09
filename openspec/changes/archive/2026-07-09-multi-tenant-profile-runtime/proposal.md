## Why

The current multi-tenant implementation is architecturally flawed: containers run their own gateway, duplicating routing/command-handling logic that belongs on the host. This creates bugs around session management, slash command dispatch, and configuration sync. Hermes already has profile isolation (full HERMES_HOME per profile) and Docker sandboxing (docker_env) — multi-tenancy should compose these existing primitives rather than building parallel infrastructure. Each tenant needs isolated workspace, memory, tools, skills, and .claude config — which is exactly what a profile already provides.

## What Changes

- **BREAKING**: Remove all existing tenant code (gateway/tenant_router.py, gateway/workspace_manager.py, gateway/session_lifecycle.py, hermes_cli/tenant_cmd.py, hermes_cli/tenant_compose.py, hermes_cli/tenant_registry.py, etc.) — clean slate
- Add a **user registry** backed by PostgreSQL: each user has identity fields (name, email, WIW ID, roles/responsibilities) plus linked IM identities (Feishu open_id, Telegram user_id, etc.)
- Add **IM identity resolution** at the gateway layer: when a DM arrives, resolve the sender's IM identity to a registered user; auto-register unknown internal users
- Map each registered user to a **Hermes profile** that provides full environment isolation (config.yaml, .env, skills, memory, workspace, .claude)
- Extend the existing **docker_env** backend to serve as the tenant agent runtime container — mount the user's profile content (workspace, skills, memory, .claude) into the container; no gateway runs inside
- All **message routing, slash commands, cron, configuration** remain host-side in the existing gateway; the container is a pure agent execution sandbox
- Provide **admin tools/skills** so an administrator agent (also running in its own profile container) can manage user records (CRUD identity, assign roles, update WIW IDs)
- Add a **web API** for user/tenant management (frontend registration, IM linking, profile provisioning)

## Capabilities

### New Capabilities
- `user-registry`: PostgreSQL-backed user identity store with IM identity linking and auto-registration
- `tenant-profile-runtime`: Profile-based tenant isolation using extended docker_env for agent execution containers
- `tenant-gateway-routing`: Host-side gateway routing from IM identity → user → profile → container agent
- `tenant-admin-tools`: Admin agent skills/tools for user CRUD, role assignment, and profile provisioning

### Modified Capabilities
- `tool-routing`: Docker environment tool routing needs to support per-user profile mounts and tenant-scoped container labeling

## Impact

- **Database**: New PostgreSQL dependency for user registry (gateway already uses SQLite for sessions; this is a separate service)
- **Gateway**: `gateway/run.py` gains user-resolution middleware in `_handle_message()` pipeline; profile routing extends existing `_profile_runtime_scope()`
- **Docker environment**: `tools/environments/docker.py` gains profile-mount configuration for tenant containers
- **CLI**: New `hermes tenant` subcommands for user/profile lifecycle management
- **Config**: New `gateway.tenants` section in config.yaml for enabling multi-tenant mode, DB connection, auto-registration policy
- **API**: New REST endpoints for user management (builds on existing gateway API server pattern in `gateway/platforms/api_server.py`)
- **Removed**: All files in the existing tenant implementation (~15 files across gateway/, hermes_cli/, tests/)
