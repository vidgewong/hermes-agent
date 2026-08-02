## Context

OpenStar is a multi-tenant wrapper around Hermes. Each user gets their own Hermes container. For Feishu/Lark integration, there are currently two credential layers:

- **App A** (platform-wide gateway app): configured once by the admin; handles all inbound events (DM + group) via `FEISHU_APP_ID`/`FEISHU_APP_SECRET`; uses `im.message.receive_v1` subscription.
- **App B** (per-user CLI app): each user can bind their own `app_id`+`app_secret` via the IM binding UI; today this is only used for *outbound* delivery in cross-org group chats via `lark-cli`/`send_via=lark_cli`.

The problem: App B has no active inbound listener. Group messages in the user's personal groups never reach their Hermes agent. To fix this, App B must become a **full inbound+outbound proxy for group chats**, while App A handles DM only.

Feishu's permission model distinguishes:
- **User access token**: scoped to a specific user's identity; cannot receive events in groups the user joined via the app bot.
- **App access token**: tenant/app-scoped; the app bot receives all events in chats it belongs to; required for `im.message.receive_v1` event subscriptions via long connection.

App B is a Feishu Custom App (not ISV app), so it supports app-access-token authentication and can subscribe to group events in chats the bot has been added to.

## Goals / Non-Goals

**Goals:**
- App B's Feishu bot is added to user groups → receives all messages without @-mention requirement
- Each group (`chat_id`) maps to a distinct Hermes session in the user's container
- Hermes replies are delivered back to the group as App B
- App A continues to handle DM/p2p traffic; group events on App A are silently dropped
- Binding flow stores an app access token (refreshed automatically)
- No new Feishu admin console changes required beyond App B already having `im.message.receive_v1` and `im:message:create_v1` scopes

**Non-Goals:**
- App B handling DM (p2p) — App A owns that surface
- @-mention gating in groups for App B — every message triggers the agent (user explicitly adds bot to group to enable)
- Supporting non-Feishu IM platforms in this change
- Any UI changes — the existing IM binding dialog already collects `app_id`+`app_secret`

## Decisions

### D1: Per-user App B adapter lifecycle — piggyback on user container startup

**Decision**: When a user's Hermes container starts, Hermes checks `~/.hermes/config.yaml` for a `gateway.platforms.feishu` block with `role: app_b`. If present, it starts a `FeishuAdapter` instance configured with App B credentials, `group_only: true` flag, and `group_sessions_per_user: false` (one session per group, shared across all group members).

**Why not a separate process**: Hermes already manages the gateway event loop. Starting a second gateway process per user would double resource usage and complicate lifecycle management. Instead, the existing multiplex profile mechanism — `_start_secondary_profile_adapters` — can host the App B adapter as a pseudo-secondary profile or as a named extra adapter within the same gateway.

**Alternative considered**: Dedicated microservice per user — rejected as too heavy for a multi-tenant environment with potentially hundreds of users.

### D2: App access token at bind time, not user token

**Decision**: The `POST /api/im/feishu/bindings` handler calls Feishu's `POST /auth/v3/app_access_token/internal` using `app_id`+`app_secret` to obtain an `app_access_token` and stores it (with expiry) in the binding record. This token is refreshed automatically by the gateway adapter (same pattern as existing lark SDK client auth).

**Why**: `im.message.receive_v1` events in group chats are delivered to the app (not a user), so only an app access token can authenticate the WebSocket long connection. User tokens have group-chat limitations.

**Alternative considered**: Rely on lark_oapi SDK's built-in token management (pass `app_id`+`app_secret` only) — this is actually the preferred approach: the lark_oapi SDK manages token refresh internally. No need to persist `app_access_token` explicitly; only `app_id`+`app_secret` must be stored (already the case).

### D3: Group-only filter flag on FeishuAdapter

