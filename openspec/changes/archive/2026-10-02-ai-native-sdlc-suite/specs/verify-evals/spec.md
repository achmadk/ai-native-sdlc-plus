# Spec Delta

## Purpose

Proves changes work through test-first verification and durable evaluations, so quality claims rest on measured deltas rather than assertions about velocity.

## ADDED Requirements

### Requirement: Test fails before it passes

The system SHALL require at least one verification test that is observed to fail before the fix and pass after it, for every behavior change.

#### Scenario: Bug fix demonstrates red to green
- **WHEN** a behavior fix is submitted without a failing-then-passing test
- **THEN** verification is marked incomplete and names the missing red-to-green evidence

### Requirement: Evaluation criteria with judge caveats

The system SHALL define evaluation criteria for every skill task eval, and where an automated judge is used the system SHALL document its limits and require a sampled human spot-check.

#### Scenario: Judge result carries caveats
- **WHEN** an eval uses an automated judge
- **THEN** the report states the judge's known blind spots and the human spot-check sample rate and outcome

#### Scenario: Incident converts to permanent eval
- **WHEN** an incident, security finding, flaky build, or test failure occurs
- **THEN** a permanent regression eval is added capturing the failure mode so recurrence is detected

### Requirement: With-skill versus baseline deltas

The system SHALL run each skill task eval both with and without the skill and SHALL report the delta in assertion pass rate, tokens, and time against pre-registered pass criteria, including negative results.

#### Scenario: Negative result is reported honestly
- **WHEN** a with-skill run underperforms baseline on any metric
- **THEN** the report publishes the negative delta and records the design correction, without retuning the eval to flatter the suite

### Requirement: Trigger accuracy with pushy descriptions

The system SHALL publish per-skill trigger descriptions stating what the skill does and when to use it with concrete trigger phrases, and SHALL measure should-trigger versus near-miss should-not-trigger accuracy.

#### Scenario: Near-miss does not trigger
- **WHEN** a near-miss query resembling but outside the skill's scope is issued
- **THEN** the skill does not activate and the eval records a true negative
