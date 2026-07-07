## ADDED Requirements

### Requirement: Session-start skill reconciliation
The system SHALL, at the start of each Claude Code SDK session, reconcile Hermes skills into `~/.agents/skills/` so that Claude Code's native Skill tool can find them.

#### Scenario: Hermes skill made available to Claude Code Skill tool
- **WHEN** a Claude Code SDK session starts
- **THEN** the system SHALL scan `~/.hermes/skills/` recursively for `SKILL.md` files and create a symlink `~/.agents/skills/<name>` pointing to each skill's parent directory, for any skill not already present in `~/.agents/skills/`

#### Scenario: Claude skills symlink kept consistent
- **WHEN** a new symlink is created in `~/.agents/skills/<name>`
- **THEN** the system SHALL also create `~/.claude/skills/<name>` → `~/.agents/skills/<name>` if that symlink does not already exist

#### Scenario: Reconcile is idempotent
- **WHEN** reconcile is called and all Hermes skills already have correct symlinks
- **THEN** the system SHALL make no filesystem changes and complete without error

### Requirement: Skill name collision handling
The system SHALL not overwrite an existing non-Hermes entry in `~/.agents/skills/` during reconciliation.

#### Scenario: Name collision — Claude Code entry wins
- **WHEN** `~/.agents/skills/<name>` already exists and is NOT a symlink to the Hermes skill directory for that name
- **THEN** the system SHALL skip creating the Hermes symlink for that name and append a collision entry to `~/.hermes/sync/skill_collisions.log` with the Hermes path, the existing path, and a timestamp

#### Scenario: Correct symlink already present
- **WHEN** `~/.agents/skills/<name>` already exists as a symlink pointing to the correct Hermes skill directory
- **THEN** the system SHALL treat it as already reconciled and take no action
