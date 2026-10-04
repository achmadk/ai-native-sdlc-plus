# Spec Delta

## Purpose

Closes the gap between what the organization already knows and what the agent can see by packing prior decisions, incidents, rules, and ticket criteria into one compact reusable brief.

## ADDED Requirements

### Requirement: Compact brief with sources and staleness

The system SHALL assemble a context brief containing prior decisions, relevant incidents, security rules, standards, and ticket acceptance criteria, each with a source link and a staleness date, and SHALL keep the brief reusable across turns.

#### Scenario: Task needing incident knowledge succeeds
- **WHEN** an agent receives a task whose correct answer depends on a past incident record and a standards document
- **THEN** the brief includes both sources with links and dates, and the agent's answer cites them

#### Scenario: Stale source is flagged
- **WHEN** a source exceeds its declared freshness window or has been superseded
- **THEN** the brief marks it stale and states which newer source replaces it

### Requirement: No duplication of existing writing

The system SHALL reference existing documents by link rather than copying their content, and SHALL include only the minimum excerpt needed to act.

#### Scenario: Standard already documented elsewhere
- **WHEN** a coding standard exists in the repo
- **THEN** the brief links to it with a one-line summary instead of reproducing the full text

### Requirement: lane-proportional depth

The system SHALL scale brief depth with lane risk: Lite receives at most a pointer list, Standard a short brief, Critical a full brief with security and incident sections.

#### Scenario: Lite change gets pointer list only
- **WHEN** a Lite change requests context
- **THEN** the output is a short pointer list with no more than five minutes of reading overhead
