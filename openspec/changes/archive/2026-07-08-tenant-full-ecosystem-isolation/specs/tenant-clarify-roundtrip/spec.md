## ADDED Requirements

### Requirement: Tenant container emits clarify events on SSE stream
When the in-container agent triggers a `clarify` / `AskUserQuestion` call, the container SHALL emit an `event: clarify` SSE event with a JSON payload containing: `session_id`, `question`, `options` (list of `{label, description}` objects), and `multi_select` flag.

#### Scenario: AskUserQuestion produces clarify SSE event
- **WHEN** the Claude Code SDK runtime inside a tenant container calls `AskUserQuestion` with options
- **THEN** `event: clarify` is emitted on the SSE stream with the question and all option labels before the agent blocks waiting for a response

#### Scenario: Clarify event halts further SSE output until answered
- **WHEN** `event: clarify` is emitted
- **THEN** no further `text_chunk` or `tool_start` events are emitted until the container receives a response on `POST /clarify/{session_id}`

### Requirement: Tenant container exposes clarify response endpoint
The tenant container's `api_server` SHALL expose `POST /clarify/{session_id}` that accepts a JSON body `{"answer": "<label or index>"}` and unblocks the waiting `AskUserBridge` callback.

#### Scenario: Valid clarify POST unblocks agent
- **WHEN** `POST /clarify/{session_id}` is called with a valid answer while the agent is blocked on clarify
- **THEN** the `AskUserBridge` callback resolves with the answer value and the agent resumes, emitting further SSE events

#### Scenario: Clarify POST with unknown session_id returns 404
- **WHEN** `POST /clarify/{session_id}` is called with a session ID that has no pending clarify
- **THEN** the server returns HTTP 404 with `{"error": "no pending clarify for session"}`

#### Scenario: Clarify times out after 5 minutes
- **WHEN** `POST /clarify/{session_id}` is not called within 300 seconds of the clarify event
- **THEN** the container resolves the clarify with a timeout error, emits `event: error`, and closes the SSE stream

### Requirement: Host gateway renders Feishu interactive card on clarify event
Upon receiving `event: clarify` from the tenant container SSE stream, the host gateway SHALL call the platform adapter's `send_clarify()` method to render the question as an interactive card, and SHALL POST the user's answer back to the tenant container.

#### Scenario: Host renders clarify options as Feishu card buttons
- **WHEN** the host gateway receives `event: clarify` on the tenant SSE stream
- **THEN** `FeishuAdapter.send_clarify()` is called with the question and options, rendering a card with clickable buttons (one per option)

#### Scenario: User button click triggers clarify POST to container
- **WHEN** the user clicks a button on the Feishu clarify card
- **THEN** the host gateway calls `POST /clarify/{session_id}` on the tenant container with `{"answer": "<selected label>"}` and removes the interactive buttons from the card
