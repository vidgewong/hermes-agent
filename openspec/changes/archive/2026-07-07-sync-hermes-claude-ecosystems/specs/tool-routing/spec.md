## ADDED Requirements

### Requirement: Minimal tool blocklist for SDK runtime
The system SHALL only block Claude Code built-in tools that directly conflict with Hermes orchestration. All other built-in tools SHALL be enabled.

#### Scenario: Blocked tools — orchestration conflicts only
- **WHEN** the Claude Code SDK runtime initializes
- **THEN** `disallowed_tools` SHALL contain exactly: `Agent`, `Workflow`, `SendMessage`, `EnterWorktree`, `ExitWorktree` — and no others

#### Scenario: File and shell tools are enabled
- **WHEN** the Claude Code SDK runtime is active and the model requests a file or shell operation (Read, Write, Edit, Bash, Glob, Grep)
- **THEN** Claude Code's native built-in tool SHALL handle the operation directly

#### Scenario: Cron and task tools are enabled
- **WHEN** the Claude Code SDK runtime is active
- **THEN** CronCreate, CronDelete, CronList, ScheduleWakeup, TaskCreate, TaskGet, TaskList, TaskOutput, TaskStop, TaskUpdate SHALL be available as Claude Code built-ins

#### Scenario: Skill tool is enabled and finds Hermes skills
- **WHEN** the Claude Code SDK runtime invokes the `Skill` tool
- **THEN** it SHALL find Hermes-originated skills in `~/.claude/skills/` because the skill gateway reconcile has symlinked them at session start

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
- **THEN** the Hermes MCP server tool list SHALL not be filtered (no change to existing behavior)

### Requirement: Cron tool description clarifies delivery model
The system SHALL update the `cronjob` MCP tool description to make clear when to use Hermes cron vs Claude Code's built-in CronCreate.

#### Scenario: User can distinguish cron tools
- **WHEN** the model or user inspects the available cron tools
- **THEN** the `cronjob` MCP tool description SHALL state that it creates Hermes-managed jobs with Feishu/chat delivery, while the built-in `CronCreate` creates local scheduled tasks without Hermes delivery
