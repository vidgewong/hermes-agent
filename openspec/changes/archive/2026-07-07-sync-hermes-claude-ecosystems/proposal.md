## Why

Hermes runs Claude Code as a second agent runtime via the Claude Agent SDK, but `claude_code_session.py` disables every Claude Code built-in tool with a blanket `disallowed_tools` list, routing all operations through the Hermes MCP server. This makes Claude Code's native file editing, Bash, skills, memory, and cron inaccessible — and because the two ecosystems have different on-disk layouts, a naïve unblock would leave `~/.claude/skills/` empty and memory siloed. A targeted unblock plus lightweight content bridges are enough to make both runtimes useful without introducing a sync daemon or new persistent processes.

## What Changes

- **Unblock Claude Code built-in tools**: Remove the blanket `disallowed_tools` list. Only keep blocked the five tools that genuinely conflict with Hermes orchestration: `Agent`, `Workflow`, `SendMessage`, `EnterWorktree`, `ExitWorktree`. Enable Bash, Read, Write, Edit, Glob, Grep, WebFetch, TaskCreate, CronCreate, CronDelete, CronList, ScheduleWakeup, Skill, LSP, NotebookEdit, ToolSearch, ReportFindings.
- **Skill presence bridge**: On session start, populate `~/.claude/skills/` (symlinks into `~/.agents/skills/`) with Hermes skills so Claude Code's native `Skill` tool can find them. No daemon — a one-shot reconcile at session start and a watcher only for skill additions during the session.
- **Global memory injection**: On session start in SDK runtime, translate the Hermes memory snapshot (MEMORY.md fragments + user.me if present) into the `append` section of the Claude Code system prompt that is already passed via `_sdk_system_prompt`. No CLAUDE.md file needed — memory is injected the same way Hermes already injects platform context.
- **Cron event visibility**: When CronCreate is unblocked, Claude Code writes jobs to `~/.claude/scheduled_tasks.json` which Claude Code's own daemon fires. Expose a read-only `cron_events_since` MCP tool so Claude sessions can query recent Hermes cron job results. Do not attempt to bridge Claude cron → Feishu (different execution contexts; out of scope).
- **MCP surface deduplication**: When SDK runtime is active, filter the Hermes MCP server tool list to remove tools that duplicate enabled Claude Code built-ins (terminal, read_file, write_file, patch, search_files) to avoid confusing the model with redundant options.

## Capabilities

### New Capabilities
- `skill-gateway`: Session-start reconciliation that symlinks Hermes skills into `~/.agents/skills/` and watches for additions during the session
- `unified-memory`: Hermes memory injection into the SDK system prompt `append` block at session start
- `tool-routing`: Minimal blocklist + MCP surface deduplication for SDK runtime mode

### Modified Capabilities
<!-- No existing openspec specs carry requirement-level changes -->

## Impact

- **Code**: `agent/claude_code_session.py` — reduce `_builtin_tools_to_block`, add session-start skill reconcile call and memory-append injection; `agent/transports/hermes_tools_mcp_server.py` — add runtime-mode filter for duplicate tools; new `agent/skill_gateway.py` (~100 lines: scan + symlink logic); new `agent/sync_translators/memory_to_sdk.py` (~60 lines: format MEMORY.md fragments into prompt text)
- **Config**: Optional `ecosystem_sync.enabled` flag in `~/.hermes/config.yaml` (default true); no new required config
- **Dependencies**: No new dependencies — skill reconcile uses stdlib `pathlib` + symlinks; memory inject reuses existing memory loader
- **User-visible**: Hermes skills appear in Claude Code's `/skill` command; Hermes memory context is available in SDK sessions; Claude Code's file tools work natively; Claude Code cron jobs are created in `~/.claude/scheduled_tasks.json` and fired by Claude Code's own daemon
- **Risk**: Skill symlink collisions if `~/.agents/skills/<name>` already exists with different content; mitigated by skipping existing symlinks and logging; no risk to Hermes main loop since all changes are contained to SDK session setup
- **Rebase safety**: All new code is additive and isolated to SDK session setup and two new small modules; zero changes to Hermes core (conversation_loop, tool_executor, gateway, cron scheduler)
