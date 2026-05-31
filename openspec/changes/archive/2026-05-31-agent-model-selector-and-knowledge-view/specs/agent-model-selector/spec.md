## ADDED Requirements

### Requirement: Model field displays as dropdown selector
The system SHALL render the model field in the agent detail panel as a dropdown Select component instead of plain text. The dropdown SHALL list all available models for that agent.

#### Scenario: Dropdown shows available models
- **WHEN** agent detail panel is expanded
- **THEN** the model field shows a Select dropdown with the current model pre-selected and other available models as options

#### Scenario: Available models come from API
- **WHEN** the agents API returns `available_models` array
- **THEN** the Select dropdown lists all models from that array

### Requirement: Model selection calls placeholder function
The system SHALL call a placeholder function when the user selects a different model. The function SHALL NOT actually switch the model in V1.

#### Scenario: User selects a different model
- **WHEN** user picks a different model from the dropdown
- **THEN** a toast notification displays "Model switch not yet implemented"
- **AND** the selection visually updates in the dropdown
- **AND** the actual agent model does NOT change

### Requirement: API returns available_models list
The system SHALL include an `available_models` field in each agent's API response containing the list of selectable model IDs.

#### Scenario: API response structure
- **WHEN** GET `/api/openstar/agents` is called
- **THEN** each agent object includes `available_models` as an array of strings (e.g., ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5"])
