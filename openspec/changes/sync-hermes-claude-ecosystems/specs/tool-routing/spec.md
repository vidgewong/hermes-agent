## ADDED Requirements

### Requirement: Minimal tool blocklist for SDK runtime
The system SHALL only block Claude Code built-in tools that directly conflict with Hermes orchestration: `Agent`, `Workflow`, `SendMessage`, `EnterWorktree`, `ExitWorktree`. All other built-in tools (Bash, Read, Write, Edit, Skill, TaskCreate, CronCreate, WebFetch, etc.) SHALL be enabled.

#### Scenario: File operations use Claude Code built-ins
- **WHEN** the Claude Code SDK runtime is active and the model requests a file operation (Read, Write, Edit)
- **THEN** Claude Code's native built-in tool SHALL handle the operation directly without routing through Hermes MCP

#### Scenario: Orchestration tools remain blocked
- **WHEN** the Claude Code SDK runtime is active
- **THEN** the tools `Agent`, `Workflow`, `SendMessage`, `EnterWorktree`, and `ExitWorktree` SHALL remain in the `disallowed_tools` list to prevent Claude Code from spawning its own sub-agents or workflows outside Hermes control

#### Scenario: Hermes MCP tools remain accessible
- **WHEN** Claude Code built-in tools are enabled alongside the Hermes MCP server
- **THEN** Hermes-specific MCP tools (messaging, gateway, channel management, Hermes skill operations) SHALL remain accessible via the `mcp__hermes-tools__` namespace

### Requirement: Runtime-aware tool preference
The system SHALL route tool calls based on the active runtime mode: Claude Code built-ins are primary in SDK runtime mode; Hermes tools are primary in native runtime mode.

#### Scenario: SDK runtime prefers Claude Code tools
- **WHEN** the active runtime is `claude_code_sdk` and a tool call can be handled by either a Claude Code built-in or a Hermes MCP tool
- **THEN** the Claude Code built-in SHALL be used (it is natively available to the model without the `mcp__hermes-tools__` prefix)

#### Scenario: Native runtime uses Hermes tools
- **WHEN** the active runtime is the native Python loop
- **THEN** all tool calls SHALL route through Hermes' native tool registry as before (no change to existing behavior)

### Requirement: Tool deduplication in system prompt
The system SHALL not expose duplicate tool capabilities (e.g., both `Bash` and `mcp__hermes-tools__terminal`) when Claude Code built-ins are enabled, to avoid confusing the model with redundant options.

#### Scenario: Overlapping tools removed from MCP surface
- **WHEN** the Claude Code SDK runtime is active with built-in tools enabled
- **THEN** the Hermes MCP server SHALL NOT expose tools that duplicate Claude Code built-ins (terminal, read_file, write_file, patch, search_files) — only Hermes-unique tools SHALL be exposed via MCP

#### Scenario: MCP tool list adapts to runtime mode
- **WHEN** the Hermes MCP server initializes for a Claude Code SDK session
- **THEN** the server SHALL check the runtime mode and filter its tool list to exclude tools that overlap with enabled Claude Code built-ins

### Requirement: Skill tool routing
The system SHALL enable Claude Code's native `Skill` tool, which reads from `~/.claude/skills/`, since the ecosystem sync keeps that directory up-to-date with Hermes skills.

#### Scenario: Claude Code Skill tool uses synced skills
- **WHEN** the Claude Code SDK runtime invokes the `Skill` tool
- **THEN** it SHALL find Hermes skills in `~/.claude/skills/` because the ecosystem sync has mirrored them there

#### Scenario: Hermes-only skill context available via MCP
- **WHEN** a skill requires Hermes-specific runtime context (e.g., active channel, gateway state) that Claude Code's Skill tool cannot provide
- **THEN** the Hermes MCP server SHALL expose `skill_view` and `skill_manage` tools that provide this additional context
