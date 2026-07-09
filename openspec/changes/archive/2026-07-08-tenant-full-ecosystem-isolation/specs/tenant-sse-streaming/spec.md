## ADDED Requirements

### Requirement: Tenant container exposes SSE streaming endpoint
The tenant container's `api_server` SHALL expose a `GET /v1/stream` endpoint that accepts a chat request via query parameters or request body and returns a `text/event-stream` response. Each event SHALL be one of: `text_chunk`, `tool_start`, `tool_end`, `turn_done`, `error`.

#### Scenario: SSE endpoint returns text chunks during generation
- **WHEN** a client sends `GET /v1/stream` with a valid message payload
- **THEN** the response has `Content-Type: text/event-stream` and emits `event: text_chunk` lines as the model generates tokens, followed by `event: turn_done` when the turn completes

#### Scenario: SSE endpoint emits tool lifecycle events
- **WHEN** the agent calls a tool during a streaming turn
- **THEN** `event: tool_start` is emitted before tool execution and `event: tool_end` is emitted after, both carrying the tool name and call ID as JSON data

#### Scenario: SSE endpoint emits error event on agent failure
- **WHEN** the agent raises an unhandled exception during a streaming turn
- **THEN** `event: error` is emitted with the error message and the connection is closed

### Requirement: Host gateway uses SSE client for tenant message forwarding
The host gateway's `TenantRouter` SHALL use an SSE client (via `httpx`) to connect to `/v1/stream` instead of the synchronous `/v1/chat/completions` endpoint when `tenant_routing.streaming` is `true` in gateway config.

#### Scenario: Host receives text chunks and feeds stream card
- **WHEN** a tenant DM arrives and `tenant_routing.streaming` is enabled
- **THEN** the host gateway calls `_stream_card_text()` on each `text_chunk` event, producing a live-updating Feishu card identical to superuser sessions

#### Scenario: Host receives tool events and updates stream card
- **WHEN** the tenant agent calls a tool during a streaming turn
- **THEN** the host gateway calls `_stream_card_tool_start()` on `tool_start` and `_stream_card_tool_end()` on `tool_end`, showing tool progress in the Feishu card

#### Scenario: SSE connection drops and host retries
- **WHEN** the SSE connection to the tenant container is interrupted before `turn_done`
- **THEN** the host gateway retries the connection within 2 seconds using the `Last-Event-ID` header carrying the last received event ID

#### Scenario: Fallback to synchronous forwarding when streaming disabled
- **WHEN** `tenant_routing.streaming` is `false` or absent in gateway config
- **THEN** the host uses the existing synchronous `POST /v1/chat/completions` forwarding without change
