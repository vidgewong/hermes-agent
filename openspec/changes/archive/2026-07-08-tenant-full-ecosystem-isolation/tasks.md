## 1. .claude Persistence (tenant-claude-persistence)

- [x] 1.1 Update `provision_tenant()` in `hermes_cli/tenant_cmd.py` to `mkdir -p {profile_dir}/.claude` with mode `0700` after creating the profile directory
- [x] 1.2 Update `generate_tenant_compose()` in `hermes_cli/tenant_compose.py` to add `{profile_dir}/.claude:/home/hermes/.claude` volume entry for each non-suspended tenant service
- [x] 1.3 Write unit test in `tests/hermes_cli/test_tenant_registry.py`: verify `.claude/` exists after `provision_tenant()` and that re-provisioning does not delete existing `.claude/` content
- [x] 1.4 Write unit test in `tests/hermes_cli/test_tenant_compose_volumes.py`: verify generated compose YAML includes the `.claude` volume entry

## 2. SOUL.md Layer (soul-md-layer)

- [x] 2.1 Update `generate_tenant_compose()` to add `{hermes_home}/SOUL.md:/home/hermes/.hermes/SOUL.md:ro` volume entry only when `SOUL.md` exists on the host at compose-generation time
- [x] 2.2 Update the system prompt builder (locate in `gateway/run.py` or `agent/claude_code_session.py`) to read `HERMES_HOME/SOUL.md` at turn start and prepend its content before any `CLAUDE.md` content
- [x] 2.3 Ensure SOUL.md loading is silent when the file is absent (no warning/error)
- [x] 2.4 Write test: system prompt with SOUL.md present has SOUL content before CLAUDE.md content; test with SOUL.md absent produces normal system prompt

## 3. Tenant Container SSE Streaming (tenant-sse-streaming)

- [x] 3.1 Add `httpx[http2]` to `requirements.txt` and `requirements-tenant.txt`
- [x] 3.2 Add `GET /v1/stream` SSE endpoint to `gateway/platforms/api_server.py`; the endpoint accepts a message body, starts a gateway turn, and emits `text_chunk`, `tool_start`, `tool_end`, `turn_done`, `error` events as `text/event-stream`
- [ ] 3.3 Wire `GatewayEventDispatcher` events into the SSE response stream inside the container's gateway turn handler
- [x] 3.4 Implement `TenantRouter.stream_message()` in `gateway/tenant_router.py` using `httpx` async SSE client connecting to `GET /v1/stream`; parse each event and call the appropriate host `GatewayEventDispatcher` callback
- [x] 3.5 Add `tenant_routing.streaming: bool = False` field to `GatewayConfig` in `gateway/config.py`
- [x] 3.6 Update `gateway/run.py` DM forwarding path: when `tenant_routing.streaming` is `True`, call `stream_message()` instead of `forward_message()`; wire `_stream_card_start`, `_stream_card_text`, `_stream_card_tool_start`, `_stream_card_tool_end`, `_stream_card_finish` into the SSE event handlers
- [x] 3.7 Implement SSE retry logic in `stream_message()`: on connection drop before `turn_done`, retry within 2s using `Last-Event-ID`; emit a "reconnecting…" card update to the user
- [x] 3.8 Write integration test in `tests/gateway/test_tenant_sse_streaming.py`: mock SSE server emitting text and tool events; verify host stream card callbacks are invoked in order

## 4. Clarify Round-Trip (tenant-clarify-roundtrip)

- [x] 4.1 Add an in-process pending-clarify registry to `api_server.py`: a dict `{session_id: asyncio.Future}` for active clarify waits
- [x] 4.2 Update `AskUserBridge` (or a new SSE variant) inside the container to emit `event: clarify` on the SSE stream with `session_id`, `question`, `options`, `multi_select`, then `await` the Future
- [x] 4.3 Add `POST /clarify/{session_id}` endpoint to `api_server.py` that resolves the pending Future with `{"answer": ...}` from the request body; return 404 if no pending clarify for that session_id
- [x] 4.4 Add 300-second timeout to each pending clarify Future; on timeout emit `event: error` and close the SSE stream
- [x] 4.5 Update `TenantRouter.stream_message()` in the host to handle `event: clarify`: call `adapter.send_clarify()` with the options and register a callback that POSTs to `POST /clarify/{session_id}` when the user answers
- [x] 4.6 Wire Feishu card action callback (`_handle_clarify_card_action`) to call `TenantRouter.resolve_tenant_clarify(session_id, answer)` for tenant-originated clarify events
- [x] 4.7 Write test: full round-trip — SSE stream emits clarify → host sends Feishu card → simulate button click → verify `POST /clarify/{session_id}` is called → agent resumes

