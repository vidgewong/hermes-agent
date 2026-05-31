## ADDED Requirements

### Requirement: Agents display as grid blocks
The system SHALL render agents as individual blocks in a responsive grid layout instead of a vertical list.

#### Scenario: Desktop shows 3-column grid
- **WHEN** viewport is large (lg breakpoint)
- **THEN** agents are displayed in a 3-column grid

#### Scenario: Expanded agent spans full width
- **WHEN** user clicks an agent block to expand details
- **THEN** the expanded block spans full grid width (all columns)
