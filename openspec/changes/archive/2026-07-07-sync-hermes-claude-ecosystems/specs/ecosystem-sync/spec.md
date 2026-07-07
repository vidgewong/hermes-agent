## ADDED Requirements

### Requirement: Session-start ecosystem reconciliation
The system SHALL perform a lightweight reconciliation at the start of each Claude Code SDK session to make Hermes content available to Claude Code's native tools.

#### Scenario: Reconciliation order at session start
- **WHEN** a new Claude Code SDK session is initialized (before the first user message is processed)
- **THEN** the system SHALL execute in order: (1) skill gateway reconcile, (2) memory snapshot injection into system prompt append block

#### Scenario: Reconciliation failure is non-fatal
- **WHEN** the skill reconcile or memory injection step raises an exception
- **THEN** the system SHALL log the error and continue session initialization — the session SHALL proceed even if reconciliation partially fails

### Requirement: No persistent sync daemon
The system SHALL NOT introduce a background filesystem watcher process or thread as part of this change. Content bridging is session-scoped (triggered at session start only).
