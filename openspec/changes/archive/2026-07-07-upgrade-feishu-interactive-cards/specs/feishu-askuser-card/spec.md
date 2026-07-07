## ADDED Requirements

### Requirement: Feishu clarify renders as interactive card
The Feishu adapter SHALL override `send_clarify` to render AskUser/clarify prompts as interactive cards instead of plain text numbered lists.

#### Scenario: Single-select clarify with options
- **WHEN** `send_clarify` is called with a question and a non-empty choices list
- **THEN** the adapter SHALL send a Feishu interactive card with:
  - A blue header containing the question (or a short title)
  - The question text as a markdown element
  - Each choice rendered as a `CardListItem` (description text + button)
  - A note element with guidance text (e.g., "点击按钮选择，或直接回复")

#### Scenario: Open-ended clarify without options
- **WHEN** `send_clarify` is called with a question and no choices (empty or None)
- **THEN** the adapter SHALL send a Feishu interactive card with:
  - A blue header
  - The question as markdown
  - A note element indicating the user should reply with free text
- **AND** `mark_awaiting_text(clarify_id)` SHALL be called so the gateway text-intercept captures the reply

#### Scenario: Button value encodes clarify routing
- **WHEN** a clarify card is rendered with choices
- **THEN** each option button's value SHALL follow the format `clarify:{clarify_id}:{choice_index}` (1-indexed)

### Requirement: Clarify card callback resolves selection
The Feishu adapter SHALL handle `clarify:` prefixed card action callbacks to resolve the pending clarify.

#### Scenario: User clicks a clarify option button
- **WHEN** a card action event arrives with value prefix `clarify:` (e.g., `clarify:req_42:2`)
- **THEN** the adapter SHALL call `resolve_gateway_clarify(clarify_id, chosen_text)` with the corresponding choice text
- **AND** return a replacement card (green header, "已选择: {choice}") to update in place

#### Scenario: Callback from non-initiating user is rejected
- **WHEN** a card action event arrives with `clarify:` prefix but the operator is not the session owner
- **THEN** the adapter SHALL return a toast error ("Only the session owner can answer") and NOT resolve the clarify

### Requirement: Confirmation card replaces clarify card
After a clarify option is selected via button click, the original card SHALL be replaced in-place with a confirmation card.

#### Scenario: Confirmation card content
- **WHEN** a clarify button is clicked and successfully resolved
- **THEN** the replacement card SHALL have:
  - A green header with "已选择" or "Answered"
  - Markdown showing the original question and the selected answer
  - No action buttons (read-only state)

### Requirement: Text fallback coexistence
The Feishu clarify card SHALL coexist with the text-intercept fallback path.

#### Scenario: User types a reply instead of clicking
- **WHEN** a clarify card is sent with options AND `mark_awaiting_text` is also called
- **THEN** if the user types a reply instead of clicking a button, the gateway text-intercept SHALL resolve the clarify normally
- **AND** the card SHALL remain in its original state (not replaced, since no callback fired)
