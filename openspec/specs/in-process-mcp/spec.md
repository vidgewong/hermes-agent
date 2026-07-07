## ADDED Requirements

### Requirement: In-process MCP server for SDK runtime
The system SHALL expose Hermes tools to the Claude Code SDK runtime via an in-process MCP server (`McpSdkServerConfig` with `type: "sdk"`), executing tool handlers directly in the Hermes main process without spawning a subprocess.

#### Scenario: SDK session starts with in-process MCP
- **WHEN** the Claude Code SDK runtime initializes a session
- **THEN** `_build_hermes_tools_mcp_config(agent)` SHALL return an `McpSdkServerConfig` object (not a stdio dict)
- **AND** no MCP subprocess SHALL be spawned

#### Scenario: Tool handler executes in main process
- **WHEN** the Claude CLI invokes a Hermes MCP tool (e.g., `web_search`)
- **THEN** the tool handler SHALL execute in the Hermes main process address space
- **AND** the handler SHALL have access to the AIAgent instance via closure

#### Scenario: All non-blocked tools are registered
- **WHEN** the in-process MCP server is built
- **THEN** every tool from `get_tool_definitions()` that is not in the blocked set SHALL be registered as an `SdkMcpTool` with its name, description, and input_schema

### Requirement: AIAgent access for tool handlers
The system SHALL pass the live AIAgent instance to tool handlers that declare an `agent` parameter, enabling tools that were previously blocked due to subprocess isolation.

#### Scenario: delegate_task receives agent instance
- **WHEN** the `delegate_task` tool is invoked via in-process MCP
- **THEN** the handler SHALL receive the AIAgent instance
- **AND** the tool SHALL execute successfully (not return a "blocked" error)

#### Scenario: Tools without agent parameter are unaffected
- **WHEN** a tool handler does not declare an `agent` parameter (e.g., `web_search`)
- **THEN** the dispatch layer SHALL call it without the `agent` argument
- **AND** the tool SHALL continue to work as before

### Requirement: Error isolation in tool handlers
The system SHALL catch all exceptions from tool handlers and return structured error JSON to the SDK, preventing tool failures from crashing the Hermes main process.

#### Scenario: Tool handler raises an exception
- **WHEN** a tool handler raises any exception during execution
- **THEN** the in-process MCP handler wrapper SHALL catch the exception
- **AND** SHALL return `{"error": "<message>", "tool": "<name>"}` as the tool result
- **AND** the Hermes main process SHALL continue running

### Requirement: Graceful fallback to stdio mode
The system SHALL fall back to the existing stdio MCP subprocess if `claude-agent-sdk` does not support the in-process MCP API (version < 0.2.110).

#### Scenario: SDK version lacks in-process MCP support
- **WHEN** `create_sdk_mcp_server` or `SdkMcpTool` cannot be imported from `claude_agent_sdk`
- **THEN** the system SHALL log a warning and fall back to the stdio subprocess MCP config
- **AND** the session SHALL still start successfully with the subprocess-based MCP

### Requirement: Stateful tools use shared stores
The system SHALL instantiate `MemoryStore`, `TodoStore`, and `SessionDB` in the main process and share them with tool handlers, ensuring state consistency without IPC.

#### Scenario: Memory tool shares MemoryStore with main process
- **WHEN** the `memory` tool is invoked via in-process MCP
- **THEN** it SHALL use the same `MemoryStore` instance as the Hermes main process
- **AND** changes made by the tool SHALL be immediately visible to Hermes

#### Scenario: Todo state persists across turns
- **WHEN** a `todo` tool call creates a task in turn N
- **AND** a subsequent `todo` call reads tasks in turn N+1
- **THEN** the task created in turn N SHALL be present in the response
