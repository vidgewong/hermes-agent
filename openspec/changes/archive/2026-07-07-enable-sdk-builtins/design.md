## Context

Hermes' Claude Code SDK runtime currently blocks all but the most basic built-in tools, routing everything through the Hermes MCP server. This was necessary when the SDK lacked features like user interaction and subagents. Now the SDK has mature support for:

- **AskUserQuestion**: structured multi-choice questions surfaced via `canUseTool` callback
- **Monitor**: background process watching with event-driven reactions
- **Agent**: native subagent orchestration with AgentDefinition, background execution, nesting, and resume

Hermes already has parallel infrastructure: `clarify` for user questions (gateway blocking-prompt bridge), `delegate_task` for subagents. The goal is to enable the SDK's built-ins alongside Hermes' tools — additive, not replacement.

Current state: `_builtin_tools_to_block` in `claude_code_session.py` blocks Agent, Workflow, and many others. The `permission_mode` is `bypassPermissions`.

## Goals / Non-Goals

**Goals:**
- Enable AskUserQuestion with bidirectional bridging to Hermes' gateway (Feishu/Web) and TUI
- Enable Monitor for background process observation
- Enable the Agent built-in so Claude can use SDK-native subagents
- Register Hermes-specific subagent definitions (AgentDefinition) so they're discoverable
- Maintain delegate_task as a parallel MCP tool (not deprecated)

**Non-Goals:**
- Replacing delegate_task with Agent (they coexist)
- Enabling Workflow tool (stays blocked — Hermes owns orchestration)
- Changing the native Python runtime path (only SDK runtime affected)
- Building a full permission UI (AskUserQuestion handles it structurally)

## Decisions

### 1. AskUserQuestion bridges through Hermes' existing `clarify` protocol

**Choice**: Implement a `canUseTool` callback that detects `AskUserQuestion` calls, translates the SDK question format into Hermes' `clarify` protocol (for gateway) or TUI prompt (for interactive), waits for the user response, and returns `PermissionResultAllow(updated_input={questions, answers})`.

**Rationale**: Hermes already has a proven blocking-prompt bridge for `clarify` that works across Feishu, Web gateway, and TUI. We adapt the format rather than building new UX infrastructure.

**Alternative considered**: Exposing AskUserQuestion as an MCP tool instead — rejected because it's already a built-in with well-defined SDK semantics and the callback pattern is idiomatic.

### 2. Monitor unblocked with no additional bridging

**Choice**: Simply remove `Monitor` from `_builtin_tools_to_block`. The Monitor tool watches background scripts natively in the Claude CLI subprocess — no Hermes bridging needed.

**Rationale**: Monitor operates entirely within the Claude CLI process. It watches stdout of background commands and generates events. Hermes doesn't need to intercept or bridge this — it's self-contained.

### 3. Agent tool unblocked; Hermes subagents registered via `agents` parameter

**Choice**: Remove `Agent` from `_builtin_tools_to_block`. Pass Hermes-specific subagent definitions (e.g., specialized workers for code review, research, etc.) via the `agents` parameter in `ClaudeAgentOptions`.

**Rationale**: This enables Claude to use both SDK-native subagents (via Agent tool) AND Hermes' delegate_task (via MCP). They serve different purposes: Agent is better for focused, tool-restricted subtasks with context isolation; delegate_task is better for Hermes-aware work with gateway routing and depth tracking.

### 4. Permission mode stays `bypassPermissions` but AskUserQuestion always prompts

**Choice**: Keep `bypassPermissions` as the permission mode. Per SDK docs, AskUserQuestion always reaches `canUseTool` regardless of permission mode (it's in the "ask rules" category that fires before mode evaluation).

**Rationale**: We want all tool calls to auto-approve (Hermes handles its own guardrails), but AskUserQuestion is inherently interactive — it must reach the user. The SDK guarantees this behavior.

### 5. Hermes subagent definitions are derived from skills + delegate profiles

**Choice**: Build `AgentDefinition` entries from Hermes' skill library (skills that act as agents) and pre-defined profiles (code-reviewer, researcher, etc.). These are passed in the `agents` dict at session creation.

**Rationale**: Hermes already has a rich skill library. Converting skill metadata to AgentDefinition format makes them available through the SDK's Agent tool with proper descriptions, prompts, and tool restrictions.

## Risks / Trade-offs

**[Risk] AskUserQuestion timeout in headless/cron mode** → In cron sessions there's no user to answer. Mitigation: detect session type; in cron mode, auto-deny AskUserQuestion calls with a message "no user available in headless mode".

**[Risk] Agent tool subagents don't have Hermes MCP tools** → SDK subagents only get the tools listed in their AgentDefinition. Mitigation: include `mcp__hermes-tools__*` in subagent tool lists, or register the in-process MCP server for subagents too.

**[Risk] Dual subagent systems confuse the model** → Claude might not know when to use Agent vs delegate_task. Mitigation: system prompt guidance explaining when to use each; delegate_task for Hermes-aware background work, Agent for focused subtasks.

**[Trade-off] Monitor uses Claude CLI process resources** → Background monitoring runs inside the Claude CLI subprocess. Acceptable since Hermes already allocates this subprocess for the session duration.
