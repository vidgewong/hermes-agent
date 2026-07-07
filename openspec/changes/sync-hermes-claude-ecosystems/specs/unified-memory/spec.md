## ADDED Requirements

### Requirement: Memory bidirectional sync
The system SHALL synchronize memory content between Hermes' memory system (`~/.hermes/hermes-agent/memory/MEMORY.md` + fragment files) and Claude Code's memory system, so that memories saved by either runtime are visible to the other.

#### Scenario: Hermes memory update synced to Claude Code
- **WHEN** the Hermes native runtime saves a new memory fragment (e.g., `~/.hermes/hermes-agent/memory/feedback_testing.md`)
- **THEN** the system SHALL translate the memory content into Claude Code's memory format and write it to `~/.claude/` so that Claude Code sessions can access it

#### Scenario: Claude Code memory update synced to Hermes
- **WHEN** the Claude Code SDK runtime saves a memory via its built-in memory system
- **THEN** the system SHALL translate the memory into a Hermes memory fragment file with appropriate frontmatter (name, description, type) and update `MEMORY.md` index

### Requirement: Project instruction synchronization
The system SHALL synchronize project-level instructions between Hermes' `SOUL.md` and Claude Code's `CLAUDE.md` at the project root level.

#### Scenario: SOUL.md changes reflected in CLAUDE.md
- **WHEN** `SOUL.md` in a project directory is modified
- **THEN** the system SHALL update or create a corresponding `CLAUDE.md` in that project directory with equivalent content, prepended with a comment indicating it is auto-synced from SOUL.md

#### Scenario: CLAUDE.md changes reflected in SOUL.md
- **WHEN** `CLAUDE.md` in a project directory is modified by Claude Code
- **THEN** the system SHALL update `SOUL.md` with the new content, preserving any Hermes-specific sections (e.g., channel routing rules, platform-specific instructions) that have no Claude Code equivalent

#### Scenario: Project-scoped memory sync
- **WHEN** Claude Code creates project-scoped memories under `~/.claude/projects/<project>/memory/`
- **THEN** the system SHALL merge these into the corresponding Hermes project memory directory, translating format as needed

### Requirement: Memory format translation
The system SHALL provide a translation layer that converts between Hermes memory format (YAML frontmatter + markdown body) and Claude Code's memory format.

#### Scenario: Hermes to Claude Code translation
- **WHEN** a Hermes memory fragment with frontmatter (name, description, metadata.type) is synced to Claude Code
- **THEN** the translator SHALL produce a file in Claude Code's expected location and format, preserving the semantic content while adapting structure

#### Scenario: Claude Code to Hermes translation
- **WHEN** a Claude Code memory entry is synced to Hermes
- **THEN** the translator SHALL infer appropriate Hermes frontmatter fields (type from content analysis, name from filename, description from first line) and create a properly structured fragment file

#### Scenario: Unrecognized memory format
- **WHEN** a memory file cannot be parsed by the translator (corrupted or unknown format)
- **THEN** the system SHALL log a warning, skip the file, and not corrupt the other ecosystem's memory store

### Requirement: Memory deduplication across ecosystems
The system SHALL detect duplicate memories (same semantic content saved by both runtimes) and consolidate them into a single entry rather than creating duplicates.

#### Scenario: Duplicate detection by content hash
- **WHEN** both ecosystems contain memory entries with the same content hash (ignoring formatting differences)
- **THEN** the system SHALL treat them as the same memory and not create a second entry during sync

#### Scenario: Near-duplicate detection
- **WHEN** memories differ only in minor phrasing but describe the same fact (same name slug, overlapping description)
- **THEN** the system SHALL keep the more recent version and log that a potential duplicate was consolidated

### Requirement: Memory sync respects ecosystem boundaries
The system SHALL not sync memories that are ecosystem-specific and would be meaningless in the other context.

#### Scenario: Hermes channel-specific memories excluded
- **WHEN** a Hermes memory references internal infrastructure (channel IDs, gateway state, Feishu-specific context) that Claude Code cannot act on
- **THEN** the system SHALL still sync the memory (for context) but MAY mark it with metadata indicating it originated from Hermes

#### Scenario: Claude Code session metadata excluded
- **WHEN** Claude Code stores session-specific data (file history, shell snapshots, paste cache) in `~/.claude/`
- **THEN** the system SHALL NOT sync these operational files — only explicit memory/skill content is synced
