## Context

Hermes runs two agent runtimes. The native Python loop uses Hermes' own tool registry (skill_view, terminal, read_file, memory, cron scheduler, etc.). The Claude Code SDK runtime (`claude_code_session.py`) currently disables all Claude Code built-in tools via `_builtin_tools_to_block` and routes everything through the `hermes-tools` MCP server.

**Actual on-disk layout (verified):**

| Content | Hermes | Claude Code |
|---|---|---|
| Skills | `~/.hermes/skills/<category>/<name>/SKILL.md` | `~/.agents/skills/<name>/` — symlinked into `~/.claude/skills/<name>` |
| Memory | `~/.hermes/hermes-agent/memory/MEMORY.md` + `<name>.md` fragments | Injected via `CLAUDE.md` files or system prompt |
| Global CLAUDE.md | Does not exist | Does not exist |
| Cron | `~/.hermes/cron/jobs.json` — fired by Hermes scheduler, delivers to Feishu | `~/.claude/scheduled_tasks.json` — fired by Claude Code's own daemon |
| user.me | `~/.hermes/user.me` (may not exist) | N/A |

Claude Code's `Skill` tool reads from `~/.claude/skills/` which contains symlinks to `~/.agents/skills/`. Hermes skills in `~/.hermes/skills/` are invisible to Claude Code's Skill tool unless a corresponding entry exists in `~/.agents/skills/`.

## Goals / Non-Goals

**Goals:**
- Unblock all Claude Code built-in tools except the five orchestration-level ones that conflict with Hermes (Agent, Workflow, SendMessage, EnterWorktree, ExitWorktree)
- Make Hermes skills available to Claude Code's native Skill tool via symlink reconciliation at session start
- Make Hermes memory context available in SDK sessions by injecting it into the system prompt append block (not by writing CLAUDE.md files)
- Remove duplicate tools from the Hermes MCP surface when SDK built-ins are active
- Keep all new code additive and outside Hermes core so the branch rebases cleanly

