## ADDED Requirements

### Requirement: Tenant container exposes slash command endpoint
The tenant container's `api_server` SHALL expose `POST /v1/slash` accepting `{"command": "<slash command string>", "session_id": "<id>"}` and executing the command against the tenant's in-container gateway state. The response SHALL be `{"ok": true, "message": "<confirmation text>"}` or `{"ok": false, "error": "<reason>"}`.

#### Scenario: /model command updates tenant's model config
- **WHEN** `POST /v1/slash` is called with `{"command": "/model claude-sonnet-5"}`
- **THEN** the tenant container updates its model config and returns `{"ok": true, "message": "Model set to claude-sonnet-5"}`

#### Scenario: /new command resets tenant session
- **WHEN** `POST /v1/slash` is called with `{"command": "/new"}`
- **THEN** the tenant container starts a new session and returns `{"ok": true, "message": "New session started"}`

#### Scenario: /reset command clears tenant session history
- **WHEN** `POST /v1/slash` is called with `{"command": "/reset"}`
- **THEN** the tenant container clears the current session history and returns `{"ok": true}`

#### Scenario: /stop command interrupts current tenant turn
- **WHEN** `POST /v1/slash` is called with `{"command": "/stop"}` while a turn is in progress
- **THEN** the tenant container sets the interrupt flag, the running turn is stopped, and `{"ok": true, "message": "Turn interrupted"}` is returned

#### Scenario: Unknown slash command returns error
- **WHEN** `POST /v1/slash` is called with an unrecognised command string
- **THEN** the server returns `{"ok": false, "error": "Unknown command: /foobar"}`

### Requirement: Host gateway forwards slash commands to tenant container
When the host gateway detects a message from a tenant-routed DM sender that is a slash command, it SHALL POST the command to the tenant container's `/v1/slash` endpoint instead of (or before) starting an SSE turn.

#### Scenario: Host detects slash command in tenant DM
- **WHEN** a tenant DM message starts with `/` and the sender is mapped to a tenant container
- **THEN** the host calls `TenantRouter.forward_slash(command, session_id)` which POSTs to `http://127.0.0.1:{port}/v1/slash`

#### Scenario: Host relays slash command confirmation to user
- **WHEN** `forward_slash()` receives `{"ok": true, "message": "..."}` from the container
- **THEN** the host gateway sends the confirmation message back to the Feishu DM sender

#### Scenario: /claude-code-runtime slash command is forwarded, not applied to host
- **WHEN** a tenant sends `/claude-code-runtime` in a DM
- **THEN** the command is forwarded to the tenant container (changing that tenant's runtime) and does NOT modify the host gateway's runtime config
