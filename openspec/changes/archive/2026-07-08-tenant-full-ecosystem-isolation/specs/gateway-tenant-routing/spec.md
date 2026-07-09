## MODIFIED Requirements

### Requirement: Identity-based DM routing
The system SHALL route inbound DM messages to the correct tenant profile based on the sender's platform identity.

#### Scenario: Known sender routed to their tenant
- **WHEN** a DM arrives from a sender whose platform identity is registered in the tenant registry
- **THEN** the gateway routes the message to that sender's tenant profile's container

#### Scenario: Unknown sender with auto-provision
- **WHEN** a DM arrives from an unregistered sender AND `tenants.auto_provision` is enabled
- **THEN** the gateway triggers tenant provisioning, starts the container, and routes the message to the new tenant

#### Scenario: Unknown sender without auto-provision
- **WHEN** a DM arrives from an unregistered sender AND `tenants.auto_provision` is disabled
- **THEN** the gateway responds with a configurable rejection message and does not create a session

### Requirement: Superuser DM bypass
The system SHALL route DMs from the superuser's own platform identity directly to the superuser profile without tenant routing.

#### Scenario: Superuser sends a DM
- **WHEN** a DM arrives from an identity listed under `tenants.superuser_identities`
- **THEN** the message is routed to the host superuser profile, bypassing tenant routing entirely

### Requirement: Streaming message forwarding to tenant container
The system SHALL forward routed messages to the tenant container using SSE streaming when `tenant_routing.streaming: true`, and fall back to synchronous HTTP forwarding otherwise.

#### Scenario: Streaming forward connects via SSE
- **WHEN** a message is routed to a running tenant container and `tenant_routing.streaming: true`
- **THEN** the host gateway opens a `GET /v1/stream` SSE connection and relays events to the platform adapter in real time

#### Scenario: Synchronous fallback when streaming disabled
- **WHEN** `tenant_routing.streaming` is false or absent
- **THEN** the host gateway uses `POST /v1/chat/completions` and waits for a single response (existing behaviour)

#### Scenario: Forward to stopped container with auto-start
- **WHEN** a message is routed to a tenant whose container is stopped AND `tenants.auto_start: true`
- **THEN** the host gateway starts the container, waits for readiness, then forwards the message via the configured method (streaming or synchronous)

#### Scenario: Container not ready timeout
- **WHEN** the tenant container fails to become ready within `tenants.start_timeout` seconds (default: 30)
- **THEN** the host gateway responds with a "service unavailable" message to the sender

### Requirement: Slash command forwarding to tenant container
The system SHALL detect slash commands in tenant DMs and forward them to the container's `/v1/slash` endpoint rather than processing them on the host.

#### Scenario: Slash command detected and forwarded
- **WHEN** a tenant DM message begins with `/` and the sender is mapped to a tenant container
- **THEN** `TenantRouter.forward_slash()` POSTs `{"command": "<text>"}` to `http://127.0.0.1:{port}/v1/slash`

#### Scenario: Slash command result relayed to sender
- **WHEN** `forward_slash()` returns `{"ok": true, "message": "..."}`
- **THEN** the host gateway sends the message to the DM sender via the platform adapter

### Requirement: Response routing back to sender with streaming fidelity
The system SHALL route responses from tenant containers back to the original sender preserving streaming events.

#### Scenario: Text chunks delivered progressively via stream card
- **WHEN** the tenant SSE stream emits `text_chunk` events
- **THEN** the host gateway calls `_stream_card_text()` for each chunk, updating the Feishu card progressively

#### Scenario: Tool events shown in stream card
- **WHEN** the tenant SSE stream emits `tool_start` and `tool_end` events
- **THEN** the host gateway calls `_stream_card_tool_start()` and `_stream_card_tool_end()`, showing tool progress in the card
