## MODIFIED Requirements

### Requirement: Downstream skill sync on superuser change
The system SHALL propagate skill changes from the superuser profile to all tenant profiles whenever the superuser's skills are modified, respecting governance frontmatter in `SKILL.md`.

#### Scenario: New skill added to superuser propagates per propagate_to
- **WHEN** the superuser installs a new skill via `hermes skills install <skill>`
- **THEN** the system syncs that skill to all tenants listed in the skill's `propagate_to` field (or all tenants if `propagate_to: all`) whose `allowed_skills` also permits it

#### Scenario: Skill updated on superuser propagates to propagate_to targets
- **WHEN** the superuser or an owner directly modifies an existing skill's SKILL.md
- **THEN** the system overwrites the corresponding skill in each tenant in `propagate_to` that has it permitted

#### Scenario: Skill removed from superuser
- **WHEN** the superuser removes a skill via `hermes skills uninstall <skill>`
- **THEN** the system removes that skill from all tenant profiles that had it

### Requirement: Allowlist-aware propagation
The system SHALL only propagate skills that are permitted by each tenant's allowlist, combined with the skill's own `propagate_to` policy.

#### Scenario: Skill not in tenant allowlist is not propagated
- **WHEN** the superuser installs a new skill AND a tenant's `allowed_skills` does not include that skill name
- **THEN** the skill is NOT synced to that tenant's profile, regardless of `propagate_to`

#### Scenario: Tenant not in propagate_to does not receive skill
- **WHEN** a skill's `propagate_to` lists specific tenant names and a tenant is not in that list
- **THEN** the skill is not propagated to that tenant even if their `allowed_skills` permits it

### Requirement: Governance-gated propagation for group proposals
The system SHALL only propagate a group-proposed skill version to tenants after the approval quorum is met; owner direct-changes bypass the gate.

#### Scenario: Proposal below quorum is not propagated
- **WHEN** a group proposal exists for a skill but quorum has not been reached
- **THEN** `sync_all_tenant_skills()` continues to use the existing canonical version of the skill; the proposed version is not pushed to any tenant

#### Scenario: Quorum reached triggers automatic propagation
- **WHEN** the final required approval is written for a pending proposal
- **THEN** the proposed SKILL.md is promoted to canonical and `sync_all_tenant_skills()` is invoked immediately for all tenants in `propagate_to`

### Requirement: Sync triggering mechanisms
The system SHALL trigger tenant skill sync via both automatic hooks and manual CLI commands.

#### Scenario: Automatic sync after skill management
- **WHEN** any skill management operation completes on the superuser profile (install, uninstall, update)
- **THEN** `sync_tenant_skills()` is invoked automatically as a post-hook

#### Scenario: Manual sync via CLI
- **WHEN** the superuser runs `hermes tenant sync-skills`
- **THEN** a full reconciliation of all tenant skill directories is performed against the superuser's current skills, each tenant's allowlist, and each skill's `propagate_to` policy

#### Scenario: Sync status reporting
- **WHEN** the sync completes
- **THEN** the system reports per-tenant: skills added, updated, removed, and any errors
