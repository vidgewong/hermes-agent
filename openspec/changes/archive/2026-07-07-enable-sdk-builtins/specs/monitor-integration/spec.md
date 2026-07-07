## ADDED Requirements

### Requirement: Monitor built-in enabled for SDK sessions
The system SHALL enable the Claude Code SDK's Monitor built-in tool, allowing Claude to watch background processes and react to their output.

#### Scenario: Monitor available in SDK session
- **WHEN** a Claude Code SDK session is active
- **THEN** the `Monitor` tool SHALL NOT be in the `disallowed_tools` list
- **AND** Claude SHALL be able to use Monitor to watch background scripts

#### Scenario: Monitor operates within Claude CLI process
- **WHEN** Claude invokes the Monitor tool to watch a background script
- **THEN** the monitoring SHALL execute entirely within the Claude CLI subprocess
- **AND** no Hermes-side bridging or interception SHALL be required
- **AND** the monitored process events SHALL be visible in the SDK event stream

#### Scenario: Monitor events surfaced in Hermes event log
- **WHEN** Monitor emits events during a session
- **THEN** the events SHALL be captured by the existing `on_event` callback
- **AND** SHALL be logged in the Hermes session event stream for observability
