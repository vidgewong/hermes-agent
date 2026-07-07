## ADDED Requirements

### Requirement: Bidirectional skill synchronization
The system SHALL synchronize skill files between `~/.hermes/skills/` and `~/.claude/skills/` such that a skill created or modified in one location is reflected in the other within 5 seconds.

#### Scenario: Skill created in Hermes is available in Claude Code
- **WHEN** a new skill file is created at `~/.hermes/skills/<name>/skill.md`
- **THEN** the system SHALL create a corresponding skill at `~/.claude/skills/<name>.md` with equivalent content translated to Claude Code's expected format

#### Scenario: Skill modified in Claude Code is reflected in Hermes
- **WHEN** a skill file at `~/.claude/skills/<name>.md` is modified
- **THEN** the system SHALL update `~/.hermes/skills/<name>/skill.md` with the translated content, preserving Hermes-specific frontmatter fields that have no Claude Code equivalent

#### Scenario: Skill deleted in one ecosystem
- **WHEN** a skill file is deleted in either `~/.hermes/skills/` or `~/.claude/skills/`
- **THEN** the system SHALL delete the corresponding file in the other ecosystem and log the deletion to `~/.hermes/sync/sync.log`

### Requirement: Filesystem watcher daemon
The system SHALL run a background filesystem watcher that monitors both `~/.hermes/` and `~/.claude/` for changes to syncable content (skills, memory, project instructions).

#### Scenario: Watcher detects file change
- **WHEN** a file within a watched directory is created, modified, or deleted
- **THEN** the system SHALL trigger the appropriate sync translator within 5 seconds of the filesystem event

#### Scenario: Watcher daemon startup
- **WHEN** the Hermes gateway process starts
- **THEN** the filesystem watcher SHALL start automatically and perform an initial full reconciliation pass

#### Scenario: Watcher daemon crash recovery
- **WHEN** the filesystem watcher process terminates unexpectedly
- **THEN** session lifecycle hooks SHALL still trigger sync at session start and session end, providing degraded but functional synchronization

### Requirement: Session lifecycle sync hooks
The system SHALL trigger a full synchronization pass at the beginning and end of each agent session, regardless of whether the filesystem watcher is running.

#### Scenario: Sync on session start
- **WHEN** a new agent session begins (either native or SDK runtime)
- **THEN** the system SHALL perform a full bidirectional reconciliation before processing the first user message

#### Scenario: Sync on session end
- **WHEN** an agent session ends (user exits, timeout, or crash)
- **THEN** the system SHALL perform a final sync pass to capture any changes made during the session

### Requirement: Content-hash deduplication
The system SHALL compare file content hashes before writing to avoid unnecessary disk writes and prevent sync loops.

#### Scenario: Identical content skipped
- **WHEN** a sync event is triggered but the source and target files have identical content (same SHA-256 hash)
- **THEN** the system SHALL skip the write operation and not update the target file's mtime

#### Scenario: Sync loop prevention
- **WHEN** the system writes a file as part of sync
- **THEN** the system SHALL suppress the resulting filesystem event to prevent an infinite sync loop between the two ecosystems

### Requirement: Conflict resolution with audit log
The system SHALL resolve conflicts using last-write-wins (most recent mtime) and log all conflicts to `~/.hermes/sync/conflicts.log`.

#### Scenario: Concurrent modification conflict
- **WHEN** the same logical content is modified in both `~/.hermes/` and `~/.claude/` between sync cycles
- **THEN** the system SHALL keep the version with the most recent mtime, write it to the other side, and append a conflict entry to the log including both file paths, timestamps, and which side won

#### Scenario: Conflict log review
- **WHEN** a user queries the sync status (via CLI or TUI)
- **THEN** the system SHALL display recent conflicts from the audit log with enough detail to manually recover the overwritten version

### Requirement: Sync configuration
The system SHALL read sync configuration from `~/.hermes/config.yaml` under the `ecosystem_sync` key, allowing users to enable/disable sync, set intervals, and exclude patterns.

#### Scenario: Sync disabled by config
- **WHEN** `ecosystem_sync.enabled` is set to `false` in config.yaml
- **THEN** the system SHALL not start the filesystem watcher and SHALL not perform session lifecycle syncs

#### Scenario: Custom exclude patterns
- **WHEN** `ecosystem_sync.exclude_patterns` contains glob patterns
- **THEN** the system SHALL not sync files matching those patterns in either direction
