## ADDED Requirements

### Requirement: Identity resolution on message arrival
The system SHALL resolve the sender's IM identity to a registered user before any other message processing. Resolution SHALL query the user registry by (platform, platform_user_id) extracted from the MessageEvent.

#### Scenario: Known user sends DM
- **WHEN** a message arrives from Feishu user "ou_abc123" who is registered
- **THEN** the system resolves to user "zhang.san", loads their profile "tenant-zhangsan", and scopes all subsequent processing to that profile

#### Scenario: Unknown user sends DM (auto-register enabled)
- **WHEN** a message arrives from an unregistered Feishu user and auto_register is true
- **THEN** the system auto-registers the user, provisions their profile, and proceeds with message handling

#### Scenario: Unknown user sends DM (auto-register disabled)
- **WHEN** a message arrives from an unregistered user and auto_register is false
- **THEN** the system sends a reply "You are not registered. Contact an administrator." and drops the message

### Requirement: Profile scoping via existing multiplex infrastructure
The system SHALL use `_profile_runtime_scope()` to scope the resolved user's turn to their profile. All session resolution, config loading, and credential access SHALL operate within the scoped profile.

#### Scenario: Session isolation between tenants
- **WHEN** user A and user B send messages concurrently
- **THEN** each message is processed in its own profile scope; user A's session history is not visible to user B's agent

#### Scenario: Credential isolation
- **WHEN** a tenant's agent needs an API key (e.g., for web search)
- **THEN** the system reads from the tenant's profile .env, not the host default .env

### Requirement: Slash command routing remains host-side
The system SHALL process all slash commands on the host gateway before dispatching to the tenant's agent. Slash commands SHALL operate in the tenant's profile context.

#### Scenario: Tenant uses /skills command
- **WHEN** tenant user sends "/skills" in their DM
- **THEN** the gateway lists skills available in the tenant's profile (not the admin's skills)

#### Scenario: Tenant uses /new command
- **WHEN** tenant user sends "/new"
- **THEN** the gateway resets the session for that tenant's profile only

#### Scenario: Admin-only commands
- **WHEN** a non-admin tenant sends "/tenant users" (an admin command)
- **THEN** the system rejects with "permission denied" or treats it as unknown command

### Requirement: Multi-tenant mode activation
The system SHALL enable multi-tenant routing only when `gateway.multi_tenant.enabled: true` in config.yaml. When disabled, the gateway operates in existing single-profile or manual multiplex mode.

#### Scenario: Multi-tenant disabled
- **WHEN** gateway.multi_tenant.enabled is false or absent
- **THEN** the gateway routes messages using existing logic (no user registry lookup)

#### Scenario: Multi-tenant enabled
- **WHEN** gateway.multi_tenant.enabled is true
- **THEN** every DM goes through identity resolution before session creation

### Requirement: DM-only routing scope
The system SHALL only apply tenant routing to direct messages (DMs). Group chats are out of scope and SHALL use existing routing logic.

#### Scenario: DM message triggers tenant routing
- **WHEN** a message arrives with chat_type="private" or equivalent DM indicator
- **THEN** tenant identity resolution is triggered

#### Scenario: Group message bypasses tenant routing
- **WHEN** a message arrives with chat_type="group"
- **THEN** existing routing logic is used (no user registry lookup)
