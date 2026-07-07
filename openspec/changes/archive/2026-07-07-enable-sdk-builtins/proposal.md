## Why

The Claude Code SDK exposes powerful built-in tools (AskUserQuestion, Monitor, Agent) that Hermes currently blocks entirely. With session sync already working, these tools can now be unblocked to enable: (1) structured user interaction via AskUserQuestion — surfaced through both Hermes gateway and TUI; (2) background process monitoring via Monitor; (3) native SDK subagent orchestration via the Agent tool — coexisting with Hermes' delegate_task for richer multi-agent patterns.

## What Changes

- Unblock `AskUserQuestion` built-in: when Claude calls it, Hermes bridges the question to the user via gateway (Feishu/Web) or TUI, collects their answer, and returns it
- Unblock `Monitor` built-in: allows Claude to watch long-running background processes and react to output lines as events
- Unblock `Agent` built-in: enables Claude Code's native subagent system (AgentDefinition, background agents, nested subagents, resume)
- Register Hermes-specific subagents as `AgentDefinition` entries so the SDK Agent tool can invoke them (Hermes skills as agents, specialized workers)
- Bridge `AskUserQuestion` responses through Hermes' existing `clarify` infrastructure (gateway blocking-prompt bridge for Feishu/Web, TUI prompt for interactive)
- `delegate_task` remains available as a Hermes MCP tool (parallel coexistence, not replacement)

## Capabilities

### New Capabilities
- `ask-user-bridge`: Bridges the SDK's AskUserQuestion tool to Hermes' user interaction surfaces (gateway + TUI), translating between SDK question format and Hermes' clarify/prompt protocol
- `monitor-integration`: Enables the SDK Monitor built-in for watching background processes within Hermes sessions
- `sdk-subagents`: Enables the SDK Agent built-in and registers Hermes-specific subagent definitions (via AgentDefinition) so Claude can spawn specialized workers through the native SDK mechanism

### Modified Capabilities
- `tool-routing`: The disallowed_tools list shrinks — AskUserQuestion, Monitor, and Agent are removed from the block list

## Impact

- `agent/claude_code_session.py`: `_builtin_tools_to_block` list modified (remove AskUserQuestion, Monitor, Agent)
- `agent/claude_code_session.py`: Add `canUseTool` callback to handle AskUserQuestion permission flow
- `agent/claude_code_session.py` or `agent/claude_code_sdk_runtime.py`: Register Hermes subagents as `AgentDefinition` in the SDK options
- `agent/transports/hermes_tools_mcp_server.py`: If standalone mode, no changes needed (AskUserQuestion is a built-in, not MCP)
- Gateway infrastructure: `clarify` / blocking-prompt bridge needs an adapter for AskUserQuestion's multi-choice format
- TUI: prompt renderer needs to handle AskUserQuestion's structured questions/options
- Dependencies: No new packages — uses existing `claude-agent-sdk` APIs