**Decision**: Add a `group_only: bool` field to `FeishuAdapterSettings`. When `True`, `_on_message_event` drops all `chat_type == "p2p"` events immediately. Symmetrically, App A gains a `dm_only: bool` flag (or uses existing `group_policy: "disabled"`) that drops all group events.

**Why**: Clean separation at the event ingestion point rather than post-routing. Avoids any risk of duplicate session routing when both apps are active.

**Alternative considered**: Route based on `chat_id` namespace — fragile because `chat_id` format doesn't reliably indicate type without consulting Feishu API.

### D4: Session key for group chats — `chat_id` as session, no user isolation

**Decision**: App B group adapter uses `group_sessions_per_user=False`, so `build_session_key` produces a single session per `chat_id` (not per `chat_id`+`user_id`). This is the correct model since App B represents the user (not a participant), and the conversation is the group as a whole.

**Why**: The user wants their agent to maintain one continuous conversation per group, not fork per group member.

### D5: Config persistence — write App B gateway block to user's `~/.hermes/config.yaml`

**Decision**: After a successful bind, the backend writes (or updates) a `gateway.platforms.feishu_app_b` block in the user's Hermes container config file at `/data/openstar/instances/{instance_id}/config.yaml`. The gateway's secondary adapter startup reads this block at start time.

**Why**: Hermes config is the canonical source of truth for gateway credentials. Persisting to the DB only would require the backend to push config every time the container restarts.

**Implementation note**: Use a distinct platform key (`feishu_app_b`) rather than `feishu` to avoid collision with App A's config.

## Risks / Trade-offs

- **[Risk] Feishu app scopes not pre-configured**: App B must have `im:message:receive_v1` and `im:message:create_v1` enabled in the Feishu open-platform console before the binding works. → Mitigation: document in the bind dialog UI; add a `probe_bot` call at bind time to verify and surface a clear error.
- **[Risk] Bot not added to group**: Even with correct scopes, App B only receives events from groups where its bot account has been added as a member. → Mitigation: surface this as a setup requirement in the UI; consider a `/hermes status` hint.
- **[Risk] Two adapters using the same lark SDK WebSocket client could conflict**: The existing `_app_lock_identity` guard uses `app_id` to prevent two processes starting the same app. App A and App B have different `app_id` values, so no conflict. → Verified: `_app_lock_identity = self._app_id`; distinct values mean distinct locks.
- **[Risk] Container restart clears adapter state**: App B adapter is restarted on every container start. Any in-flight group messages during restart are dropped. → Acceptable; same behaviour as existing App A reconnect logic.
- **[Trade-off] `group_sessions_per_user=False`**: All group members' messages go into one shared session. This is intentional (agent acts as a group participant, not per-user), but means the agent cannot tell who in the group sent a specific message without reading `sender.open_id` from the event metadata. The existing `message_prefix_for_group_senders` gateway config already handles this.

## Migration Plan

1. Deploy backend changes (binding endpoint stores `app_id`+`app_secret`, writes config block to instance data).
2. Existing bindings: a migration script backfills the `feishu_app_b` config block for users who already have a binding with `app_id`+`app_secret` stored.
3. Users must restart their Hermes container (or the platform auto-restarts it) to pick up the new gateway config.
4. App A: deploy `dm_only: true` (via `group_policy: disabled`) simultaneously to prevent duplicate event handling. Rolling restart is safe — brief window where both handle groups is acceptable (idempotent dedup).

**Rollback**: Remove the `feishu_app_b` block from the user's config and restart container. App A reverts to handling all events.

## Open Questions

- Should App B also handle reactions and card interactions in groups, or only messages? (Likely yes — keep parity with App A behaviour.)
- Should the group policy on App B enforce any allowlist, or always allow all group members? (Proposed: `group_policy: open` for App B since the user chose to add their bot.)
- Does the existing `_send_via_lark_cli` path need to be kept as a fallback, or can it be fully replaced once App B adapter is running? (Propose: keep as legacy fallback for non-container deployments.)
