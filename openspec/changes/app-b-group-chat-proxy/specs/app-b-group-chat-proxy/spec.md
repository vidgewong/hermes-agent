## ADDED Requirements

### Requirement: App B adapter starts on container boot when binding exists
When a user has a Feishu App B bound (app_id + app_secret stored in their instance config), the Hermes gateway SHALL automatically start a `FeishuAdapter` instance configured with App B credentials at container startup.

#### Scenario: App B adapter starts on boot
- **WHEN** Hermes starts and `gateway.platforms.feishu_app_b` is present in the user's `config.yaml`
- **THEN** the gateway SHALL instantiate and connect a `FeishuAdapter` for App B credentials
- **AND** the adapter SHALL connect via WebSocket long connection (or webhook if configured)

#### Scenario: App B adapter does not start when no binding exists
- **WHEN** Hermes starts and no `feishu_app_b` block is present in the user's config
- **THEN** no App B adapter SHALL be started
- **AND** this SHALL NOT affect App A or any other adapter

### Requirement: App B adapter uses app access token
The App B `FeishuAdapter` SHALL authenticate using the app access token derived from the bound `app_id` and `app_secret`, not a user access token.

#### Scenario: App access token authentication for WebSocket
- **WHEN** the App B adapter connects its WebSocket long connection
- **THEN** it SHALL use the lark_oapi SDK's built-in app-access-token flow (AppID + AppSecret)
- **AND** token refresh SHALL be handled automatically by the SDK client

#### Scenario: Bind endpoint stores app_id and app_secret
- **WHEN** a user submits their CLI app credentials via `PUT /api/im/feishu/bindings/{session_id}`
- **THEN** the backend SHALL store the `app_id` and `app_secret` in the user's instance config under `gateway.platforms.feishu_app_b`
- **AND** the backend SHALL NOT attempt to exchange them for a user access token

### Requirement: App B proxies group chat messages to Hermes
The App B adapter SHALL forward all inbound group chat messages to the user's Hermes agent for processing.

#### Scenario: Group message received and dispatched
- **WHEN** a message is posted to a Feishu group chat that App B's bot has joined
- **THEN** the App B adapter SHALL receive the `im.message.receive_v1` event
- **AND** SHALL route it to the Hermes agent as a new user turn (no @-mention required)
- **AND** the sender's name SHALL be prepended to the message text as a prefix

#### Scenario: p2p (DM) messages ignored by App B
- **WHEN** a DM (chat_type = "p2p") event arrives on App B's event stream
- **THEN** the App B adapter SHALL discard the event without processing
- **AND** SHALL NOT create any agent turn

### Requirement: Each group chat maps to a distinct Hermes session
The App B adapter SHALL use the Feishu `chat_id` as the session discriminator, creating one Hermes session per group.

#### Scenario: Session key derived from chat_id
- **WHEN** the App B adapter processes a group message
- **THEN** it SHALL call `build_session_key` with `group_sessions_per_user=False`
- **AND** all messages from the same `chat_id` SHALL map to the same session key regardless of sender

#### Scenario: Different groups have isolated sessions
- **WHEN** messages arrive from two different group `chat_id` values
- **THEN** each SHALL resolve to a different session key
- **AND** agent context SHALL NOT be shared between them

### Requirement: App B delivers Hermes replies to the originating group
All Hermes agent output for a group session SHALL be sent back to the group chat as App B's bot identity.

#### Scenario: Reply posted as App B
- **WHEN** Hermes produces a response for a group session
- **THEN** the App B adapter SHALL send the message to the originating `chat_id` using App B's app access token
- **AND** the message SHALL appear from App B's bot account in the group

#### Scenario: Streaming progress card in group
- **WHEN** the agent starts processing a group message
- **THEN** the App B adapter SHALL post a streaming progress card to the group using App B credentials
- **AND** card updates SHALL use App B's CardKit API credentials

### Requirement: App A drops group chat events when App B is active
When App B is bound and running, the shared gateway App A SHALL ignore all group chat inbound events to prevent duplicate processing.

#### Scenario: App A group events dropped
- **WHEN** a group chat message arrives on App A's event stream and the user has an active App B binding
- **THEN** App A SHALL discard the event without routing it to the agent

#### Scenario: App A continues handling DMs
- **WHEN** a p2p (DM) message arrives on App A's event stream
- **THEN** App A SHALL process it normally regardless of App B binding status

### Requirement: Bind flow writes App B gateway config to instance
When a user successfully binds their CLI app, the backend SHALL persist the App B configuration to the user's Hermes instance data so the adapter auto-starts on next container boot.

#### Scenario: Config block written on bind
- **WHEN** `PUT /api/im/feishu/bindings/{session_id}` completes successfully
- **THEN** the backend SHALL write (or overwrite) the `gateway.platforms.feishu_app_b` block in `/data/openstar/instances/{instance_id}/config.yaml`
- **AND** the block SHALL contain `app_id`, `app_secret`, `group_only: true`, and `group_sessions_per_user: false`

#### Scenario: Config block removed on unbind
- **WHEN** `DELETE /api/im/feishu/bindings/{session_id}` is called
- **THEN** the backend SHALL remove the `gateway.platforms.feishu_app_b` block from the instance config

### Requirement: App B probe at bind time validates scopes
Before storing credentials, the bind endpoint SHALL probe App B to verify it is reachable and has the required message permissions.

#### Scenario: Probe succeeds — binding proceeds
- **WHEN** the user submits valid `app_id` + `app_secret` and the Feishu app has `im.message.receive_v1` scope
- **THEN** the bind endpoint SHALL return success with the bot's `open_id` and display name

#### Scenario: Probe fails — binding rejected
- **WHEN** the probe call to Feishu fails (invalid credentials, missing scopes, or network error)
- **THEN** the bind endpoint SHALL return HTTP 422 with a human-readable error message
- **AND** SHALL NOT persist any credentials
