# Spec Delta

## Purpose

Routes every change to the right amount of ceremony by classifying risk deterministically and pointing the worker to the next required skill, while owning install, health checks, and brownfield onboarding.

## ADDED Requirements

### Requirement: Deterministic lane classification

The system SHALL classify every change into exactly one lane — Lite, Standard, or Critical — using published path and change-type rules from a config file, never by model judgment alone.

#### Scenario: Typo classified as Lite
- **WHEN** a change touches only documentation text with no behavior, auth, payment, migration, infra, or security-sensitive paths
- **THEN** the classifier outputs lane Lite with the matched rule cited

#### Scenario: Auth change classified as Critical
- **WHEN** a change touches authentication, payments, data migration, infrastructure, or a configured security-sensitive path
- **THEN** the classifier outputs lane Critical with the matched rule cited

#### Scenario: Ambiguous change defaults upward
- **WHEN** no rule matches unambiguously or inputs are malformed
- **THEN** the classifier outputs Standard or Critical (never Lite) and states the reason

### Requirement: Thin router with lazy cold paths

The system SHALL keep the always-loaded router context to skill names plus descriptions while full init, health-check, and onboarding detail loads only on explicit invocation.

#### Scenario: Route points to next skill
- **WHEN** a worker starts a change with a classified lane
- **THEN** the router returns the lane, the required evidence for that lane, and the single next skill to run

#### Scenario: Init and health checks are on-demand
- **WHEN** a worker invokes init or doctor without a classified change in progress
- **THEN** the system loads the full init or doctor guidance and does not burden normal routing with that detail

### Requirement: Evidence ladder enforcement

The system SHALL require lane-appropriate evidence (spec link, trace block, test changes, review notes) with advisory guidance locally, a visible warning on local mismatch, and a blocking verdict in CI; the CI verdict SHALL verify evidence exists, never assert it is good.

#### Scenario: Missing trace blocks merge in CI
- **WHEN** a Standard change reaches the CI check without its required trace block
- **THEN** the check fails with a message naming the missing artifact and the lane rule that requires it

#### Scenario: Local mismatch warns without blocking
- **WHEN** the same missing evidence is detected on a developer machine
- **THEN** the check emits a visible warning and exits without blocking local work

### Requirement: Brownfield onboarding without history retrofit

The system SHALL on-board existing repositories starting from the first new change and SHALL NOT require retrofitting history, decision logs, or specs for prior work.

#### Scenario: Existing repo onboards on next change
- **WHEN** init runs in a repository with existing unclassified history
- **THEN** setup completes for future changes and no backfill of prior changes is required
