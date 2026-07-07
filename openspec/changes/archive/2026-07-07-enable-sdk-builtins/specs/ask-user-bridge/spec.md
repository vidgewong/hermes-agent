## ADDED Requirements

### Requirement: AskUserQuestion bridged to Hermes user interaction surfaces
The system SHALL handle the SDK's AskUserQuestion tool calls by bridging them to Hermes' user interaction infrastructure (gateway for Feishu/Web, TUI for interactive terminal sessions), collecting the user's answer, and returning it to the SDK in the expected format.

#### Scenario: AskUserQuestion via gateway (Feishu/Web)
- **WHEN** Claude calls AskUserQuestion during a gateway session
- **THEN** the `canUseTool` callback SHALL translate the question into Hermes' blocking-prompt format
- **AND** SHALL send the question (with options) to the user via the gateway channel (Feishu message / Web UI)
- **AND** SHALL block until the user responds
- **AND** SHALL return `PermissionResultAllow(updated_input={questions, answers})` with the user's selections

#### Scenario: AskUserQuestion via TUI (interactive terminal)
- **WHEN** Claude calls AskUserQuestion during an interactive TUI session
- **THEN** the `canUseTool` callback SHALL render the question and numbered options in the terminal
- **AND** SHALL accept the user's input (number selection or free text)
- **AND** SHALL return the answer in SDK format

#### Scenario: AskUserQuestion in headless/cron mode
- **WHEN** Claude calls AskUserQuestion during a cron or headless session (no user available)
- **THEN** the `canUseTool` callback SHALL return `PermissionResultDeny(message="No user available in headless mode — make a reasonable decision or skip this step")`
- **AND** Claude SHALL proceed without user input

#### Scenario: Multi-select questions
- **WHEN** the AskUserQuestion call contains a question with `multiSelect: true`
- **THEN** the bridge SHALL allow the user to select multiple options
- **AND** SHALL return the selections as a comma-separated string or array of labels

#### Scenario: Free-text "Other" response
- **WHEN** the user provides free text instead of selecting a predefined option
- **THEN** the bridge SHALL use the user's text as the answer value directly
- **AND** SHALL NOT return the literal string "Other"

### Requirement: canUseTool callback registered for SDK sessions
The system SHALL pass a `canUseTool` callback in the `ClaudeAgentOptions` to handle AskUserQuestion and any future tools that require user interaction.

#### Scenario: Callback registered at session creation
- **WHEN** a Claude Code SDK session is initialized
- **THEN** the `ClaudeAgentOptions` SHALL include a `can_use_tool` callback
- **AND** the callback SHALL handle `AskUserQuestion` by bridging to the appropriate surface
- **AND** the callback SHALL auto-allow all other tool calls (Hermes handles its own guardrails via in-process MCP)
