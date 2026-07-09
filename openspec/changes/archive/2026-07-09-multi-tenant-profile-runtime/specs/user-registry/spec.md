## ADDED Requirements

### Requirement: User record storage
The system SHALL store user records in PostgreSQL with fields: id (UUID), username (unique), display_name, email (nullable), wiw_id (nullable), roles (text array), responsibilities (text), created_at, updated_at.

#### Scenario: Create a new user
- **WHEN** a user record is created with username "zhang.san" and display_name "Zhang San"
- **THEN** the system stores the record with a generated UUID, timestamps set to now, and returns the complete user record

#### Scenario: Username uniqueness enforced
- **WHEN** a user record is created with a username that already exists
- **THEN** the system rejects the creation with a conflict error

#### Scenario: Update user metadata
- **WHEN** an existing user's wiw_id or responsibilities are updated
- **THEN** the system persists the changes and updates the updated_at timestamp

### Requirement: IM identity linking
The system SHALL store IM identity records with fields: id (UUID), user_id (FK to users), platform (enum: feishu, telegram, discord, slack, whatsapp, wechat, dingtalk), platform_user_id (string), display_name (nullable), metadata (JSONB), linked_at. The combination (platform, platform_user_id) SHALL be unique.

#### Scenario: Link Feishu identity to user
- **WHEN** a Feishu open_id "ou_abc123" is linked to user "zhang.san"
- **THEN** the system creates an im_identities record with platform="feishu", platform_user_id="ou_abc123", user_id pointing to zhang.san's record

#### Scenario: Prevent duplicate identity linking
- **WHEN** an IM identity (platform + platform_user_id) is linked that already exists for another user
- **THEN** the system rejects the operation with a conflict error indicating the identity is already linked

#### Scenario: Resolve user from IM identity
- **WHEN** the system queries for platform="feishu" and platform_user_id="ou_abc123"
- **THEN** it returns the linked user record with all fields

#### Scenario: Multiple identities per user
- **WHEN** a user has both a Feishu and a Telegram identity linked
- **THEN** both identities resolve to the same user record

### Requirement: User-profile mapping
The system SHALL store user-to-profile mappings with fields: user_id (FK), profile_name (string), is_primary (boolean), provisioned_at. Each user SHALL have exactly one primary profile.

#### Scenario: Map user to profile
- **WHEN** user "zhang.san" is mapped to profile "tenant-zhangsan" as primary
- **THEN** the mapping is stored and the profile_name can be retrieved by user_id

#### Scenario: Profile provisioning status
- **WHEN** a user's profile mapping has provisioned_at set to null
- **THEN** the system indicates the profile is pending provisioning

### Requirement: Auto-registration of unknown IM users
The system SHALL auto-register unknown IM users when `gateway.multi_tenant.auto_register` is true. Auto-registration SHALL create a user record with username derived from the platform_user_id, link the IM identity, and provision a new profile.

#### Scenario: Auto-register on first DM (enabled)
- **WHEN** an unknown Feishu user sends a DM and auto_register is true
- **THEN** the system creates a user record, links the Feishu identity, provisions a profile, and proceeds to handle the message in the new profile's context

#### Scenario: Reject unknown user (disabled)
- **WHEN** an unknown Feishu user sends a DM and auto_register is false
- **THEN** the system replies with a "not registered" message and does not create any records

#### Scenario: Auto-registration username generation
- **WHEN** an unknown user is auto-registered from platform "feishu" with platform_user_id "ou_abc123"
- **THEN** the generated username SHALL be deterministic and URL-safe (e.g., "feishu-ou_abc123") and the display_name SHALL be populated from the platform's user info API if available

### Requirement: Database connection management
The system SHALL connect to PostgreSQL using connection parameters from `gateway.multi_tenant.database_url` in config.yaml. Connection pooling SHALL be used for concurrent access.

#### Scenario: Startup connection
- **WHEN** the gateway starts with multi_tenant.enabled=true
- **THEN** it establishes a connection pool to the configured database_url and runs schema migrations if needed

#### Scenario: Missing database configuration
- **WHEN** multi_tenant.enabled=true but database_url is not configured
- **THEN** the gateway fails to start with a clear error message indicating the missing configuration
