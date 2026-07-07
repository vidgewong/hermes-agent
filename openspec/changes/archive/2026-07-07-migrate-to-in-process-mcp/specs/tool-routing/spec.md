## MODIFIED Requirements

### Requirement: Minimal tool blocklist for SDK runtime
The system SHALL only block tools that genuinely cannot function in the SDK context. Tools that were previously blocked solely due to subprocess isolation (needing AIAgent access) SHALL be unblocked now that handlers execute in-process.

#### Scenario: Blocked tools — reduced to true incompatibilities
- **WHEN** the in-process MCP server initializes
- **THEN** the blocked tools set SHALL contain only: `clarify`, `computer_use`
- **AND** `delegate_task`, `read_terminal`, `close_terminal` SHALL NOT be in the blocked set

#### Scenario: delegate_task is available in SDK mode
- **WHEN** the Claude Code SDK runtime is active with in-process MCP
- **THEN** `delegate_task` SHALL be exposed as an available MCP tool
- **AND** it SHALL function correctly using the AIAgent instance from the closure

#### Scenario: read_terminal and close_terminal are available
- **WHEN** the Claude Code SDK runtime is active with in-process MCP
- **THEN** `read_terminal` and `close_terminal` SHALL be exposed as available MCP tools
- **AND** they SHALL access the terminal environment manager from the AIAgent instance

#### Scenario: Native runtime is unaffected
- **WHEN** the active runtime is the native Python loop
- **THEN** the tool dispatch SHALL not be affected by this change (no change to existing behavior)

## ADDED Requirements

### Requirement: Claude Code built-in deduplication remains unchanged
The `disallowed_tools` list in `ClaudeCodeSession` that blocks Claude Code built-ins (Bash, Read, Write, etc.) to prevent duplication with Hermes equivalents SHALL remain unchanged by this migration.

#### Scenario: Built-in tools still blocked for deduplication
- **WHEN** the Claude Code SDK session is configured with in-process MCP
- **THEN** the `disallowed_tools` list SHALL still contain: Bash, Read, Write, Edit, Glob, Grep, Agent, Workflow, WebFetch, and all deferred built-ins
- **AND** this list SHALL be independent of the MCP tool blocklist (they serve different purposes)
