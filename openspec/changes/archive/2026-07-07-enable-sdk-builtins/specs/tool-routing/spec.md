## MODIFIED Requirements

### Requirement: Minimal tool blocklist for SDK runtime
The system SHALL only block Claude Code built-in tools that directly conflict with Hermes orchestration or have no meaning in the Hermes context. Tools that provide additive capabilities (user interaction, monitoring, subagents) SHALL be enabled.

#### Scenario: Blocked tools — reduced to orchestration conflicts and duplicates only
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
