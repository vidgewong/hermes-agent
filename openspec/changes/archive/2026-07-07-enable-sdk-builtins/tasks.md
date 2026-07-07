## 1. Unblock Built-in Tools

- [x] 1.1 Remove `AskUserQuestion` from `_builtin_tools_to_block` in `claude_code_session.py`
- [x] 1.2 Remove `Agent` from `_builtin_tools_to_block` and add it to `allowed_tools`
- [x] 1.3 Remove `Monitor` from `_builtin_tools_to_block` and add it to `allowed_tools`
- [x] 1.4 Remove `Workflow` from `_builtin_tools_to_block` comment to clarify it stays blocked intentionally (orchestration conflict)

## 2. AskUserQuestion Bridge

- [x] 2.1 Create `agent/ask_user_bridge.py` with `handle_ask_user_question(input_data, session_type)` that detects session type (gateway/TUI/cron) and routes accordingly
- [x] 2.2 Implement gateway path: translate SDK question format to Hermes' `clarify` blocking-prompt protocol, send via gateway channel, wait for response, translate back to SDK answer format
- [x] 2.3 Implement TUI path: render questions/options in terminal with numbered choices, accept selection or free text input, return SDK answer format
- [x] 2.4 Implement cron/headless path: return `PermissionResultDeny` with guidance message
- [x] 2.5 Handle multi-select questions (comma-separated selections) and free-text "Other" responses
- [x] 2.6 Register `canUseTool` callback in `ClaudeAgentOptions` that routes AskUserQuestion to the bridge and auto-allows all other tools

## 3. SDK Subagent Integration

- [x] 3.1 Create `agent/sdk_subagent_profiles.py` with a function `build_hermes_agent_definitions()` that returns a dict of AgentDefinition entries
- [x] 3.2 Define core subagent profiles: code-reviewer (read-only), researcher (web+read), general-worker (full tools)
- [x] 3.3 Optionally derive AgentDefinition entries from Hermes skills that have agent-like metadata (description, tools, prompt)
- [x] 3.4 Pass `agents=build_hermes_agent_definitions()` in `ClaudeAgentOptions` at session creation
- [x] 3.5 Ensure subagents have access to Hermes MCP tools by including the in-process MCP server in their tool set

## 4. System Prompt Guidance

- [x] 4.1 Add delegation guidance to the SDK system prompt explaining: Agent for focused subtasks with context isolation; delegate_task for Hermes-aware work with gateway routing
- [x] 4.2 Add AskUserQuestion usage guidance: when to ask vs when to decide autonomously

## 5. Testing

- [x] 5.1 Unit test: verify AskUserQuestion is NOT in `_builtin_tools_to_block`, Agent and Monitor are NOT blocked
- [x] 5.2 Unit test: `handle_ask_user_question()` correctly translates between SDK and Hermes formats
- [x] 5.3 Unit test: cron mode auto-denies AskUserQuestion
- [x] 5.4 Unit test: `build_hermes_agent_definitions()` returns valid AgentDefinition entries
- [x] 5.5 Integration test: start SDK session, verify Agent and Monitor appear in available tools
- [ ] 5.6 Manual test: trigger AskUserQuestion via gateway, verify question appears in Feishu/Web and answer returns correctly
