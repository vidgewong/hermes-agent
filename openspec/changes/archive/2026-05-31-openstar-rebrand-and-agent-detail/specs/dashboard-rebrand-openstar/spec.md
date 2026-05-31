## ADDED Requirements

### Requirement: Dashboard brand displays as OpenStar
The system SHALL display "OpenStar" as the brand name in the dashboard sidebar header and mobile header, replacing the previous "Hermes Agent" branding.

#### Scenario: Sidebar shows OpenStar brand
- **WHEN** user views the dashboard sidebar
- **THEN** the brand text displays "OpenStar" instead of "Hermes Agent"

#### Scenario: Mobile header shows OpenStar brand
- **WHEN** user views the dashboard on a mobile device
- **THEN** the header displays "OpenStar" as the brand name

### Requirement: System action labels use OpenStar
The system SHALL label the update system action as "Update OpenStar" (was "Update Hermes"), and the in-progress label as "Updating OpenStar…".

#### Scenario: Update button shows OpenStar
- **WHEN** user views the system actions in the sidebar
- **THEN** the update action is labeled "Update OpenStar"

#### Scenario: Update in progress shows OpenStar
- **WHEN** the update action is running
- **THEN** the running label displays "Updating OpenStar…"

### Requirement: Brand short name is OS
The system SHALL use "OS" as the short brand name (was "HA").

#### Scenario: Short brand used in compact contexts
- **WHEN** the brand short name is displayed
- **THEN** it shows "OS"

### Requirement: All locale files reflect OpenStar branding
The system SHALL update the `brand`, `brandShort`, `updateHermes`, and `updatingHermes` i18n keys in ALL locale files to use "OpenStar" naming.

#### Scenario: Language switch preserves OpenStar brand
- **WHEN** user switches to any supported language
- **THEN** the brand still shows "OpenStar" and the update action label uses "OpenStar"
