## ADDED Requirements

### Requirement: TUI banner displays OpenStar ASCII art
The system SHALL display "OPENSTAR" in the ASCII art banner when the TUI starts, replacing the previous "HERMES AGENT" art.

#### Scenario: TUI start shows OpenStar banner
- **WHEN** user launches the TUI
- **THEN** the ASCII art banner spells "OPENSTAR"

### Requirement: TUI theme brand name is OpenStar
The system SHALL use "OpenStar" as the brand name in the TUI theme configuration.

#### Scenario: Theme brand name
- **WHEN** the default theme is loaded
- **THEN** `brand.name` equals "OpenStar"

### Requirement: Terminal title shows OpenStar
The system SHALL use "OpenStar" as the fallback terminal title when no model is selected.

#### Scenario: No model selected
- **WHEN** no model is active in the TUI
- **THEN** the terminal tab title displays "OpenStar"

### Requirement: Slash command help uses OpenStar
The system SHALL reference "OpenStar" in slash command help text (e.g., /update help).

#### Scenario: /update help text
- **WHEN** user views help for the /update command
- **THEN** the help text says "update OpenStar to the latest version"

### Requirement: Conversation history labels use OpenStar
The system SHALL label assistant messages as "OpenStar #N" in conversation history export.

#### Scenario: History export label
- **WHEN** user exports/views conversation history
- **THEN** assistant messages are labeled "OpenStar #1", "OpenStar #2", etc.

### Requirement: Setup prompt uses OpenStar
The system SHALL reference "OpenStar" in the initial setup prompt when no model provider is configured.

#### Scenario: First-time setup
- **WHEN** user starts TUI without a configured model provider
- **THEN** the message reads "OpenStar needs a model provider before the TUI can start a session."
