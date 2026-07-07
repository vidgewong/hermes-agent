### Requirement: Minimal tool blocklist for SDK runtime
The system SHALL only block Claude Code built-in tools that directly conflict with Hermes orchestration or have no meaning in the Hermes context. Tools that provide additive capabilities (user interaction, monitoring, subagents) SHALL be enabled.

#### Scenario: Blocked tools — orchestration conflicts and duplicates only
- **WHEN** the Claude Code SDK runtime initializes
- **THEN** `disallowed_tools` SHALL contain: `Workflow`, `EnterWorktree`, `ExitWorktree`, `SendMessage` (orchestration conflicts)
- **AND** `disallowed_tools` SHALL contain: `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch` (replaced by Hermes MCP equivalents)
- **AND** `disallowed_tools` SHALL contain: `CronCreate`, `CronDelete`, `CronList`, `ScheduleWakeup`, `TaskCreate`, `TaskGet`, `TaskList`, `TaskOutput`, `TaskStop`, `TaskUpdate` (replaced by Hermes equivalents)
- **AND** `disallowed_tools` SHALL contain: `LSP`, `NotebookEdit`, `ToolSearch`, `ReportFindings`, `Skill` (not applicable or replaced)
- **AND** `disallowed_tools` SHALL NOT contain: `AskUserQuestion`, `Agent`, `Monitor`

#### Scenario: AskUserQuestion is enabled
- **WHEN** the Claude Code SDK runtime is active
- **THEN** `AskUserQuestion` SHALL NOT be in `disallowed_tools`
- **AND** it SHALL be handled by the `canUseTool` callback (not auto-approved silently)

#### Scenario: Agent tool is enabled
- **WHEN** the Claude Code SDK runtime is active
- **THEN** `Agent` SHALL NOT be in `disallowed_tools`
- **AND** it SHALL be auto-approved (included in `allowed_tools`)

#### Scenario: Monitor tool is enabled
- **WHEN** the Claude Code SDK runtime is active
- **THEN** `Monitor` SHALL NOT be in `disallowed_tools`
- **AND** it SHALL be auto-approved (included in `allowed_tools`)

### Requirement: Minimal MCP tool blocklist for in-process server
The system SHALL only block MCP tools that genuinely cannot function in the SDK context. Tools previously blocked due to subprocess isolation (needing AIAgent access) SHALL be unblocked now that handlers execute in-process.

#### Scenario: MCP blocked tools — reduced to true incompatibilities
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

### Requirement: MCP surface deduplication in SDK runtime
The system SHALL not expose tools via the Hermes MCP server that duplicate enabled Claude Code built-ins, to prevent the model from seeing redundant overlapping tool options.

#### Scenario: Overlapping MCP tools filtered in SDK mode
- **WHEN** the Hermes MCP server initializes for a Claude Code SDK session
- **THEN** the following tools SHALL be excluded from the MCP tool list: `terminal`, `read_file`, `write_file`, `patch`, `search_files`

#### Scenario: Hermes-unique MCP tools remain available
- **WHEN** the Hermes MCP server is filtered for SDK mode
- **THEN** Hermes-unique tools SHALL remain exposed: `cronjob`, `skill_view`, `skills_list`, `skill_manage`, `send_message`, `web_search`, `web_extract`, browser tools, image generation, and other Hermes-specific capabilities

#### Scenario: Native runtime is unaffected
- **WHEN** the active runtime is the native Python loop
- **THEN** the tool dispatch and MCP tool list SHALL not be affected by these changes

### Requirement: Cron tool description clarifies delivery model
The system SHALL update the `cronjob` MCP tool description to make clear when to use Hermes cron vs Claude Code's built-in CronCreate.

#### Scenario: User can distinguish cron tools
- **WHEN** the model or user inspects the available cron tools
- **THEN** the `cronjob` MCP tool description SHALL state that it creates Hermes-managed jobs with Feishu/chat delivery, while the built-in `CronCreate` creates local scheduled tasks without Hermes delivery
