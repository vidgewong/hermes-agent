## Why

Each platform user can already bind their own Feishu CLI App (App B) to their Hermes instance, but App B today is only used for outbound delivery (`send_via = "lark_cli"`). The platform gateway App A handles all inbound — including group chats — which means a user's personal groups are invisible to their agent. We need App B to **own the full group-chat lifecycle**: receive every group message (without @-mention gating), proxy it to Hermes, and reply as App B — so each group maps to a dedicated Hermes session and the user's agent truly works inside their own Lark/Feishu groups.

## What Changes

- **App B receives group messages**: when a user binds their CLI App (App B), the gateway must subscribe that app to `im.message.receive_v1` using an **app access token** (not user token) so it can receive group chat events on behalf of the app.
- **Per-user App B event loop**: each user's bound App B gets its own WebSocket long connection (or webhook route) independent of the shared gateway App A.
- **Group → Session mapping**: every `chat_id` in App B's inbound events maps to a unique Hermes session key; `group_sessions_per_user=False` (shared session per group, not per participant) since App B represents the user, not one of the members.
- **Reply as App B**: all Hermes responses to group events are sent back via App B's credentials (app access token), replacing the current `lark_cli` outbound path for groups.
- **App A restricted to DM only**: the shared gateway App A continues to handle p2p/DM messages but is explicitly filtered to drop group-chat events.
- **App access token at bind time**: the `POST /api/im/feishu/bindings` flow must fetch and persist an app access token (using `app_id` + `app_secret`) in addition to any existing user token, so the per-user group proxy can authenticate independently.
- **Binding stores `app_access_token`**: the `FeishuBinding` model in the backend gains an `app_access_token` field (auto-refreshed; not exposed to frontend).

## Capabilities

### New Capabilities

- `app-b-group-chat-proxy`: Per-user Feishu App B listens for group chat events (via app access token WebSocket), maps each group to a Hermes session, and proxies messages bidirectionally.

### Modified Capabilities

- `feishu-streaming-progress`: Group-chat response delivery now routes through App B rather than App A; streaming card logic must check which credential to use per `chat_id`.

## Impact

- **Backend**: `routers/im.py` (or equivalent IM binding router) — extend bind flow to fetch & persist `app_access_token`; add per-user App B adapter lifecycle (start/stop with user instance).
- **Gateway / Feishu adapter**: `plugins/platforms/feishu/adapter.py` — `_send_via_lark_cli` replaced with proper App B SDK send path; `_on_message_event` in App A must filter out group events; new `AppBGroupAdapter` class (thin wrapper) that shares event-handling logic but uses per-user `app_id`/`app_secret`.
- **Gateway config**: new `app_b` section in per-user `gateway.yaml`; `group_sessions_per_user=False` for App B adapters.
- **Feishu permissions**: App B must have `im:message:receive_v1` (read group messages) and `im:message:create_v1` (send to group) scopes enabled in the Feishu open-platform console — document this requirement.
- **No frontend changes** beyond what is already in the IM binding UI (the QR / app-secret flow already collects `app_id`+`app_secret`).
