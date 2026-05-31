## ADDED Requirements

### Requirement: Agent detail panel shows Knowledge section
The system SHALL display a "Knowledge" section in the agent detail panel, below the existing model/task/actions information, showing the agent's knowledge layer structure.

#### Scenario: Knowledge section is visible
- **WHEN** agent detail panel is expanded
- **THEN** a "Knowledge" section heading is displayed with the layered knowledge tree below it

### Requirement: Knowledge section displays Skills with L0/L1/L2 layers
The system SHALL display each skill as a collapsible entry. Within each skill, the system SHALL show L0 summary, L1 categories with file lists, and L2 modules with file lists.

#### Scenario: Skill entry collapsed
- **WHEN** the Knowledge section loads
- **THEN** each skill is shown as a collapsible row with the skill name

#### Scenario: Skill entry expanded shows L0
- **WHEN** user expands a skill entry
- **THEN** the L0 section displays the skill's summary text with a "L0" badge in primary color

#### Scenario: Skill entry expanded shows L1
- **WHEN** user expands a skill entry
- **THEN** the L1 section displays category folders (e.g., "architecture", "aspice") each with their file lists, labeled with a "L1" badge in warning color

#### Scenario: Skill entry expanded shows L2
- **WHEN** user expands a skill entry
- **THEN** the L2 section displays supported module names (e.g., "audio", "adas") each with their file lists, labeled with a "L2" badge in success color

### Requirement: Knowledge section displays Agent Memory summary
The system SHALL display the agent's memory summary below the skills list.

#### Scenario: Memory summary shown
- **WHEN** the Knowledge section is rendered
- **THEN** a "Memory" entry is shown with the summary text (e.g., "12 entries, last updated 2026-05-20")

### Requirement: API returns knowledge data for each agent
The system SHALL include a `knowledge` object in each agent's API response with structured skill and memory data.

#### Scenario: Knowledge data structure
- **WHEN** GET `/api/openstar/agents` is called
- **THEN** each agent's `knowledge` object contains `skills` (array of skill objects with name, l0_summary, l1.categories, l2.modules) and `memory_summary` (string)

#### Scenario: Each agent has different knowledge
- **WHEN** the three agents' knowledge is returned
- **THEN** each agent has distinct skills and content appropriate to its domain (REQ has requirement-generation, Test has test-generation, Arch has architecture-review)

### Requirement: Knowledge layers use color-coded badges
The system SHALL use color-coded badges to visually distinguish knowledge layers: L0 in primary color, L1 in warning/amber color, L2 in success/green color.

#### Scenario: Badges render with correct colors
- **WHEN** a skill is expanded showing all layers
- **THEN** L0 badge uses primary tone, L1 badge uses warning tone, L2 badge uses success tone
