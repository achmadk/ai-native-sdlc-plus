# ship-observe Specification

## Purpose

Extends rigor right of code by governing rollout, visibility, and unplanned loops for AI-generated changes so incidents feed back into intent instead of repeating.

## Requirements

### Requirement: Rollout checks scale with lane

The system SHALL require staged rollout, monitoring, and a rollback plan for Critical AI-generated changes, a rollout note for Standard, and no extra rollout ceremony for Lite beyond standard merge checks.

#### Scenario: Critical change requires rollback plan
- **WHEN** a Critical change is ready to ship without a staged rollout and rollback plan
- **THEN** ship readiness is denied with the missing rollout elements named

### Requirement: Agent visibility in production

The system SHALL record which parts of a shipped change were agent-generated versus human-written, with model and tool identifiers sufficient for later incident triage.

#### Scenario: Incident triage finds agent scope
- **WHEN** an incident review asks which hunks were agent-generated
- **THEN** the ship record identifies the agent scope without requiring session access

### Requirement: Unplanned loops close back to intent

The system SHALL treat incidents, test failures, security findings, and flaky builds as inputs that write a new intent, which re-enters the standard lane flow rather than bypassing it.

#### Scenario: Breach writes a new intent
- **WHEN** a security finding emerges from a shipped change
- **THEN** a new intent is opened capturing the finding, its lane is classified, and the fix proceeds through that lane's gates