**Non-Goals:**
- Bidirectional file sync or a persistent sync daemon
- Writing to `~/.claude/CLAUDE.md` (file does not exist; creating it changes Claude Code global behavior in ways that are hard to undo)
- Bridging Claude Code cron → Feishu (Claude cron fires in its own daemon context, not in Hermes; adding a webhook call from inside Claude Code's cron execution would require modifying Claude Code itself)
- Syncing `~/.claude/scheduled_tasks.json` into Hermes cron (different schema, different executor, duplication risk)
- Merging session histories

## Decisions

### 1. Tool Unblock: Minimal Blocklist

**Choice**: Keep blocked only: `Agent`, `Workflow`, `SendMessage`, `EnterWorktree`, `ExitWorktree`. Enable everything else.

**Rationale for each blocked tool**: `Agent`/`Workflow`/`SendMessage` spawn Claude Code sub-agents or send messages outside Hermes' control. `EnterWorktree`/`ExitWorktree` modify the working directory in ways that break Hermes session state tracking. All other built-ins are safe to enable: Hermes' permission model (bypassPermissions) is already set; secret redaction and approval guards apply at the tool result level in the MCP layer, not in the built-in layer.

**Note on `Skill`**: Unblocking it only helps if `~/.agents/skills/` contains Hermes skills — hence the skill gateway.

**Note on `CronCreate`**: Unblocking it means Claude Code can create jobs in `~/.claude/scheduled_tasks.json` fired by Claude Code's own daemon. This is independent of Hermes cron. Users should be aware of this: if they want Hermes-delivered cron (→ Feishu), they should create jobs via the `mcp__hermes-tools__cronjob` tool, not via the built-in `CronCreate`. The MCP tool description will note this.

### 2. Skill Gateway: Bidirectional Sync with Live Watcher

**Choice**: At the start of each SDK session, call `SkillGateway.reconcile()` which:
1. Scans all skills under `~/.hermes/skills/` recursively for `SKILL.md` files
2. For each skill, creates a symlink `~/.agents/skills/<name>` → the skill's parent directory, skipping if the symlink already points to the correct target
3. Logs any name collisions (both sides have `<name>`) without overwriting; the existing entry wins
4. Creates `~/.claude/skills/<name>` → `~/.agents/skills/<name>` if the Claude skills dir symlink is missing
5. Reverse-syncs Claude-native skills: if `~/.agents/skills/<name>` is not a Hermes symlink, bridges it into `~/.hermes/skills/_claude/<name>`
6. Cleans up dangling symlinks on both sides (skills that were deleted)
7. Starts a background polling watcher (2s interval, daemon thread) that re-runs reconcile on every tick

**Why a watcher**: Skills can be added or removed at any time during a session (via Hermes CLI, manual install, or Claude Code's own skill tools). Without live reconciliation, the two ecosystems drift until the next session restart.

**Why polling, not fsevents/inotify**: Avoids a hard dependency on `watchdog`. Skill changes are infrequent; 2s polling is negligible overhead and simpler to reason about.

**Why symlinks, not file copies**: Hermes skills are directories (`<name>/SKILL.md` + optional support files). Symlinking the directory preserves all support files and stays in sync automatically when Hermes updates a skill's content.

**Collision policy**: If `~/.agents/skills/<name>` already exists and is NOT a symlink to the Hermes skill, skip it (Claude Code's version wins) and log the collision to `~/.hermes/sync/skill_collisions.log`.

### 3. Memory Injection: Global CLAUDE.md + System Prompt Append

**Choice**: Two-pronged approach:
1. Write `~/.claude/CLAUDE.md` with the Hermes memory snapshot — this makes memory visible to ALL Claude Code sessions, including direct `claude` invocations that don't go through Hermes.
2. Also inject via the `_sdk_system_prompt` `append` field for real-time accuracy in Hermes-managed sessions.

The file is marked with `<!-- AUTO-GENERATED BY HERMES -->` and only overwritten when content changes. It is also updated whenever the `memory` tool writes (add/replace/remove) so that direct Claude Code sessions see changes immediately.

**Why CLAUDE.md now**: The user runs `claude` directly and needs Hermes context there too. Since we own the file content (marked header), it's safe to manage.

**What gets injected**: The same memory snapshot that Hermes native runtime builds — MEMORY.md fragments formatted as a brief context block. `user.me` is included if the file exists.

**Size guard**: If the snapshot exceeds 4KB, truncate older/lower-priority entries (reference first, then project, then older feedback).

### 4. MCP Surface Deduplication

**Choice**: The `hermes_tools_mcp_server.py` checks at init time whether it is serving an SDK runtime session (via a flag or env var set by `claude_code_session.py`) and filters its tool list to remove: `terminal`, `read_file`, `write_file`, `patch`, `search_files`. Hermes-unique tools remain: `cronjob`, `skill_view`, `skills_list`, `skill_manage`, `send_message`, `web_search`, `web_extract`, browser tools, image gen, etc.

**Rationale**: Exposing both `Bash` and `mcp__hermes-tools__terminal` gives the model two identical-looking tools. This leads to inconsistent choices and confusing tool-use traces. Deduplication removes the noise.

### 5. Cron: No Bridge (document the split instead)

**Choice**: Do not attempt to bridge Claude cron → Feishu. Update the `cronjob` MCP tool description to clearly state: "Use this tool to create Hermes-managed cron jobs that deliver results to Feishu/chat. For local scheduled tasks without delivery, use the built-in CronCreate."

**Rationale**: Claude Code's `scheduled_tasks.json` jobs are fired by Claude Code's internal daemon — a subprocess of the Claude Code CLI that Hermes has no hook into. Adding a bridge would require either: (a) polling `scheduled_tasks.json` from Hermes (fragile, polling), or (b) having Claude Code jobs call a Hermes webhook (requires modifying Claude Code's prompt/behavior to add a webhook call to every cron job, which is brittle and would break on Claude Code updates). The clean solution is user education via tool descriptions, not infrastructure plumbing.

## Risks / Trade-offs

- **[Skill name collision]** A Claude Code skill in `~/.agents/skills/<name>` conflicts with a Hermes skill of the same name → Skip + log; Claude Code's version wins. Acceptable: Hermes skills outnumber Claude Code skills; collision is rare.
- **[Memory size]** Large Hermes memory snapshot bloats the system prompt → 4KB cap with truncation. Same guard already in native runtime.
- **[CronCreate confusion]** User creates a cron job with built-in CronCreate expecting Feishu delivery → Tool description explains the split. Not a code problem.
- **[Rebase conflicts]** Changes in `claude_code_session.py` and `hermes_tools_mcp_server.py` conflict during rebase → Both changes are confined to well-isolated sections (the `_builtin_tools_to_block` list and the MCP server's tool-list builder); conflicts will be small and mechanical.

## Migration Plan

1. **Phase 1**: Reduce `_builtin_tools_to_block` to the five orchestration tools. Test that built-ins work in SDK mode. No content bridging yet.
2. **Phase 2**: Add `SkillGateway.reconcile()` call at SDK session start. Verify Hermes skills appear in Claude Code's Skill tool.
3. **Phase 3**: Add memory snapshot injection into `_sdk_system_prompt` append. Verify Hermes memory context is visible in SDK sessions.
4. **Phase 4**: MCP surface deduplication. Remove duplicate tools from Hermes MCP server in SDK mode.
5. **Rollback**: Restore original `_builtin_tools_to_block` list in `claude_code_session.py`. All other changes (skill_gateway.py, memory_to_sdk.py) are dead code unless called — trivially removable.
