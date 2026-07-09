## MODIFIED Requirements

### Requirement: Per-tenant container lifecycle
The system SHALL manage a dedicated Docker container for each tenant profile, with start/stop/restart capabilities.

#### Scenario: Start tenant container
- **WHEN** the superuser runs `hermes tenant up <name>` or a message arrives for a stopped tenant
- **THEN** the system starts a container for that tenant with the tenant's profile mounted as `HERMES_HOME`

#### Scenario: Stop tenant container
- **WHEN** the superuser runs `hermes tenant down <name>`
- **THEN** the system gracefully stops the tenant's container (SIGTERM → timeout → SIGKILL)

#### Scenario: Container auto-start on message
- **WHEN** an inbound DM arrives for a tenant whose container is not running AND `tenants.auto_start: true`
- **THEN** the system starts the tenant's container before routing the message

### Requirement: Single-profile container view
The system SHALL render each tenant container as a standalone Hermes installation where the tenant profile appears as the root `~/.hermes/` directory.

#### Scenario: Container filesystem layout
- **WHEN** a tenant container starts
- **THEN** the container's `HERMES_HOME` (e.g., `/home/hermes/.hermes/`) contains only the tenant's profile contents — no `profiles/` subdirectory, no other tenant data

#### Scenario: Profile list inside container
- **WHEN** code inside the tenant container calls `list_profiles()`
- **THEN** only one profile is returned (the "default" which IS this tenant's data)

### Requirement: Container volume mounts include .claude and SOUL.md
The system SHALL mount the tenant's `.claude/` directory and (if present) the superuser's `SOUL.md` into every tenant container, in addition to the existing profile and code mounts.

#### Scenario: .claude directory is mounted read-write
- **WHEN** `generate_tenant_compose()` is called for tenant `alice`
- **THEN** the service definition includes `{profile_dir}/.claude:/home/hermes/.claude` (read-write)

#### Scenario: SOUL.md is mounted read-only when present
- **WHEN** `generate_tenant_compose()` is called and `{hermes_home}/SOUL.md` exists on the host
- **THEN** the service definition includes `{hermes_home}/SOUL.md:/home/hermes/.hermes/SOUL.md:ro`

#### Scenario: Missing SOUL.md does not block compose generation
- **WHEN** `{hermes_home}/SOUL.md` does not exist
- **THEN** `generate_tenant_compose()` omits the SOUL.md volume entry without error

### Requirement: Shared code mount
The system SHALL mount the superuser's `hermes-agent/` codebase read-only into all tenant containers to avoid duplicating the multi-GB installation.

#### Scenario: Code volume is read-only
- **WHEN** a tenant container's agent process attempts to write to the code directory
- **THEN** the write fails with a read-only filesystem error

#### Scenario: Code updates propagate to running containers
- **WHEN** the superuser updates Hermes (`hermes update`)
- **THEN** all tenant containers see the new code on their next process restart (no rebuild needed)

### Requirement: Container resource limits
The system SHALL apply configurable resource limits (memory, CPU) per tenant container.

#### Scenario: Default resource limits
- **WHEN** a tenant container starts without explicit resource config
- **THEN** the container runs with default limits: 2GB memory, 1 CPU core

#### Scenario: Custom resource limits
- **WHEN** a tenant's config declares `container.memory: "4g"` and `container.cpus: "2"`
- **THEN** the container starts with those resource constraints
