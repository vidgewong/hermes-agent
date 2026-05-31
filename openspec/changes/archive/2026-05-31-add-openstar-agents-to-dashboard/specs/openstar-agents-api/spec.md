## ADDED Requirements

### Requirement: GET /api/openstar/agents returns agent list
The system SHALL expose a `GET /api/openstar/agents` endpoint that returns the list of OpenStar business agents with their metadata and current status.

#### Scenario: Successful retrieval
- **WHEN** a GET request is made to `/api/openstar/agents`
- **THEN** the response SHALL be 200 with JSON body containing an `agents` array

#### Scenario: Response structure
- **WHEN** the endpoint returns successfully
- **THEN** each agent object SHALL contain: `id` (string), `name` (string), `description` (string), `status` ("online" | "busy" | "offline"), `icon` (string, lucide icon name), `last_active` (ISO 8601 timestamp or null)

### Requirement: Agent list contains three fixed business agents
The system SHALL return exactly three agents: `mb-req` (MB-REQ Agent), `mb-test` (MB-Test Agent), `mb-arch` (MB-Arch Agent). These are fixed configuration, not dynamically registered.

#### Scenario: All three agents returned
- **WHEN** the endpoint is called
- **THEN** the response contains exactly three agent entries with ids "mb-req", "mb-test", "mb-arch"

### Requirement: Agent status reflects runtime state
The system SHALL report each agent's status based on its actual runtime state. In V1, if no agent runtime is connected, status defaults to "offline".

#### Scenario: No agent runtime connected
- **WHEN** no agent process is running for a given agent
- **THEN** that agent's status SHALL be "offline" and last_active SHALL be null

#### Scenario: Agent has active session
- **WHEN** an agent has an active session in the session store
- **THEN** that agent's status SHALL be "online" and last_active SHALL reflect the most recent activity timestamp

### Requirement: Endpoint requires session authentication
The system SHALL protect the endpoint with the same session authentication as other `/api/` endpoints (X-Hermes-Session-Token header or cookie auth).

#### Scenario: Unauthenticated request
- **WHEN** a request is made without valid session credentials
- **THEN** the response SHALL be 401 Unauthorized
