## ADDED Requirements

### Requirement: Agents navigation item in sidebar
The system SHALL add an "Agents" navigation item in the dashboard sidebar, positioned immediately after the "Sessions" item. The nav item SHALL use the `Bot` icon from lucide-react.

#### Scenario: Sidebar displays Agents nav item
- **WHEN** user views the dashboard sidebar
- **THEN** an "Agents" navigation item is visible directly below "Sessions", with a Bot icon

#### Scenario: Agents nav item highlights when active
- **WHEN** user is on the `/agents` route
- **THEN** the Agents nav item is highlighted as active (same style as other active nav items)

### Requirement: Agents page renders at /agents route
The system SHALL register a `/agents` route that renders the AgentsPage component. The page SHALL display a heading and the three OpenStar agent cards.

#### Scenario: Navigate to Agents page
- **WHEN** user clicks the "Agents" sidebar nav item
- **THEN** the browser navigates to `/agents` and the Agents page content is displayed

#### Scenario: Direct URL access
- **WHEN** user directly navigates to `/agents` via URL
- **THEN** the Agents page loads correctly with all three agent cards

### Requirement: Agent cards display name, description, and status
The system SHALL display each agent as a card/entry containing: an icon, agent name, brief description, status badge, and last active time. The three agents are MB-REQ Agent, MB-Test Agent, and MB-Arch Agent.

#### Scenario: All three agents displayed
- **WHEN** the Agents page loads successfully
- **THEN** three agent cards are visible: MB-REQ Agent, MB-Test Agent, MB-Arch Agent

#### Scenario: Agent status online
- **WHEN** an agent's status is "online"
- **THEN** a success-toned badge with pulsing dot and "Online" text is shown

#### Scenario: Agent status busy
- **WHEN** an agent's status is "busy"
- **THEN** a warning-toned badge with "Busy" text is shown

#### Scenario: Agent status offline
- **WHEN** an agent's status is "offline"
- **THEN** a muted/outline-toned badge with "Offline" text is shown

### Requirement: Agent card is clickable to start conversation
The system SHALL make each agent card clickable. Clicking SHALL navigate the user to the chat interface with the selected agent.

#### Scenario: Click agent when embedded chat is enabled
- **WHEN** user clicks an agent card and embedded chat feature is enabled
- **THEN** user is navigated to `/chat?agent=<agent-id>`

#### Scenario: Click agent when embedded chat is disabled
- **WHEN** user clicks an agent card and embedded chat is not enabled
- **THEN** the card is not interactive (no click handler)

### Requirement: Agent data refreshes periodically
The system SHALL poll the agents API every 5 seconds to refresh status data while the page is active.

#### Scenario: Status changes between polls
- **WHEN** an agent transitions from "online" to "busy"
- **THEN** the badge updates to "Busy" on the next poll cycle

#### Scenario: Page unmount stops polling
- **WHEN** user navigates away from the Agents page
- **THEN** the polling interval is cleared

### Requirement: Visual style matches Hermes dashboard
The system SHALL use existing design tokens: `font-mondwest` for display text, `@nous-research/ui` components (Card, Badge, Spinner), lucide-react icons, standard dark-themed color palette.

#### Scenario: Page renders with correct styling
- **WHEN** the Agents page is rendered
- **THEN** it uses the same Card component, typography classes, and color tokens as other dashboard pages (e.g., SessionsPage overview)

### Requirement: Internationalization support
The system SHALL support i18n for all user-visible text on the Agents page using the existing `useI18n()` pattern.

#### Scenario: Language switch
- **WHEN** user switches dashboard language
- **THEN** page title, agent names/descriptions, and status labels update to the selected language
