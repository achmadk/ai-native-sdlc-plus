# Spec Delta

## Purpose

Turns vague requests into explicit intent, acceptance criteria, constraints, and test expectations before any code is written, so review and verification have something to check against.

## ADDED Requirements

### Requirement: Single intent artifact per lane

The system SHALL produce one intent file for Lite and Standard changes and split intent from detailed specification for Critical changes.

#### Scenario: Standard feature gets combined spec
- **WHEN** a Standard change is specified
- **THEN** the output is a single file containing intent, acceptance criteria, constraints, and test expectations

#### Scenario: Critical change splits intent and spec
- **WHEN** a Critical change is specified
- **THEN** the output is a separate intent statement plus a detailed specification with threat considerations and rollout constraints

### Requirement: Acceptance criteria are testable

The system SHALL express every acceptance criterion as an observable behavior with explicit pass conditions, and SHALL include test expectations that can fail before the change and pass after it.

#### Scenario: Vague request becomes verifiable criteria
- **WHEN** a requester writes "make login faster"
- **THEN** the skill returns measurable criteria (e.g., conditions, thresholds, boundaries) plus at least one test expectation per criterion

#### Scenario: Untestable criterion is rejected
- **WHEN** a draft criterion has no observable pass condition
- **THEN** the skill flags it as untestable and proposes a testable rewrite instead of proceeding

### Requirement: One approval gate at highest judgment point

The system SHALL require exactly one human approval on the specification for Standard changes before build begins, and SHALL NOT require additional pre-approvals for Lite changes.

#### Scenario: Standard build waits for spec approval
- **WHEN** a Standard spec is complete but not yet human-approved
- **THEN** build work does not start and the worker states which approval is pending

#### Scenario: Lite change needs no pre-approval
- **WHEN** a Lite change has a short intent plus plan block in the PR
- **THEN** no pre-build approval is required, provided tests and trace evidence are present at merge
