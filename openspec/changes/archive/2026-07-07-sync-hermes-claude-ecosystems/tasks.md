## 1. Tool Blocklist Reduction

- [x] 1.1 In `agent/claude_code_session.py`, reduce `_builtin_tools_to_block` to exactly: `["Agent", "Workflow", "SendMessage", "EnterWorktree", "ExitWorktree"]`
- [x] 1.2 Update the inline comment above `_builtin_tools_to_block` to reflect the new rationale (orchestration conflicts only, not tool duplication)
- [x] 1.3 Smoke-test that Bash, Read, Write, Edit, Skill, CronCreate, TaskCreate, WebFetch work in SDK runtime mode after the change

## 2. Skill Gateway

- [x] 2.1 Create `agent/skill_gateway.py` with a `SkillGateway` class containing a single `reconcile()` method
- [x] 2.2 Implement `reconcile()`: scan `~/.hermes/skills/` recursively for `SKILL.md` files; for each skill, create `~/.agents/skills/<name>` as a symlink to the skill's parent directory if not already present
- [x] 2.3 For each new `~/.agents/skills/<name>` symlink created, also create `~/.claude/skills/<name>` → `~/.agents/skills/<name>` if the Claude skills symlink is missing
- [x] 2.4 Implement collision handling: if `~/.agents/skills/<name>` exists and is NOT a symlink to the Hermes skill path, skip it and append a line to `~/.hermes/sync/skill_collisions.log`
- [x] 2.5 Call `SkillGateway().reconcile()` at SDK session start in `agent/claude_code_session.py`, wrapped in a try/except that logs errors without aborting session init

## 3. Memory Injection

- [x] 3.1 Create `agent/sync_translators/memory_to_sdk.py` with a `build_memory_append(max_bytes=4096)` function that reads MEMORY.md fragments from `~/.hermes/hermes-agent/memory/` and `~/.hermes/user.me` and returns a formatted markdown string
- [x] 3.2 Format output: user.me as `## User Profile` section (if present), then memory fragments grouped by type (user → feedback → project → reference), each as a brief `### <name>` subsection
- [x] 3.3 Enforce the 4KB cap: if the formatted block exceeds `max_bytes`, drop reference entries first, then project entries, then older feedback entries, appending `<!-- N entries omitted: size limit -->` at the end
- [x] 3.4 In `agent/claude_code_session.py`, call `build_memory_append()` before constructing `_sdk_system_prompt`; if the result is non-empty, append it to the `append` string (or set it as `append` if no other append text exists)
- [x] 3.5 Handle missing memory directory gracefully: if `~/.hermes/hermes-agent/memory/` does not exist, `build_memory_append()` returns an empty string

## 4. MCP Surface Deduplication

- [x] 4.1 In `agent/transports/hermes_tools_mcp_server.py`, identify the tool list construction point and add a check: if an `sdk_runtime=True` flag (passed via env var or constructor arg from `claude_code_session.py`) is set, exclude `terminal`, `read_file`, `write_file`, `patch`, `search_files` from the exposed tool list
- [x] 4.2 Update the `cronjob` MCP tool description to clarify: "Creates a Hermes-managed cron job with Feishu/chat delivery. For local scheduled tasks without Hermes delivery, use the built-in CronCreate tool instead."
- [x] 4.3 Pass the sdk_runtime flag from `claude_code_session.py` to the MCP server (via env or constructor) so the filter activates only in SDK sessions

## 5. Testing & Validation

- [x] 5.1 Unit test for `SkillGateway.reconcile()`: verifies symlinks are created, idempotent on re-run, skips and logs on collision
- [x] 5.2 Unit test for `build_memory_append()`: verifies correct sections, size cap truncation, graceful empty-dir handling
- [x] 5.3 Integration test: start an SDK session with at least one Hermes skill present; verify the skill appears in `~/.claude/skills/` and is invocable via the Skill tool
- [x] 5.4 Integration test: start an SDK session with Hermes memory fragments; verify the memory context block appears in the session's system prompt
- [x] 5.5 Integration test: verify Bash, Read, Write, Edit tools function in SDK runtime; verify Agent and Workflow remain blocked