## 5. Slash Command Passthrough (tenant-slash-passthrough)

- [x] 5.1 Add `POST /v1/slash` endpoint to `gateway/platforms/api_server.py`; dispatch the command string to the existing `_handle_slash_command()` handler and return `{"ok": bool, "message": str}`
- [x] 5.2 Implement `TenantRouter.forward_slash(command, session_id)` in `gateway/tenant_router.py`: POST to `http://127.0.0.1:{port}/v1/slash` and return the response dict
- [x] 5.3 Update `gateway/run.py` DM handling: before routing to SSE or synchronous forwarding, check if the message text starts with `/`; if so call `forward_slash()` and deliver the confirmation message, skip the agent turn
- [x] 5.4 Remove the existing host-side slash-command handling for `/model`, `/new`, `/reset`, `/stop`, `/claude-code-runtime` in the tenant-DM code path (these now go to the container, not the host)
- [x] 5.5 Write test: slash command DM from a tenant sender → verify `forward_slash()` is called with correct command string and result message is relayed back

## 6. Skill Governance (skill-governance)

- [x] 6.1 Define `SkillGovernance` dataclass in `hermes_cli/tenant_skills_sync.py` with fields `owner`, `group`, `propagate_to`, `approval_policy`
- [x] 6.2 Implement `parse_skill_governance(skill_dir: Path) -> SkillGovernance` that reads optional YAML frontmatter from `SKILL.md` and falls back to defaults
- [x] 6.3 Update `sync_tenant_skills()` and `sync_all_tenant_skills()` to respect `propagate_to` from governance metadata: skip tenants not in `propagate_to` list
- [x] 6.4 Implement `submit_skill_proposal(tenant, skill_name, proposed_skill_md, description)` in a new `hermes_cli/skill_proposals.py`: validate tenant is in group, write `skills/<name>/_proposals/<tenant>/<hash>/SKILL.md` and `meta.yaml`
- [x] 6.5 Implement `approve_skill_proposal(approver_tenant, skill_name, proposal_hash)`: write `_approvals/<approver>.approve`; call `_check_quorum()` after writing
- [x] 6.6 Implement `_check_quorum(skill_name, proposal_hash)`: count approval files vs group size per `approval_policy`; if met call `_promote_proposal()` which copies proposed SKILL.md to canonical and calls `sync_all_tenant_skills()`
- [x] 6.7 Add CLI commands `hermes tenant propose-skill <tenant> <skill>` and `hermes tenant approve-skill <tenant> <skill> <hash>` in `hermes_cli/subcommands/tenant.py`
- [x] 6.8 Implement `contribute_skill(tenant, skill_name, skill_dir)`: place under `skills/_contributions/<tenant>/<skill_name>/`; add `hermes tenant contribute-skill` and `hermes skill promote-contribution` CLI commands
- [x] 6.9 Add `skill_proposals_gc` cron task: scan all `_proposals/` directories, remove entries older than 30 days, log removals
- [x] 6.10 Write tests in `tests/hermes_cli/test_skill_governance.py`: proposal creation, approval quorum trigger, owner bypass, propagate_to filtering, and GC

## 7. Integration and Documentation

- [x] 7.1 Update `openspec/changes/multi-tenant-profile-isolation/migration-guide.md` with migration steps for `.claude/` volume and SOUL.md
- [x] 7.2 Update `skills/tenant-onboarding/SKILL.md` to inform tenants about SOUL.md, their `.claude/` persistence, and skill proposal workflow
- [ ] 7.3 Run `hermes tenant compose` and verify generated `docker-compose.tenants.yml` includes all new volume entries
- [ ] 7.4 Run `hermes doctor` and verify no new warnings are emitted for a correctly configured multi-tenant setup
- [ ] 7.5 End-to-end smoke test: start a tenant container with streaming enabled, send a Feishu DM, verify stream card updates appear, send a clarify-triggering message, verify card button appears and answer flows back
