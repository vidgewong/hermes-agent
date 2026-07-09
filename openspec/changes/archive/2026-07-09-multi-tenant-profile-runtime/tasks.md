## 1. Cleanup — Remove Flawed Tenant Code

- [x] 1.1 Remove gateway/tenant_router.py, gateway/session_lifecycle.py, gateway/workspace_manager.py, gateway/workspace_api.py, gateway/agent_window.py
- [x] 1.2 Remove hermes_cli/tenant_cmd.py, hermes_cli/tenant_compose.py, hermes_cli/tenant_registry.py, hermes_cli/tenant_directory.py, hermes_cli/tenant_skills_sync.py, hermes_cli/skill_proposals.py, hermes_cli/subcommands/tenant.py
- [x] 1.3 Remove tools/user_registry_tool.py
- [x] 1.4 Remove all test files: tests/gateway/test_tenant_*.py, tests/hermes_cli/test_tenant_*.py, tests/hermes_cli/test_skill_governance.py, tests/hermes_cli/test_soul_md_system_prompt.py
- [x] 1.5 Remove openspec/changes/ directories for old tenant specs (tenant-session-architecture, tenant-stateless-container, multi-tenant-profile-isolation) and openspec/specs/tenant-* specs
- [x] 1.6 Remove skills/tenant-onboarding/
- [x] 1.7 Remove web/src/pages/TenantsPage.tsx and its route reference in App.tsx
- [x] 1.8 Clean up any imports/references to removed modules in gateway/run.py, hermes_cli/main.py, hermes_cli/skills_hub.py, toolsets.py, model_tools.py

## 2. User Registry — Database Layer

- [x] 2.1 Add asyncpg/sqlalchemy[asyncio] + alembic to pyproject.toml[tenant] optional deps (host-side, not requirements-tenant.txt)
- [x] 2.2 Create gateway/tenant/models.py with SQLAlchemy models: User, IMIdentity, UserProfile tables
- [x] 2.3 Create gateway/tenant/registry.py with UserRegistry class: create_user, get_user, update_user, list_users, link_identity, unlink_identity, resolve_by_im_identity, map_profile, get_user_profile
- [x] 2.4 Create gateway/tenant/db.py with connection pool management: init_db(database_url), get_session(), run_migrations()
- [x] 2.5 Create alembic migration for initial schema (users, im_identities, user_profiles tables)
- [x] 2.6 Add config schema: gateway.multi_tenant.enabled, gateway.multi_tenant.database_url, gateway.multi_tenant.auto_register, gateway.multi_tenant.admin_profiles, gateway.multi_tenant.container_idle_timeout
- [x] 2.7 Write tests for UserRegistry: CRUD operations, identity linking, conflict handling, auto-registration username generation

## 3. Gateway Identity Resolution

- [x] 3.1 Create gateway/tenant/resolver.py with TenantResolver class: resolve_user(platform, platform_user_id) → User, auto_register_user(platform, platform_user_id, platform_metadata), get_profile_for_user(user) → profile_name
- [x] 3.2 Integrate TenantResolver into gateway/run.py _handle_message(): add identity resolution step before session creation (behind multi_tenant.enabled flag)
- [x] 3.3 Wire resolved profile into existing _profile_runtime_scope() — set HERMES_HOME to the tenant's profile directory for the turn
- [x] 3.4 Add DM-only gating: skip tenant resolution for group messages (chat_type != private)
- [x] 3.5 Handle "not registered" reply when auto_register is false and user is unknown
- [x] 3.6 Write tests for TenantResolver: known user resolution, auto-registration flow, DM-only gating, disabled auto-register rejection

## 4. Profile Provisioning

- [x] 4.1 Create gateway/tenant/provisioner.py with TenantProvisioner class: provision_profile(user, template=None) → profile_name, deprovision_profile(user), is_provisioned(user)
- [x] 4.2 Implement provisioning using existing profiles.py create_profile() with optional --clone from template
- [x] 4.3 Integrate provisioning into auto-registration flow (resolver calls provisioner after creating user)
- [x] 4.4 Add profile_template config: gateway.multi_tenant.profile_template (profile name to clone from, or null for empty)
- [x] 4.5 Write tests for provisioning: new profile creation, template cloning, idempotent re-provision, deprovision

## 5. Docker Environment Extension — Tenant Containers

