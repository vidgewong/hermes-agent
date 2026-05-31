## ADDED Requirements

### Requirement: Agent card click expands detail panel
The system SHALL expand an inline detail panel below the agent card when clicked, instead of navigating to chat. Clicking again SHALL collapse the panel.

#### Scenario: First click expands detail
- **WHEN** user clicks an agent card on the Agents page
- **THEN** a detail panel expands below that card showing agent information

#### Scenario: Second click collapses detail
- **WHEN** user clicks the same expanded agent card
- **THEN** the detail panel collapses

#### Scenario: Click different agent switches expansion
- **WHEN** user clicks a different agent card while one is expanded
- **THEN** the previous panel collapses and the new one expands

### Requirement: Agent detail panel shows model information
The system SHALL display the model name/ID that the agent is configured to use.

#### Scenario: Model displayed in detail
- **WHEN** the agent detail panel is expanded
- **THEN** the model name (e.g., "claude-sonnet-4-6") is shown with a label

### Requirement: Agent detail panel shows current task
The system SHALL display what task the agent is currently working on, or an empty state message if idle.

#### Scenario: Agent is working on a task
- **WHEN** agent has an active current_task
- **THEN** the task description is displayed in the detail panel

#### Scenario: Agent is idle
- **WHEN** agent has no current_task (null)
- **THEN** a message like "No active task" is displayed

### Requirement: Agent detail panel shows recent actions
The system SHALL display a list of recent actions/operations the agent has performed (up to 5 most recent).

#### Scenario: Agent has recent actions
- **WHEN** agent has entries in recent_actions
- **THEN** up to 5 recent actions are displayed as a compact list

#### Scenario: Agent has no recent actions
- **WHEN** agent has no recent_actions (empty array)
- **THEN** a message like "No recent activity" is displayed

### Requirement: Agent detail panel has Chat button with slash command
The system SHALL display a "Start Chat" button in the detail panel that navigates to the chat interface with a pre-filled slash command for dispatching work to that agent.

#### Scenario: Click Start Chat button
- **WHEN** user clicks the "Start Chat" button for mb-req agent
- **THEN** user is navigated to `/chat?command=/mb-req`

#### Scenario: Slash command mapping
- **WHEN** the Start Chat button is rendered for any agent
- **THEN** the command parameter uses the agent id as slash command: `/mb-req`, `/mb-test`, `/mb-arch`

### Requirement: Chat page pre-fills command from URL parameter
The system SHALL read the `command` URL query parameter and pre-fill the chat input with its value (without auto-sending).

#### Scenario: Chat opens with command parameter
- **WHEN** user navigates to `/chat?command=/mb-req`
- **THEN** the chat input field is pre-filled with "/mb-req" text

#### Scenario: User can edit before sending
- **WHEN** the command is pre-filled in the input
- **THEN** the user can append additional text before sending

#### Scenario: No command parameter
- **WHEN** user navigates to `/chat` without command parameter
- **THEN** the chat input remains empty (normal behavior)

### Requirement: Backend API returns extended agent information
The system SHALL extend the `/api/openstar/agents` response to include `model`, `current_task`, and `recent_actions` fields for each agent.

#### Scenario: API response includes new fields
- **WHEN** GET `/api/openstar/agents` is called
- **THEN** each agent object includes `model` (string), `current_task` (string | null), and `recent_actions` (array of strings)

#### Scenario: Default values for V1
- **WHEN** no real agent runtime is connected
- **THEN** `model` returns the configured default, `current_task` returns null, `recent_actions` returns empty array
