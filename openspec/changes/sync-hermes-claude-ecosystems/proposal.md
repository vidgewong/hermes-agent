## Why

Hermes now runs Claude Code as a second agent runtime via the Claude Agent SDK. Currently, all Claude Code built-in tools are blocked (`disallowed_tools` in `claude_code_session.py`) forcing every operation through the Hermes MCP server. This defeats Claude Code's native capabilities (file editing, Bash, skills, memory, cron) and makes `~/.claude` effectively dead. Enabling Claude's full toolset requires bidirectional synchronization between `~/.hermes` and `~/.claude` so that skills, memory, CLAUDE.md, and settings authored in one ecosystem appear in the other — transparently to the user.

## What Changes

- **Unblock Claude Code built-in tools**: Remove the blanket `disallowed_tools` list; selectively block only tools that genuinely conflict with Hermes orchestration (Agent, Workflow, SendMessage) rather than duplicating Hermes functionality.
- **Introduce a filesystem sync daemon**: A background process that watches `~/.hermes` and `~/.claude` for changes and mirrors them bidirectionally using content-aware merge rules (skills, memory, settings each have distinct sync strategies).
- **Unified content layer**: A reconciliation layer that translates between Hermes and Claude Code's differing conventions for skills (`~/.hermes/skills/` vs `~/.claude/skills/`), memory (`MEMORY.md` + fragments vs Claude's memory format), and project instructions (`SOUL.md` / project CLAUDE.md).
- **Tool conflict resolution**: For tools that exist on both sides (file ops, terminal, cron), define routing rules — Claude Code tools are primary when in SDK runtime mode, Hermes tools remain primary in native runtime mode.
- **Session-level sync hooks**: Trigger sync on session start and session end to guarantee consistency even if the background watcher isn't running.

## Capabilities

### New Capabilities
- `ecosystem-sync`: Bidirectional synchronization engine for `~/.hermes` ↔ `~/.claude` content (skills, memory, settings, project instructions)
- `tool-routing`: Intelligent routing layer that decides which ecosystem's tool handles a given operation based on active runtime mode
- `unified-memory`: Merged view of Hermes and Claude Code memory systems with conflict resolution

### Modified Capabilities
<!-- No existing openspec specs are being modified at the requirements level -->

## Impact

- **Code**: `agent/claude_code_session.py` (remove disallowed_tools blocklist, add sync hooks), new `agent/ecosystem_sync.py` module, new `agent/tool_routing.py` module
- **Config**: New sync configuration in `~/.hermes/config.yaml` (sync intervals, conflict resolution policy, excluded paths)
- **Dependencies**: `watchfiles` or similar filesystem watcher library for the daemon
- **User-visible**: Users will see their skills/memory available in both `hermes` and `claude` contexts without manual duplication; Claude Code's native file editing, Bash, and cron tools become available in SDK runtime mode
- **Risk**: Race conditions during concurrent writes from both runtimes; needs last-writer-wins with conflict log or content-hash dedup
