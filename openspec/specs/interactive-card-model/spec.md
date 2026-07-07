## ADDED Requirements

### Requirement: Platform-agnostic card data model
The system SHALL provide a platform-agnostic interactive card data model (`InteractiveCard`) that can represent structured interactive messages independently of any specific messaging platform.

#### Scenario: Card with header and markdown content
- **WHEN** a card is built with a title, color, and markdown element
- **THEN** the `InteractiveCard` instance SHALL contain a `CardHeader` with the specified title and color, and one `CardMarkdown` element in its elements list

#### Scenario: Card with action buttons
- **WHEN** a card is built with a `CardActions` element containing buttons
- **THEN** each `CardButton` SHALL have `text`, `type` (primary/default/danger), and `value` (callback action string) fields

#### Scenario: Card with list items
- **WHEN** a card is built with `CardListItem` elements
- **THEN** each list item SHALL have a text description and a button (text, type, value), suitable for rendering option lists

### Requirement: Fluent builder API
The system SHALL provide a builder/method-chain API for constructing `InteractiveCard` instances, avoiding manual dict construction.

#### Scenario: Building a complete card with builder
- **WHEN** code calls `InteractiveCard.builder().title(...).markdown(...).actions_equal([...]).note(...).build()`
- **THEN** the returned `InteractiveCard` SHALL contain the header, markdown element, equal-column actions, and note in the specified order

#### Scenario: Builder produces immutable card
- **WHEN** `build()` is called on a builder
- **THEN** the returned `InteractiveCard` SHALL be a complete data object that does not reference the builder's mutable state

### Requirement: Card element types
The system SHALL support the following element types: `CardMarkdown`, `CardDivider`, `CardActions`, `CardListItem`, `CardNote`, `CardSelect`.

#### Scenario: All element types are representable
- **WHEN** a card is built using each of the six element types
- **THEN** the card's elements list SHALL contain one instance of each type in insertion order

### Requirement: Button callback value convention
Every `CardButton` SHALL carry a `value` string that uses a colon-prefixed routing scheme (e.g., `perm:allow`, `clarify:abc123:2`, `stream:stop`) so that callback handlers can dispatch by prefix.

#### Scenario: Button value follows prefix convention
- **WHEN** a button is created with value `"clarify:req_42:3"`
- **THEN** the value string SHALL be preserved exactly as specified and be splittable on `:` to extract prefix, id, and index

#### Scenario: Button extra metadata
- **WHEN** a button is created with an `extra` dict (e.g., `{"label": "Allow", "color": "green"}`)
- **THEN** the extra metadata SHALL be accessible on the button instance for use by renderers when constructing confirmation cards