- [x] 5.1 Update docker/Dockerfile.tenant entrypoint: change from gateway run to sleep infinity (container serves as exec target, not a gateway)
- [x] 5.2 Add TenantDockerEnvironment subclass (or configuration mode) in gateway/tenant/docker_env.py that configures profile-based mounts: workspace(rw), skills(ro), memories(rw), .claude(ro)
- [x] 5.3 Add container labeling: hermes-tenant=<username>, hermes-profile=<profile_name>
- [x] 5.4 Implement container lookup by tenant labels (reuse existing container if running)
- [x] 5.5 Implement idle timeout: stop containers inactive beyond container_idle_timeout seconds
- [x] 5.6 Wire TenantDockerEnvironment into agent creation for tenant profiles in gateway/run.py (when multi_tenant.enabled, tenant agents get Docker execution backend)
- [x] 5.7 Route ALL file I/O tools through container: implement docker exec wrappers for read_file (cat), write_file (tee/heredoc), patch (sed/patch), search_files (grep/find) in addition to terminal
- [x] 5.8 Add tool routing decision logic in model_tools.py/handle_function_call(): if multi-tenant session, route file/terminal tools to DockerEnvironment; others execute on host
- [x] 5.9 Write tests for tenant container lifecycle: creation, reuse, mount paths, idle cleanup
- [x] 5.10 Write tests for file tool isolation: verify read_file/write_file/patch/search_files execute inside container and cannot access paths outside mounts

## 6. Admin Tools and API

- [x] 6.1 Create tools/tenant_admin_tools.py with service-gated toolset (check_fn verifies current profile is in admin_profiles list): user_list, user_get, user_create, user_update, user_link_identity, user_provision
- [x] 6.2 Register tenant_admin toolset in toolsets.py
- [x] 6.3 Create gateway/tenant/api.py with REST endpoints: GET/POST /api/tenants/users, GET/PATCH/DELETE /api/tenants/users/:id, POST /api/tenants/users/:id/identities, POST /api/tenants/users/:id/provision
- [x] 6.4 Mount tenant API routes in gateway/platforms/api_server.py (behind multi_tenant.enabled check)
- [x] 6.5 Write tests for admin tools: CRUD operations, permission gating (non-admin can't use), identity linking
- [x] 6.6 Write tests for API endpoints: auth required, CRUD flow, provisioning

## 7. CLI Subcommands

- [x] 7.1 Create hermes_cli/tenant.py with `hermes tenant` subcommands: list, add, remove, link, provision, status
- [x] 7.2 Wire into hermes_cli/main.py argparse
- [x] 7.3 `hermes tenant list` — show all registered users with their profiles and linked identities
- [x] 7.4 `hermes tenant add <username>` — create user + provision profile interactively
- [x] 7.5 `hermes tenant link <username> <platform> <platform_user_id>` — link IM identity
- [x] 7.6 `hermes tenant status` — show multi-tenant system status (DB connection, active containers, user count)

## 8. Claude Agent SDK Tenant Isolation

- [x] 8.1 When creating agent session in multi-tenant mode with SDK runtime, configure ClaudeAgentOptions with cwd=tenant_workspace_dir, setting_sources=[], and tenant-scoped env (CLAUDE_CONFIG_DIR, CLAUDE_CODE_DISABLE_AUTO_MEMORY)
- [x] 8.2 Ensure tenant's .claude directory (CLAUDE.md, project instructions) is provisioned during profile creation and mounted into container
- [x] 8.3 Write test verifying SDK options are correctly set per-tenant and no cross-contamination of settings/CLAUDE.md between tenants

## 9. Configuration and Integration

- [x] 9.1 Add gateway.multi_tenant section to DEFAULT_CONFIG in hermes_cli/config.py with all new keys and defaults
- [x] 9.2 Update gateway/config.py to load multi_tenant config and validate database_url presence when enabled
- [x] 9.3 Initialize TenantResolver and UserRegistry at gateway startup (in gateway/run.py GatewayRunner.__init__) when multi_tenant.enabled
- [x] 9.4 Add database connection health check to `hermes doctor` output
- [x] 9.5 Document setup in a skill or README section: PostgreSQL setup, config.yaml example, first-user registration flow

## 10. End-to-End Validation

- [x] 10.1 Integration test: full flow from IM message → identity resolution → profile scoping → agent creation with Docker terminal → command execution in container
- [x] 10.2 Integration test: auto-registration flow (unknown user → user created → profile provisioned → container started → response sent)
- [x] 10.3 Integration test: admin tool usage (admin profile can list/create/update users; tenant profile cannot)
- [x] 10.4 Verify existing single-user mode is unaffected when multi_tenant.enabled is false
- [x] 10.5 Verify Dockerfile.tenant builds and container starts with correct mounts
- [x] 10.6 Verify Claude SDK options isolation: two tenants' sessions have independent CLAUDE_CONFIG_DIR and no settings bleed
