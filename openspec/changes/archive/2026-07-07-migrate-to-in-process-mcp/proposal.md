## Why

The Claude Code SDK runtime currently spawns `hermes_tools_mcp_server.py` as a stdio subprocess to expose Hermes tools. This introduces unnecessary IPC latency, prevents tools like `delegate_task` from accessing the live AIAgent instance, and makes debugging painful (errors may occur in the main process, the CLI subprocess, or the MCP subprocess). SDK 0.2.110 now supports in-process MCP (`McpSdkServerConfig` with `type: "sdk"`), allowing tool handlers to execute directly in the Hermes main process — eliminating the subprocess entirely.

## What Changes

- Replace the stdio MCP subprocess (`_build_hermes_tools_mcp_config()`) with an in-process `McpSdkServerConfig` that runs tool handlers directly inside the Hermes process
- Remove the `_BLOCKED_TOOLS` blocklist for tools that were only blocked due to needing AIAgent access (e.g., `delegate_task`, `read_terminal`, `close_terminal`) — they can now access the agent instance directly
- Retain `hermes_tools_mcp_server.py` as an optional standalone mode (for external clients), but the SDK runtime no longer uses it
- Eliminate PYTHONPATH/env forwarding hacks since no subprocess is spawned
- **BREAKING**: The MCP config format changes from `{type: "stdio", command: ...}` to `McpSdkServerConfig` — any code that inspects or overrides `mcp_servers` will need updating

## Capabilities

### New Capabilities
- `in-process-mcp`: In-process MCP server that exposes Hermes tools to the Claude Code SDK runtime without subprocess overhead, enabling direct AIAgent instance access for all tool handlers

### Modified Capabilities
- `tool-routing`: The tool blocklist shrinks significantly — tools that required AIAgent access (delegate_task, read_terminal, close_terminal) are now unblocked since handlers execute in-process

## Impact

- `agent/claude_code_sdk_runtime.py`: `_build_hermes_tools_mcp_config()` rewritten to return `McpSdkServerConfig`
- `agent/claude_code_session.py`: `mcp_servers` parameter type changes from `dict` to accept `McpSdkServerConfig` objects
- `agent/transports/hermes_tools_mcp_server.py`: No longer used by SDK runtime (kept for standalone use)
- `model_tools.py` / `tools/`: Tool handlers gain optional `agent` parameter for tools that need AIAgent access
- Dependencies: Requires `claude-agent-sdk >= 0.2.110` for `create_sdk_mcp_server` / `SdkMcpTool` / `McpSdkServerConfig` APIs
