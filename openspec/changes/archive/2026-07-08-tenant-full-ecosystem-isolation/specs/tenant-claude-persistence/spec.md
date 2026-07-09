## ADDED Requirements

### Requirement: Tenant profile includes a persistent .claude directory
Each tenant profile directory on the host SHALL contain a `.claude/` subdirectory that persists across container restarts. The directory SHALL be created automatically during tenant provisioning if it does not already exist.

#### Scenario: Fresh tenant provisioning creates .claude directory
- **WHEN** `provision_tenant()` is called for a new tenant named `alice`
- **THEN** the directory `~/.hermes/profiles/alice/.claude/` is created on the host with mode `0700`

#### Scenario: Container mounts .claude as home directory
- **WHEN** `generate_tenant_compose()` produces a compose file for tenant `alice`
- **THEN** the service definition includes a volume entry `{profile_dir}/.claude:/home/hermes/.claude` (read-write, no `:ro`)

#### Scenario: SkillGateway writes durable symlinks after restart
- **WHEN** a tenant container for `alice` is stopped and restarted
- **THEN** symlinks previously written to `/home/hermes/.claude/skills/` by `SkillGateway` are still present after restart

#### Scenario: MemoryWatcher persists CLAUDE.md across restarts
- **WHEN** `MemoryWatcher` syncs Hermes memory to `/home/hermes/.claude/CLAUDE.md` inside a tenant container
- **THEN** the file survives container restart because it resides on the host-mounted volume

#### Scenario: Existing .claude directory is not overwritten on re-provision
- **WHEN** `provision_tenant()` is called for a tenant that already has a `.claude/` directory with existing content
- **THEN** the existing `.claude/` directory and its contents are preserved unchanged
