## ADDED Requirements

### Requirement: SKILL.md supports governance frontmatter
Each `SKILL.md` file SHALL optionally include a YAML frontmatter block with the following fields: `owner` (tenant name or `superuser`), `group` (list of tenant names who can propose changes), `propagate_to` (list of tenant names or the string `all`), and `approval_policy` (`all`, `majority`, or `owner_only`). All fields are optional; defaults are `owner: superuser`, `group: []`, `propagate_to: all`, `approval_policy: owner_only`.

#### Scenario: Skill with full governance frontmatter is parsed correctly
- **WHEN** a `SKILL.md` begins with a YAML frontmatter block containing `owner`, `group`, `propagate_to`, and `approval_policy`
- **THEN** `parse_skill_governance()` returns a `SkillGovernance` object with all four fields populated

#### Scenario: Skill without frontmatter uses defaults
- **WHEN** a `SKILL.md` has no frontmatter block (first line is not `---`)
- **THEN** `parse_skill_governance()` returns defaults: `owner=superuser`, `group=[]`, `propagate_to=all`, `approval_policy=owner_only`

### Requirement: Group members can submit skill proposals
A tenant listed in a skill's `group` SHALL be able to propose a modified version of the skill. Proposals are stored as files on the host filesystem under `skills/<skill-name>/_proposals/<tenant>/<hash>/`.

#### Scenario: Tenant submits a skill proposal
- **WHEN** `hermes tenant propose-skill <tenant> <skill-name>` is called with modified skill content
- **THEN** a directory `skills/<skill-name>/_proposals/<tenant>/<hash>/` is created containing the proposed `SKILL.md` and a `meta.yaml` with `proposer`, `timestamp`, and `description`

#### Scenario: Non-group tenant cannot propose
- **WHEN** `hermes tenant propose-skill <tenant> <skill-name>` is called for a tenant not listed in the skill's `group`
- **THEN** the command exits with an error: `"<tenant> is not in the group for skill <skill-name>"`

### Requirement: Group members approve proposals; quorum triggers propagation
Any tenant in the `group` (or the `owner`) can approve a pending proposal by writing an approval file. When the approval count meets the `approval_policy` threshold, the proposal is automatically promoted and propagated.

#### Scenario: All-group approval policy promotes on full consensus
- **WHEN** `approval_policy` is `all` and every member of `group` has approved the proposal
- **THEN** the proposed `SKILL.md` replaces the canonical `skills/<skill-name>/SKILL.md` and `sync_all_tenant_skills()` is triggered for all tenants in `propagate_to`

#### Scenario: Majority approval policy promotes on simple majority
- **WHEN** `approval_policy` is `majority` and more than half of current `group` members have approved
- **THEN** the proposal is promoted and propagated without waiting for remaining members

#### Scenario: Owner bypass skips group approval
- **WHEN** the `owner` directly modifies `skills/<skill-name>/SKILL.md` on the host (no proposal directory)
- **THEN** `sync_all_tenant_skills()` detects the SKILL.md hash change and propagates immediately without any approval gate

#### Scenario: Stale proposals are garbage-collected
- **WHEN** a proposal directory has existed for more than 30 days without reaching quorum
- **THEN** a cron-triggered GC task removes the proposal directory and logs the removal

### Requirement: Tenants can contribute new skills to the platform
A tenant can submit a new skill (not yet in superuser's `skills/`) for platform adoption. The skill enters the superuser's proposal queue.

#### Scenario: Tenant contributes a new skill
- **WHEN** `hermes tenant contribute-skill <tenant> <skill-name>` is called and the skill does not exist in superuser's skills
- **THEN** the skill directory is placed under `skills/_contributions/<tenant>/<skill-name>/` and the superuser receives a notification via the admin toolset

#### Scenario: Superuser promotes a contributed skill
- **WHEN** the superuser runs `hermes skill promote-contribution <tenant> <skill-name>`
- **THEN** the skill is moved from `_contributions/` to `skills/<skill-name>/` with `owner: superuser` and `group: [<tenant>]` set in frontmatter
