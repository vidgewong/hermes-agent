## 1. Gateway — App B adapter support

- [x] 1.1 Add `group_only: bool` field to `FeishuAdapterSettings`; when `True`, drop all `chat_type == "p2p"` events in `_on_message_event`
- [x] 1.2 Add `dm_only: bool` field to `FeishuAdapterSettings` (or reuse `group_policy: "disabled"`); when `True`, drop all non-p2p events in `_on_message_event`
- [x] 1.3 Register `feishu_app_b` as a recognized platform key in `gateway/config.py` (maps to `FeishuAdapter` with `group_only=True` and `group_sessions_per_user=False`)
- [x] 1.4 In `gateway/run.py` startup, after loading the primary gateway config, check for a `feishu_app_b` platform block and instantiate + connect a second `FeishuAdapter` for App B (reuse `_start_one_profile_adapters` pattern or add a `_start_app_b_adapter` helper)
- [x] 1.5 Ensure App B adapter uses a distinct `_app_lock_identity` (its own `app_id`) so no lock collision with App A
- [x] 1.6 Wire App B adapter's message dispatch to the same `_handle_message` handler with `source.profile` or a tag identifying it as the App B surface
- [x] 1.7 On gateway shutdown, cleanly disconnect and unregister the App B adapter

## 2. Gateway — session and reply routing

- [x] 2.1 Confirm `build_session_key` produces the correct group-scoped key when `group_sessions_per_user=False` for App B events
- [x] 2.2 Ensure reply delivery uses App B's lark SDK client (not App A's) when the session originated from App B; add `source_adapter` lookup in the reply path
- [x] 2.3 Ensure `_send_via_lark_cli` fallback is NOT triggered for App B sessions (App B sends directly via its lark client)
- [x] 2.4 Verify streaming progress cards in groups are sent using App B credentials (CardKit API calls use App B's client)

## 3. Backend — bind/unbind endpoint

- [x] 3.1 Extend `PUT /api/im/feishu/bindings/{session_id}` to call `probe_bot(app_id, app_secret, domain)` before persisting; return HTTP 422 with error detail on probe failure
- [x] 3.2 After successful probe, write the `gateway.platforms.feishu_app_b` config block to the instance's `config.yaml` (path: `/data/openstar/instances/{instance_id}/config.yaml`)
- [x] 3.3 Config block must include: `enabled: true`, `app_id`, `app_secret`, `group_only: true`, `group_sessions_per_user: false`, `group_policy: open`
- [x] 3.4 Extend `DELETE /api/im/feishu/bindings/{session_id}` to remove the `feishu_app_b` block from the instance `config.yaml`
- [x] 3.5 After writing config, trigger a graceful Hermes container restart (or signal) so the new App B adapter starts without manual intervention

## 4. Backend — migration for existing bindings

- [x] 4.1 Write a one-time migration script that iterates existing IM bindings with `app_id`+`app_secret` stored and backfills the `feishu_app_b` config block in each instance's `config.yaml`
- [x] 4.2 Add a DB migration (Alembic) if the binding model needs a new column (e.g., `config_written_at` timestamp to track whether the config block has been synced)

## 5. App A — group event gating

- [x] 5.1 In App A's Feishu adapter initialization, read a `dm_only` flag from gateway config; set it to `True` when a `feishu_app_b` block is present in the same config file
- [x] 5.2 Add a test: App A with `dm_only=True` drops `chat_type=group` events and processes `chat_type=p2p` events normally

## 6. Tests

- [x] 6.1 Unit test: `FeishuAdapter` with `group_only=True` drops p2p events; processes group events
- [x] 6.2 Unit test: `FeishuAdapter` with `dm_only=True` drops group events; processes p2p events
- [x] 6.3 Unit test: `build_session_key` with `group_sessions_per_user=False` produces same key for different senders in the same `chat_id`
- [x] 6.4 Integration test: bind endpoint writes correct `feishu_app_b` block to instance config on success; returns 422 on probe failure
- [x] 6.5 Integration test: unbind endpoint removes `feishu_app_b` block from instance config
- [x] 6.6 Gateway boot test: gateway with `feishu_app_b` config block starts App B adapter; gateway without it does not

## 7. Documentation / config

- [x] 7.1 Add a comment in `ADDING_A_PLATFORM.md` or a new `docs/feishu-app-b-setup.md` documenting the required Feishu open-platform console scopes for App B (`im.message.receive_v1`, `im:message:create_v1`)
- [x] 7.2 Document the `group_only` and `dm_only` config flags in the gateway config reference
