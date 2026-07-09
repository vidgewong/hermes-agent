## ADDED Requirements

### Requirement: Admin toolset gated by profile
The system SHALL expose a `tenant_admin` toolset containing user management tools. This toolset SHALL only be available to profiles listed in `gateway.multi_tenant.admin_profiles` (default: ["default"]).

#### Scenario: Admin profile sees tenant tools
- **WHEN** an agent runs in a profile listed in admin_profiles
- **THEN** the agent's tool schema includes tenant_admin tools (user_list, user_get, user_create, user_update, user_link_identity, user_provision)

#### Scenario: Non-admin profile does not see tenant tools
- **WHEN** an agent runs in a tenant profile not listed in admin_profiles
- **THEN** the tenant_admin toolset is not included in the tool schema

### Requirement: user_list tool
The system SHALL provide a `user_list` tool that returns all registered users with optional filtering by platform, role, or search query.

#### Scenario: List all users
- **WHEN** admin calls user_list with no filters
- **THEN** returns a JSON array of all user records with id, username, display_name, email, wiw_id, roles, and linked identity count

#### Scenario: Filter by platform
- **WHEN** admin calls user_list with platform="feishu"
- **THEN** returns only users who have a linked Feishu identity

### Requirement: user_get tool
The system SHALL provide a `user_get` tool that returns a single user's full record including all linked identities.

#### Scenario: Get user by username
- **WHEN** admin calls user_get with username="zhang.san"
- **THEN** returns the full user record plus all linked im_identities and profile mappings

#### Scenario: User not found
- **WHEN** admin calls user_get with a non-existent username
- **THEN** returns an error indicating user not found

### Requirement: user_create tool
The system SHALL provide a `user_create` tool that creates a user record with specified fields.

#### Scenario: Create user with all fields
- **WHEN** admin calls user_create with username, display_name, email, wiw_id, roles, responsibilities
- **THEN** a new user record is created and returned

#### Scenario: Create user minimal
- **WHEN** admin calls user_create with only username and display_name
- **THEN** a new user record is created with nullable fields left empty

### Requirement: user_update tool
The system SHALL provide a `user_update` tool that updates specified fields on an existing user record.

#### Scenario: Update user roles
- **WHEN** admin calls user_update with username="zhang.san" and roles=["developer", "lead"]
- **THEN** the user's roles field is updated; other fields unchanged

#### Scenario: Update wiw_id and responsibilities
- **WHEN** admin calls user_update with wiw_id="W12345" and responsibilities="Backend services"
- **THEN** the specified fields are updated

### Requirement: user_link_identity tool
The system SHALL provide a `user_link_identity` tool that links an IM identity to an existing user.

#### Scenario: Link Feishu identity
- **WHEN** admin calls user_link_identity with username="zhang.san", platform="feishu", platform_user_id="ou_abc123"
- **THEN** the identity is linked; future messages from that Feishu user route to zhang.san's profile

#### Scenario: Link already-taken identity
- **WHEN** admin calls user_link_identity with a platform_user_id already linked to another user
- **THEN** returns an error indicating the identity is already linked to user X

### Requirement: user_provision tool
The system SHALL provide a `user_provision` tool that provisions (creates) or deprovisions (removes) a Hermes profile for a user.

#### Scenario: Provision new profile
- **WHEN** admin calls user_provision with username="zhang.san" and action="provision"
- **THEN** a Hermes profile is created for the user, the user_profiles mapping is updated with provisioned_at timestamp

#### Scenario: Deprovision profile
- **WHEN** admin calls user_provision with username="zhang.san" and action="deprovision"
- **THEN** the tenant's container is stopped, the profile is marked as deprovisioned (NOT deleted — profile directory preserved for data recovery)

#### Scenario: Provision with template
- **WHEN** admin calls user_provision with template="default"
- **THEN** the new profile is cloned from the specified template profile

### Requirement: Web API for user management
The system SHALL expose REST endpoints on the gateway API server for user CRUD and identity management. Endpoints SHALL be protected by the existing API bearer token authentication.

#### Scenario: GET /api/tenants/users
- **WHEN** authenticated request to GET /api/tenants/users
- **THEN** returns paginated list of all users

#### Scenario: POST /api/tenants/users
- **WHEN** authenticated request to POST /api/tenants/users with user data
- **THEN** creates a new user record and returns it

#### Scenario: POST /api/tenants/users/:id/identities
- **WHEN** authenticated request with platform and platform_user_id
- **THEN** links the IM identity to the specified user

#### Scenario: POST /api/tenants/users/:id/provision
- **WHEN** authenticated request to provision endpoint
- **THEN** provisions a Hermes profile for the user and returns the profile name

#### Scenario: Unauthenticated request rejected
- **WHEN** a request arrives without a valid bearer token
- **THEN** the system returns 401 Unauthorized
