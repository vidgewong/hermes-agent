## ADDED Requirements

### Requirement: Container title is Mercedes-Benz Agents
The system SHALL display "Mercedes-Benz Agents" as the Card header title.

#### Scenario: Title displays correctly
- **WHEN** user views the Agents page
- **THEN** the card header shows "Mercedes-Benz Agents"

### Requirement: Agents render as blocks in a grid
The system SHALL render agents as block cards in a responsive grid inside the container.

#### Scenario: Grid layout
- **WHEN** the agents are rendered
- **THEN** they appear as individual blocks in a `grid-cols-1 sm:grid-cols-3` grid

#### Scenario: Expanded block spans full width
- **WHEN** user expands an agent block
- **THEN** it spans the full grid width
