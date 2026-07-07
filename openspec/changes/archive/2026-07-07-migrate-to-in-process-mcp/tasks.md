## 1. In-Process MCP Server Builder

- [x] 1.1 Create `agent/in_process_mcp.py` with `build_hermes_in_process_mcp(agent)` function that constructs an `McpSdkServerConfig` using `create_sdk_mcp_server` / `SdkMcpTool`
- [x] 1.2 Register all non-blocked tools from `get_tool_definitions()` as `SdkMcpTool` entries with correct name, description, and input_schema
- [x] 1.3 Implement top-level exception handler wrapper for each tool handler that catches all exceptions and returns `{"error": ..., "tool": ...}` JSON
- [x] 1.4 Register stateful tools (memory, todo, session_search) with shared store instances (no separate per-process stores needed since we're in-process)

## 2. AIAgent Access for Tool Handlers

- [x] 2.1 Modify `handle_function_call()` in `model_tools.py` to accept an optional `agent` keyword argument and forward it to tool handlers that declare it
- [x] 2.2 Update `delegate_task` handler to accept and use the `agent` parameter for gateway session routing and depth tracking
- [x] 2.3 Update `read_terminal` and `close_terminal` handlers to accept and use the `agent` parameter for terminal environment access
- [x] 2.4 Reduce `_BLOCKED_TOOLS` set to only `clarify` and `computer_use`

## 3. SDK Runtime Integration

- [x] 3.1 Rewrite `_build_hermes_tools_mcp_config()` in `agent/claude_code_sdk_runtime.py` to accept `agent` parameter and return `McpSdkServerConfig` (in-process) instead of stdio dict
- [x] 3.2 Add version check: if `create_sdk_mcp_server` is not importable, fall back to existing stdio config with a warning log
- [x] 3.3 Update the call site in `_start_session()` to pass the agent instance to the builder
- [x] 3.4 Update `ClaudeCodeSession.__init__` type annotation for `mcp_servers` to accept both dict and `McpSdkServerConfig` objects

## 4. Cleanup and Deprecation

- [x] 4.1 Add deprecation docstring to `agent/transports/hermes_tools_mcp_server.py` marking it as standalone-only (not used by SDK runtime)
- [x] 4.2 Remove PYTHONPATH/env forwarding logic from the old `_build_hermes_tools_mcp_config()` (now dead code)
- [x] 4.3 Remove the `_build_memory_tools()` special-casing from the in-process path (stores are shared directly)

## 5. Testing and Verification

- [x] 5.1 Add unit test for `build_hermes_in_process_mcp()`: verify it returns `McpSdkServerConfig`, all expected tools are registered, blocked tools are excluded
- [x] 5.2 Add unit test for error isolation: mock a tool handler that raises, verify JSON error is returned without crashing
- [x] 5.3 Add integration test: start a session with in-process MCP, invoke `delegate_task`, verify it executes (not blocked)
- [x] 5.4 Add fallback test: mock missing `create_sdk_mcp_server` import, verify stdio config is returned
- [ ] 5.5 Manual verification: run a full Claude Code SDK session, confirm tools work end-to-end with no subprocess spawned
