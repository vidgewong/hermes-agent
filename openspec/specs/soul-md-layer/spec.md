## ADDED Requirements

### Requirement: SOUL.md is a platform-wide personality file in superuser HERMES_HOME
The superuser's `HERMES_HOME` SHALL support an optional `SOUL.md` file that defines the agent's global personality, safety constraints, and platform-level behaviour rules. Its presence is operator opt-in; absence is silently ignored.

#### Scenario: SOUL.md file is created by operator
- **WHEN** the operator creates `~/.hermes/SOUL.md` with personality content
- **THEN** the file is recognised by the system without any config change required

#### Scenario: Missing SOUL.md does not affect system behaviour
- **WHEN** `~/.hermes/SOUL.md` does not exist
- **THEN** all tenant containers and the superuser session start normally without error

### Requirement: SOUL.md is mounted read-only into every tenant container
`generate_tenant_compose()` SHALL add a bind-mount entry for `SOUL.md` in every (non-suspended) tenant service definition. The mount SHALL be read-only.

#### Scenario: Compose file includes SOUL.md mount when file exists
- **WHEN** `~/.hermes/SOUL.md` exists and `generate_tenant_compose()` is called
- **THEN** each tenant service definition includes `{hermes_home}/SOUL.md:/home/hermes/.hermes/SOUL.md:ro`

#### Scenario: Compose generation skips SOUL.md mount when file absent
- **WHEN** `~/.hermes/SOUL.md` does not exist and `generate_tenant_compose()` is called
- **THEN** no SOUL.md volume entry is added (preventing Docker "source path not found" errors)

### Requirement: System prompt builder prepends SOUL.md before CLAUDE.md
The agent session startup SHALL read `SOUL.md` from `HERMES_HOME` (if present) and prepend its content to the system prompt before any tenant-specific `CLAUDE.md` content.

#### Scenario: SOUL.md content appears before CLAUDE.md in system prompt
- **WHEN** both `SOUL.md` and `CLAUDE.md` are present at session start
- **THEN** the constructed system prompt contains SOUL.md content first, followed by CLAUDE.md content, in that order

#### Scenario: Tenant cannot override SOUL.md via their CLAUDE.md
- **WHEN** a tenant's `CLAUDE.md` contains instructions that contradict SOUL.md
- **THEN** the system prompt still presents SOUL.md content before CLAUDE.md (precedence is by position — SOUL.md is the opening context)

#### Scenario: SOUL.md hot-reload on next turn
- **WHEN** the operator modifies `SOUL.md` on the host while a tenant container is running
- **THEN** the next agent turn reads the updated file (no container restart required), because SOUL.md is read from the bind-mounted path at turn start
