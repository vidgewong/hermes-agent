## ADDED Requirements

### Requirement: Hermes memory context injected into SDK session system prompt
The system SHALL inject the Hermes memory snapshot into the Claude Code SDK session's system prompt append block at session start, so that Claude Code sessions have access to the user's memory context without requiring a global CLAUDE.md file.

#### Scenario: Memory snapshot appended to SDK system prompt
- **WHEN** a Claude Code SDK session is initialized and Hermes memory fragments exist under `~/.hermes/hermes-agent/memory/`
- **THEN** the system SHALL build a memory context block from the MEMORY.md fragments (grouped by type: user, feedback, project, reference) and append it to the `append` field of the `_sdk_system_prompt` object passed to `ClaudeAgentOptions`

#### Scenario: user.me included when present
- **WHEN** `~/.hermes/user.me` exists
- **THEN** the system SHALL prepend its content as a "User Profile" section before the memory fragments in the appended block

#### Scenario: No memory files present
- **WHEN** no MEMORY.md fragments or user.me exist
- **THEN** the system SHALL not modify the system prompt append block (no empty section injected)

### Requirement: Memory snapshot size cap
The system SHALL enforce a size cap on the injected memory block to avoid bloating the SDK session's context.

#### Scenario: Snapshot within cap
- **WHEN** the formatted memory block is at or below 4KB
- **THEN** the system SHALL inject the full block without truncation

#### Scenario: Snapshot exceeds cap
- **WHEN** the formatted memory block exceeds 4KB
- **THEN** the system SHALL truncate lower-priority entries (project and reference types first, then older feedback entries) until the block fits within 4KB, and append a note indicating that some memory entries were omitted due to size limits
