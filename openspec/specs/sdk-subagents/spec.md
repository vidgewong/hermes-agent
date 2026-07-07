## ADDED Requirements

### Requirement: Agent built-in enabled for SDK sessions
The system SHALL enable the Claude Code SDK's Agent built-in tool, allowing Claude to spawn native SDK subagents alongside Hermes' delegate_task.

#### Scenario: Agent tool available in SDK session
- **WHEN** a Claude Code SDK session is active
- **THEN** the `Agent` tool SHALL NOT be in the `disallowed_tools` list
- **AND** Claude SHALL be able to spawn subagents via the Agent tool

#### Scenario: Agent tool coexists with delegate_task
- **WHEN** both Agent (built-in) and delegate_task (MCP) are available
- **THEN** Claude SHALL be able to use either mechanism for subtask delegation
- **AND** the system prompt SHALL provide guidance on when to use each

### Requirement: Hermes subagent definitions registered as AgentDefinition
The system SHALL register Hermes-specific subagent profiles as `AgentDefinition` entries in the SDK session's `agents` parameter, making them discoverable and invocable through the Agent tool.

#### Scenario: Hermes agent profiles available at session start
- **WHEN** a Claude Code SDK session is initialized
- **THEN** `ClaudeAgentOptions.agents` SHALL contain AgentDefinition entries derived from Hermes' subagent profiles
- **AND** each definition SHALL have a description, prompt, and appropriate tool restrictions

#### Scenario: Subagent has access to Hermes MCP tools
- **WHEN** an SDK subagent is spawned via the Agent tool
- **THEN** the subagent SHALL have access to Hermes MCP tools (via the in-process MCP server)
- **AND** the subagent SHALL be able to call web_search, browser tools, memory, etc.

#### Scenario: Subagent definitions derived from Hermes skill profiles
- **WHEN** Hermes has skills or profiles that function as agent roles (e.g., code-reviewer, researcher)
- **THEN** those SHALL be converted to AgentDefinition format with appropriate description, prompt, and tools fields
- **AND** SHALL be included in the `agents` dict passed to the SDK

### Requirement: System prompt guidance for dual subagent systems
The system SHALL include guidance in the system prompt explaining when to use the SDK Agent tool vs Hermes' delegate_task.

#### Scenario: System prompt contains delegation guidance
- **WHEN** the Claude Code SDK session starts with both Agent and delegate_task available
- **THEN** the system prompt SHALL explain: use Agent for focused subtasks with context isolation and tool restrictions; use delegate_task for Hermes-aware work that needs gateway routing, depth tracking, or background result delivery
