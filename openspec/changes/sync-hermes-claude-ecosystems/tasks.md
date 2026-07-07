## 1. Tool Blocklist Reduction

- [ ] 1.1 Reduce `disallowed_tools` in `claude_code_session.py` to minimal set: Agent, Workflow, SendMessage, EnterWorktree, ExitWorktree
- [ ] 1.2 Update the Hermes MCP server (`hermes_tools_mcp_server`) to exclude tools that duplicate Claude Code built-ins (terminal, read_file, write_file, patch, search_files) when running in SDK runtime mode
- [ ] 1.3 Remove the `Skill` tool from the blocklist since ecosystem sync will keep `~/.claude/skills/` populated
- [ ] 1.4 Test that Claude Code built-in tools (Bash, Read, Write, Edit, Grep, Glob, WebFetch, CronCreate, TaskCreate, Skill) function correctly in SDK runtime mode

## 2. Sync Engine Core

- [ ] 2.1 Create `agent/ecosystem_sync.py` module with `EcosystemSync` class: init, start, stop, full_reconcile methods
- [ ] 2.2 Implement content-hash comparison (SHA-256) to detect actual changes and prevent unnecessary writes
- [ ] 2.3 Implement sync-loop suppression: track writes made by the sync engine and ignore resulting filesystem events
- [ ] 2.4 Implement last-write-wins conflict resolution with audit logging to `~/.hermes/sync/conflicts.log`
- [ ] 2.5 Add `ecosystem_sync` configuration section to config.yaml schema (enabled, interval_seconds, sync_skills, sync_memory, sync_project_instructions, exclude_patterns)

## 3. Skill Translator

- [ ] 3.1 Create `agent/sync_translators/skill_translator.py` — Hermes skill format (`skills/<name>/skill.md` with frontmatter) ↔ Claude Code skill format (`skills/<name>.md` flat file)
- [ ] 3.2 Implement Hermes→Claude direction: strip Hermes-specific frontmatter fields, preserve skill body content
- [ ] 3.3 Implement Claude→Hermes direction: generate frontmatter from filename and content, create directory structure
- [ ] 3.4 Handle skill deletion sync (remove from both sides, log)

## 4. Memory Translator

- [ ] 4.1 Create `agent/sync_translators/memory_translator.py` — Hermes memory format (YAML frontmatter + markdown + MEMORY.md index) ↔ Claude Code memory format
- [ ] 4.2 Implement Hermes→Claude direction: translate memory fragments into Claude Code's expected location/format
- [ ] 4.3 Implement Claude→Hermes direction: infer frontmatter type/name/description, create fragment file, update MEMORY.md index
- [ ] 4.4 Implement duplicate detection: skip sync when content hash matches existing entry on other side
- [ ] 4.5 Handle project-scoped memories (`~/.claude/projects/<project>/memory/` ↔ project memory directory)

## 5. Project Instructions Sync

- [ ] 5.1 Create `agent/sync_translators/instructions_translator.py` — SOUL.md ↔ CLAUDE.md bidirectional sync
- [ ] 5.2 Implement SOUL.md→CLAUDE.md: copy content with auto-sync header comment, preserve Claude-specific sections if present
- [ ] 5.3 Implement CLAUDE.md→SOUL.md: merge changes back, preserving Hermes-specific sections (channel routing, platform instructions)
- [ ] 5.4 Detect which project directories to watch (active session cwd, configured project roots)

## 6. Filesystem Watcher

- [ ] 6.1 Add `watchfiles` dependency to requirements/setup
- [ ] 6.2 Implement watcher daemon in `agent/ecosystem_sync.py`: watch `~/.hermes/skills/`, `~/.hermes/hermes-agent/memory/`, `~/.claude/skills/`, `~/.claude/projects/`
- [ ] 6.3 Wire watcher events to appropriate translator based on file path pattern matching
- [ ] 6.4 Add debounce logic (batch rapid events within 500ms window before triggering sync)

## 7. Session Lifecycle Integration

- [ ] 7.1 Add sync hook at session start in `agent/conversation_loop.py` — call `EcosystemSync.full_reconcile()` before first message
- [ ] 7.2 Add sync hook at session end — call `full_reconcile()` on session teardown (normal exit, timeout, crash handler)
- [ ] 7.3 Start filesystem watcher when gateway starts; stop on gateway shutdown
- [ ] 7.4 Add sync status to TUI status line (last sync time, any pending conflicts)

## 8. Testing & Validation

- [ ] 8.1 Unit tests for skill translator (both directions, edge cases: empty skills, large files, special characters in names)
- [ ] 8.2 Unit tests for memory translator (both directions, duplicate detection, malformed files)
- [ ] 8.3 Integration test: create skill in Hermes, verify appears in `~/.claude/skills/` within timeout
- [ ] 8.4 Integration test: modify memory in Claude Code session, verify reflected in Hermes MEMORY.md
- [ ] 8.5 Integration test: concurrent modification conflict resolution and audit log correctness
- [ ] 8.6 End-to-end test: full session with SDK runtime using Claude Code built-in tools (Bash, Edit, Skill) verifying no regressions
