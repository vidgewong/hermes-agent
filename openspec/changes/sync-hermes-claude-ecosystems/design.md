## Context

Hermes operates two agent runtimes: a native Python loop and a Claude Code SDK subprocess. The Claude Code SDK runtime (`claude_code_session.py`) currently disables all Claude Code built-in tools via `disallowed_tools`, routing every operation through an MCP server (`hermes-tools`). This means `~/.claude/` (skills, memory, settings) is effectively dead weight — Claude Code cannot use its own file editing, Bash, cron, or skill system.

The user maintains state in two home directories:
- `~/.hermes/` — skills, memory (MEMORY.md + fragments), config.yaml, SOUL.md, hooks
- `~/.claude/` — skills, memory (memory system), settings.json, projects/, sessions/

These ecosystems evolved independently. Enabling Claude's native tools without sync means edits made by Claude Code (e.g., saving a memory, installing a skill) are invisible to Hermes, and vice versa.

## Goals / Non-Goals

**Goals:**
- Enable all Claude Code built-in tools in SDK runtime mode (only block orchestration-level tools that conflict with Hermes: Agent, Workflow, SendMessage)
- Bidirectional sync of skills between `~/.hermes/skills/` and `~/.claude/skills/`
- Bidirectional sync of memory between Hermes' MEMORY.md system and Claude Code's memory
- Sync project-level instructions (SOUL.md ↔ CLAUDE.md in project directories)
- Transparent operation — user should not need to manually copy files or trigger sync
- Graceful degradation — if sync fails, both ecosystems continue working independently

**Non-Goals:**
- Merging session histories (each runtime keeps its own conversation state)
- Syncing authentication tokens or credentials between ecosystems
- Supporting third-party Claude Code plugins/extensions
- Real-time sub-second sync (eventual consistency within 5s is acceptable)
- Syncing `~/.claude/settings.json` permission rules into Hermes (different security models)

## Decisions

### 1. Sync Architecture: Filesystem Watcher + Event Hooks (not polling or symlinks)

**Choice**: `watchfiles` (Rust-backed) daemon + session lifecycle hooks.

**Alternatives considered**:
- *Symlinks*: Fragile — directory structures differ, Claude Code expects specific layout. Breaks when either tool validates its directory structure.
- *Polling*: Wastes CPU, adds latency. `watchfiles` is inotify-based on Linux, near-zero overhead.
- *Unified directory (single ~/.agent)*: Would require forking both Claude Code and Hermes, too invasive.

**Rationale**: Filesystem watching catches changes regardless of source (manual edits, tool writes, git pulls). Session hooks guarantee sync at runtime boundaries even if the watcher is temporarily down.

### 2. Content Mapping Strategy: Translation Layer (not raw copy)

**Choice**: Each content type (skills, memory, settings) has a dedicated translator that understands both formats.

**Rationale**: 
- Skills: Hermes stores skills as `~/.hermes/skills/<name>/skill.md` with frontmatter. Claude Code stores skills as `~/.claude/skills/<name>.md` (flat files or directories). A translator maps between layouts.
- Memory: Hermes uses `MEMORY.md` index + fragment files. Claude Code uses its own memory system (conversation-derived). The translator produces appropriate writes for each side.
- Project instructions: Hermes uses `SOUL.md` at project root. Claude Code uses `CLAUDE.md`. These can be symlinked or concatenated depending on whether both files should exist.

### 3. Conflict Resolution: Last-Write-Wins with Audit Log

**Choice**: When the same logical content is modified on both sides between sync cycles, the most recent mtime wins. Conflicts are logged to `~/.hermes/sync/conflicts.log`.

**Alternatives considered**:
- *Three-way merge*: Over-engineered for skill/memory files which are typically small markdown. Risk of merge artifacts corrupting instructions.
- *User prompt*: Breaks the "transparent" requirement.

**Rationale**: In practice, simultaneous edits are rare — the user is using one runtime at a time. The audit log provides recovery if the wrong side wins.

### 4. Tool Blocking: Minimal Blocklist (not blanket block)

**Choice**: Only block `Agent`, `Workflow`, `SendMessage`, `EnterWorktree`, `ExitWorktree` — tools that conflict with Hermes' orchestration or multi-agent model. Enable everything else (Bash, Read, Write, Edit, Skill, TaskCreate, CronCreate, etc.).

**Rationale**: Claude Code's native tools are optimized for their environment (permission handling, hooks, file history). Routing them through MCP adds latency and loses features (e.g., Edit's line-number awareness, Bash's background execution). The Hermes MCP server remains available as a secondary tool source for Hermes-specific operations (messaging, gateway, channel management).

### 5. Sync Scope: Configurable Include/Exclude

**Choice**: Default sync covers skills, memory, and project instructions. User can customize in `~/.hermes/config.yaml`:

```yaml
ecosystem_sync:
  enabled: true
  interval_seconds: 5
  sync_skills: true
  sync_memory: true
  sync_project_instructions: true
  exclude_patterns:
    - "*.tmp"
    - ".git/"
```

## Risks / Trade-offs

- **[Race condition]** Both runtimes write to the same logical file simultaneously → Mitigation: Lock file per-content-unit during sync; last-write-wins with conflict log for recovery.
- **[Stale state]** Watcher daemon crashes silently → Mitigation: Session hooks always trigger sync at start/end; health check in TUI status line.
- **[Format drift]** Claude Code updates its skill/memory format in a new release → Mitigation: Version-detect Claude Code installation; translator modules are isolated and versioned.
- **[Disk churn]** Aggressive sync of large memory trees → Mitigation: Content-hash comparison before write; only sync when content actually changed (not just mtime).
- **[Security]** Syncing settings could expose different permission models → Mitigation: Never sync credentials, auth tokens, or permission configs. Blocklist in sync rules.

## Migration Plan

1. **Phase 1**: Remove blanket `disallowed_tools`, add minimal blocklist. Test that Claude Code built-ins work through SDK runtime. No sync yet — both ecosystems operate independently.
2. **Phase 2**: Implement sync engine with translators for skills and memory. Add session hooks. Run in dry-run mode logging what would sync.
3. **Phase 3**: Enable live sync. Add `ecosystem_sync` config section. Default enabled for new installs, opt-in for existing.
4. **Rollback**: Disable sync via config (`ecosystem_sync.enabled: false`). Revert to full `disallowed_tools` blocklist if tool conflicts emerge.

## Open Questions

- Should `SOUL.md` and `CLAUDE.md` be kept as separate files (each referencing the other) or merged into one canonical file with a symlink? Leaning toward symlink from `CLAUDE.md` → `SOUL.md` since Hermes is the primary.
- Should the sync daemon run as a standalone process or as a thread within the Hermes gateway? Gateway-embedded is simpler but couples lifecycle.
- How should skills that depend on Hermes-specific tools (e.g., `lark-im`) appear in Claude Code's skill list? They'll be visible but non-functional unless the MCP server is connected.
