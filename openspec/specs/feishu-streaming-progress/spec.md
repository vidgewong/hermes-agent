## ADDED Requirements

### Requirement: Streaming progress card for agent turns
The Feishu adapter SHALL send a streaming progress card at the start of an agent turn to show real-time processing status.

#### Scenario: Card created at turn start
- **WHEN** an agent turn begins processing on the Feishu platform
- **THEN** the adapter SHALL create a Card Schema 2.0 interactive card with `streaming_mode: true`
- **AND** the card SHALL have a blue header indicating "Thinking..." or similar working status

#### Scenario: Card uses CardKit v1 for creation
- **WHEN** a streaming progress card is created
- **THEN** the adapter SHALL use `POST /open-apis/cardkit/v1/cards` to create the card entity
- **AND** send the card as a message referencing the `card_id`

### Requirement: Streaming text updates via CardKit v1
The system SHALL stream agent text output to the progress card's main text element using the CardKit v1 content update API.

#### Scenario: Incremental text delivery
- **WHEN** new text content is available from the agent
- **THEN** the adapter SHALL call `PUT /open-apis/cardkit/v1/cards/{card_id}/elements/{element_id}/content` with the full accumulated text and an incrementing sequence number
- **AND** the Feishu client SHALL render the update as a typewriter animation

#### Scenario: Throttled updates
- **WHEN** text arrives faster than the configured interval
- **THEN** updates SHALL be throttled to at most one API call per 1500ms or 30 character delta (whichever triggers first)
- **AND** the final flush SHALL always send the complete text

### Requirement: Tool call display in collapsible panels
The streaming progress card SHALL display tool calls in collapsible panel elements.

#### Scenario: Tool call added to panel
- **WHEN** the agent invokes a tool during the turn
- **THEN** the progress card SHALL add an entry to the "Tools" collapsible panel showing the tool name and a status indicator
- **AND** the panel header SHALL show a count (e.g., "Tools (3)")

#### Scenario: Tool result updates panel entry
- **WHEN** a tool call completes (success or failure)
- **THEN** the corresponding panel entry SHALL update its status indicator (green dot for success, red dot for failure)

### Requirement: Status header color reflects card state
The progress card header color SHALL change to reflect the current processing state.

#### Scenario: Status transitions
- **WHEN** the card is first created → header SHALL be blue ("thinking/working")
- **WHEN** the agent turn completes successfully → header SHALL change to green ("done")
- **WHEN** the agent turn errors → header SHALL change to red ("error")

#### Scenario: Header title updates with status
- **WHEN** status changes from working to done
- **THEN** the header title SHALL update to reflect completion (e.g., "✅ Complete" or "Done")

### Requirement: Card size limit handling
The streaming progress card SHALL handle the Feishu card JSON size limit (28KB) gracefully.

#### Scenario: Card approaches size limit
- **WHEN** the card JSON exceeds 28000 bytes
- **THEN** the adapter SHALL progressively compact tool panel entries (reduce to most recent N entries, truncate long text)
- **AND** if still over limit, degrade to a plain markdown card without collapsible panels

#### Scenario: Degraded mode is permanent for the turn
- **WHEN** a streaming card degrades to plain markdown mode
- **THEN** it SHALL remain in degraded mode for the rest of the turn (no attempt to restore rich mode)

### Requirement: Graceful degradation without CardKit permission
The streaming progress card SHALL degrade gracefully when the CardKit v1 API is unavailable.

#### Scenario: CardKit API returns permission error
- **WHEN** `POST /open-apis/cardkit/v1/cards` returns a permission or authorization error
- **THEN** the adapter SHALL fall back to sending a standard interactive card (Schema 1.0)
- **AND** update it periodically via `PATCH /open-apis/im/v1/messages/{message_id}` (standard card update)
- **AND** log a warning indicating CardKit v1 is unavailable

#### Scenario: Fallback update interval
- **WHEN** operating in fallback mode (PATCH instead of CardKit streaming)
- **THEN** card updates SHALL be throttled to at most one PATCH per 3000ms to avoid rate limits
