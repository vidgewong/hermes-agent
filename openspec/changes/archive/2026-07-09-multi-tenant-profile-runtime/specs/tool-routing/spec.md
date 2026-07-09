## ADDED Requirements

### Requirement: Docker environment selection for tenant profiles
The system SHALL configure DockerEnvironment as the execution backend for tenant profiles when `gateway.multi_tenant.enabled` is true. ALL filesystem I/O tools (terminal, read_file, write_file, patch, search_files) SHALL route through the tenant's Docker container. The docker environment SHALL use tenant-specific container labels and profile-based volume mounts.

#### Scenario: Tenant agent gets Docker execution backend
- **WHEN** an AIAgent is created for a tenant profile in multi-tenant mode
- **THEN** the agent's execution environment is set to DockerEnvironment with container label hermes-tenant=<username> and profile mounts configured
- **AND** all filesystem tools (terminal, read_file, write_file, patch, search_files) execute inside the container

#### Scenario: Non-tenant profile unaffected
- **WHEN** an AIAgent is created for a non-tenant profile (e.g., admin) or when multi-tenant is disabled
- **THEN** the agent uses whatever terminal environment is configured in that profile's config.yaml (default: local)
- **AND** file tools use native host I/O as before

### Requirement: Profile volume mount configuration
The system SHALL pass tenant-specific volume mounts to DockerEnvironment based on the resolved profile path. Mounts SHALL include workspace (rw), skills (ro), memories (rw), and .claude (ro).

#### Scenario: Volume mounts from profile path
- **WHEN** DockerEnvironment is configured for tenant profile at ~/.hermes/profiles/tenant-zhangsan/
- **THEN** volumes include: workspace→/workspace(rw), skills→/home/agent/.hermes/skills(ro), memories→/home/agent/.hermes/memories(rw), .claude→/home/agent/.claude(ro)

#### Scenario: Custom workspace path in config
- **WHEN** tenant's config.yaml has terminal.cwd set to a custom path
- **THEN** that path is used as the workspace mount source instead of $PROFILE_HOME/workspace

### Requirement: Container labeling for tenant lifecycle
The system SHALL label tenant containers with hermes-tenant=<username> and hermes-profile=<profile_name> in addition to existing hermes-agent labels. These labels SHALL be used for container discovery, reuse, and cleanup.

#### Scenario: Find tenant's existing container
- **WHEN** a tenant's agent needs a terminal and a container with matching labels exists and is running
- **THEN** the system reuses that container (no new container created)

#### Scenario: Cleanup orphaned tenant containers
- **WHEN** the system runs container cleanup (existing orphan reaping)
- **THEN** tenant containers idle beyond container_idle_timeout are stopped and removed

## MODIFIED Requirements

### Requirement: Minimal MCP tool blocklist for in-process server
The system SHALL only block MCP tools that genuinely cannot function in the SDK context. Tools previously blocked due to subprocess isolation (needing AIAgent access) SHALL be unblocked now that handlers execute in-process. In multi-tenant mode, the terminal tool SHALL route to the tenant's DockerEnvironment container.

#### Scenario: MCP blocked tools — reduced to true incompatibilities
- **WHEN** the in-process MCP server initializes
- **THEN** the blocked tools set SHALL contain only: `clarify`, `computer_use`
- **AND** `delegate_task`, `read_terminal`, `close_terminal` SHALL NOT be in the blocked set

#### Scenario: delegate_task is available in SDK mode
- **WHEN** the Claude Code SDK runtime is active with in-process MCP
- **THEN** `delegate_task` SHALL be exposed as an available MCP tool
- **AND** it SHALL function correctly using the AIAgent instance from the closure

#### Scenario: read_terminal and close_terminal are available
- **WHEN** the Claude Code SDK runtime is active with in-process MCP
- **THEN** `read_terminal` and `close_terminal` SHALL be exposed as available MCP tools
- **AND** they SHALL access the terminal environment manager from the AIAgent instance

#### Scenario: Terminal tool routes to tenant container in multi-tenant mode
- **WHEN** the terminal tool is called in a multi-tenant agent session
- **THEN** the command SHALL execute inside the tenant's Docker container via docker exec
- **AND** the working directory SHALL default to /workspace inside the container

### Requirement: File tools route through tenant container
The system SHALL route all file I/O tools (read_file, write_file, patch, search_files) through the tenant's Docker container when in multi-tenant mode. This provides physical filesystem isolation without path validation.

#### Scenario: read_file via docker exec
- **WHEN** read_file is called with path "/workspace/src/main.py" in multi-tenant mode
- **THEN** the system executes `docker exec <container> cat /workspace/src/main.py` and returns the content

#### Scenario: write_file via docker exec
- **WHEN** write_file is called with path and content in multi-tenant mode
- **THEN** the system writes the content into the container filesystem via docker exec
- **AND** the file persists on host through the bind-mount

#### Scenario: search_files via docker exec
- **WHEN** search_files is called with a query pattern in multi-tenant mode
- **THEN** the system executes grep/find inside the container, scoped to mounted paths

#### Scenario: patch via docker exec
- **WHEN** patch is called to modify a file in multi-tenant mode
- **THEN** the system performs the patch operation inside the container via docker exec

#### Scenario: File tool in non-tenant mode is unaffected
- **WHEN** file tools are called outside of multi-tenant mode
- **THEN** they use native host filesystem I/O as before (no docker exec)

### Requirement: Tool routing decision matrix
The system SHALL classify tools into host-executed and container-executed categories for multi-tenant mode.

#### Scenario: Host-executed tools
- **WHEN** a multi-tenant agent calls web_search, web_extract, browser_navigate, memory_store, memory_search, delegate_task, send_message, cronjob, or LLM-only tools
- **THEN** these execute on the host process, scoped to the tenant's profile

#### Scenario: Container-executed tools
- **WHEN** a multi-tenant agent calls terminal, read_file, write_file, patch, search_files, or execute_code
- **THEN** these execute inside the tenant's Docker container via docker exec
