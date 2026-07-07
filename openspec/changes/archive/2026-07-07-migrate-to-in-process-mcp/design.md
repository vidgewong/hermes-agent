## Context

The Claude Code SDK runtime (`agent/claude_code_sdk_runtime.py`) uses a stdio MCP subprocess to expose Hermes tools to the Claude CLI process. This architecture was necessary before SDK 0.2.110 because the SDK only supported external MCP servers. The subprocess (`agent/transports/hermes_tools_mcp_server.py`) cannot access the live AIAgent instance, which forces tools like `delegate_task`, `read_terminal`, and `close_terminal` to be blocked.

Current flow: `Claude CLI → stdio pipe → MCP subprocess → handle_function_call() → result → stdio pipe → Claude CLI`

Target flow: `Claude CLI → in-process handler → handle_function_call(agent=...) → result → Claude CLI`

## Goals / Non-Goals

**Goals:**
- Eliminate the MCP subprocess for the SDK runtime path
- Enable tools that require AIAgent access (delegate_task, read_terminal, close_terminal) by passing the agent instance to handlers
- Reduce per-tool-call latency by removing IPC serialization
- Simplify debugging (single process, contiguous stack traces)
- Remove PYTHONPATH/env forwarding hacks

**Non-Goals:**
- Rewriting the standalone MCP server (`hermes_tools_mcp_server.py`) — it remains for external clients
- Changing tool handler signatures for tools that don't need AIAgent access — existing `handle_function_call()` dispatch continues to work
- Modifying the Claude Code SDK itself — we use its public `McpSdkServerConfig` / `SdkMcpTool` / `create_sdk_mcp_server` API as documented

## Decisions

### 1. Use `create_sdk_mcp_server` + `SdkMcpTool` API

**Choice**: Build an `McpSdkServerConfig` using the SDK's in-process MCP API rather than implementing a custom transport.

**Rationale**: This is the SDK's officially supported mechanism for in-process tools. It handles tool registration, schema validation, and result marshalling. Using it means we don't maintain custom IPC code.

**Alternative considered**: Custom tool-call interceptor at the SDK event level — rejected because it would couple tightly to SDK internals and break on SDK updates.

### 2. Handler receives `agent` instance via closure

**Choice**: The `_build_hermes_tools_mcp_config(agent)` function captures the AIAgent instance in a closure. Each `SdkMcpTool.handler` calls through to `handle_function_call(name, args, agent=agent)`.

**Rationale**: Avoids global state. The agent instance is already available at the call site in `_start_session()`. Closures are the idiomatic Python pattern for this.

**Alternative considered**: Thread-local or global registry — rejected because Hermes may eventually support concurrent sessions.

### 3. Opt-in `agent` parameter for tool handlers

**Choice**: Tools that need AIAgent access declare `agent` as an optional parameter. The dispatch layer (`handle_function_call`) passes it when available, tools that don't declare it simply ignore it.

**Rationale**: Backwards-compatible. Existing tools continue working without modification. Only `delegate_task`, `read_terminal`, and `close_terminal` get updated initially.

### 4. Keep `hermes_tools_mcp_server.py` as standalone mode

**Choice**: Don't delete the file. Mark it as "standalone/external-client mode" and keep it working.

**Rationale**: External MCP clients (other agents, dev tools) may connect to Hermes via stdio MCP. The standalone server remains useful for that case. The cost of keeping it is near zero.

### 5. `disallowed_tools` list shrinks

**Choice**: With in-process MCP, we re-evaluate `_builtin_tools_to_block` in `claude_code_session.py`. The SDK runtime still blocks Claude Code built-ins that duplicate Hermes tools (Bash→terminal, Read→read_file, etc.) — that policy is unchanged. But we no longer need to block tools purely because the MCP subprocess couldn't handle them.

**Rationale**: The tool-routing spec already defines which built-ins to block (orchestration conflicts). The new in-process MCP doesn't change the deduplication policy.

## Risks / Trade-offs

**[Risk] Tool handler crash takes down main process** → Previously a crash in the MCP subprocess was isolated. Mitigation: tool handlers already use try/except and return error JSON. Add a top-level catch in the SdkMcpTool handler wrapper.

**[Risk] Blocking tool handler stalls the SDK event loop** → If a tool handler (e.g., browser_navigate) blocks for a long time, it could stall other events. Mitigation: The SDK already runs tool handlers in a separate thread/task. Verify this behavior during implementation; if needed, wrap handlers in `asyncio.to_thread()`.

**[Risk] SDK version pinning** → Requires `claude-agent-sdk >= 0.2.110`. Mitigation: Add version check in `_build_hermes_tools_mcp_config()` with a clear error message if the API is unavailable, falling back to stdio mode.

**[Trade-off] Memory sharing** → In-process means tool handlers share memory with the main loop. This is intentional (it's the whole point for delegate_task), but means a memory leak in a tool handler affects Hermes overall. Acceptable given existing tool handlers are short-lived.
