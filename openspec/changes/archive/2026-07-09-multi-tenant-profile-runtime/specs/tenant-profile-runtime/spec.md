## ADDED Requirements

### Requirement: Profile provisioning for tenants
The system SHALL provision a Hermes profile for each tenant user using the existing profile creation infrastructure (`profiles.py`). The profile SHALL include: config.yaml (with tenant-specific overrides), workspace directory, skills directory, memories directory, and .claude directory.

#### Scenario: Provision profile for new user
- **WHEN** a new user "zhang.san" is provisioned
- **THEN** the system creates a profile named "tenant-zhangsan" at ~/.hermes/profiles/tenant-zhangsan/ with default config.yaml, empty workspace/, skills/, and memories/ directories

#### Scenario: Provision profile with template
- **WHEN** a user is provisioned and `gateway.multi_tenant.profile_template` is set to "default"
- **THEN** the system clones the template profile's config and skills into the new profile (using existing --clone behavior)

#### Scenario: Profile already exists
- **WHEN** provisioning is requested for a user whose profile directory already exists
- **THEN** the system skips creation and maps the user to the existing profile

### Requirement: Docker container as agent execution sandbox
The system SHALL run each tenant's agent commands inside a Docker container using the existing DockerEnvironment backend. The container SHALL mount the tenant's profile content and provide an isolated terminal environment.

#### Scenario: Container creation for tenant
- **WHEN** a tenant's agent needs to execute terminal commands for the first time
- **THEN** the system creates a Docker container with labels hermes-tenant=<username>, hermes-profile=<profile_name>, mounts workspace at /workspace, and starts it with the sleep-infinity pattern

#### Scenario: Container reuse across turns
- **WHEN** the same tenant's agent needs to execute commands on a subsequent turn
- **THEN** the system finds the existing labeled container and dispatches via docker exec (no new container)

#### Scenario: Container stopped on idle timeout
- **WHEN** a tenant's container has been idle longer than `gateway.multi_tenant.container_idle_timeout` (default: 3600 seconds)
- **THEN** the system stops the container (it will be recreated on next use)

### Requirement: Profile content mounted into container
The system SHALL bind-mount the following from the tenant's profile directory into the container:
- `$PROFILE_HOME/workspace` → `/workspace` (read-write)
- `$PROFILE_HOME/skills` → `/home/agent/.hermes/skills` (read-only)
- `$PROFILE_HOME/memories` → `/home/agent/.hermes/memories` (read-write)
- `$PROFILE_HOME/.claude` → `/home/agent/.claude` (read-only)

#### Scenario: Workspace persistence
- **WHEN** the agent creates a file at /workspace/output.txt inside the container
- **THEN** the file is visible at $PROFILE_HOME/workspace/output.txt on the host

#### Scenario: Skills read-only access
- **WHEN** the agent attempts to modify a file in /home/agent/.hermes/skills/ inside the container
- **THEN** the write operation fails because the mount is read-only

#### Scenario: Memory persistence across container restarts
- **WHEN** the container is stopped and recreated
- **THEN** all memory files are preserved because they reside on the host profile directory

### Requirement: Agent runs on host, all filesystem I/O in container
The system SHALL run the AIAgent loop (LLM API calls, tool dispatch, memory operations) on the host process. ALL filesystem I/O tools (terminal, read_file, write_file, patch, search_files) SHALL execute inside the tenant's container via docker exec. The container's mount boundary provides physical tenant isolation — no path validation is needed.

#### Scenario: LLM call on host
- **WHEN** the agent makes an API call to the LLM provider
- **THEN** the call is made from the host process using the tenant profile's .env credentials

#### Scenario: Terminal command in container
- **WHEN** the agent calls the terminal tool with command "ls /workspace"
- **THEN** the command executes inside the tenant's Docker container via docker exec

#### Scenario: read_file in container
- **WHEN** the agent calls read_file with path "/workspace/main.py"
- **THEN** the read is performed inside the container via docker exec (e.g., cat /workspace/main.py)
- **AND** the agent cannot read files outside the container's mounted directories

#### Scenario: write_file in container
- **WHEN** the agent calls write_file to create "/workspace/output.txt"
- **THEN** the write is performed inside the container via docker exec
- **AND** the file is persisted on the host at $PROFILE_HOME/workspace/output.txt (via bind mount)

#### Scenario: search_files in container
- **WHEN** the agent calls search_files with a query
- **THEN** the search (grep/find) executes inside the container, limited to mounted paths only

#### Scenario: patch in container
- **WHEN** the agent calls patch to modify a file
- **THEN** the patch operation executes inside the container via docker exec

#### Scenario: Memory tool on host
- **WHEN** the agent calls memory_store or memory_search
- **THEN** the operation runs on the host, scoped to the tenant's profile directory (memories/ is also mounted into container for agent read access but memory tool writes happen on host)

#### Scenario: Cross-tenant isolation guarantee
- **WHEN** the agent attempts to read a path like "/home/openstar/.hermes/../../../other-profile/workspace/secret.txt"
- **THEN** the operation fails because the container filesystem does not contain other tenants' files — isolation is physical, not path-validated

### Requirement: Container resource limits
The system SHALL apply resource limits to tenant containers: CPU (configurable, default 2 cores), memory (configurable, default 4GB), PID limit (default 256). These SHALL be configurable per-tenant or globally.

#### Scenario: Default resource limits applied
- **WHEN** a tenant container is created with no per-tenant overrides
- **THEN** the container runs with --cpus=2, --memory=4g, --pids-limit=256

#### Scenario: Per-tenant resource override
- **WHEN** a tenant's profile config.yaml contains `terminal.docker.cpus: 4`
- **THEN** the tenant's container uses --cpus=4 instead of the default
