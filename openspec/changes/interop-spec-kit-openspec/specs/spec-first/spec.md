## MODIFIED Requirements

### Requirement: Single intent artifact per lane

The system SHALL preserve native outputs: one intent file for Lite and Standard, and separate intent and detailed specification for Critical. It SHALL also accept a supported existing upstream bundle as one logical specification input without moving or duplicating its specifications. A Critical bundle SHALL still provide identifiable intent and specification content and the required threat and rollout evidence.

#### Scenario: Standard feature gets combined spec
- **WHEN** a Standard change is specified using the native authoring format
- **THEN** the output is a single file containing intent, acceptance criteria, constraints, and test expectations

#### Scenario: Critical change splits intent and spec
- **WHEN** a Critical change is specified using the native authoring format
- **THEN** the output is a separate intent statement plus a detailed specification with threat considerations and rollout constraints

#### Scenario: Existing upstream specification remains authoritative
- **WHEN** a project supplies a supported OpenSpec or Spec Kit bundle with lane-appropriate intent, acceptance units, context, and source-linked test expectations
- **THEN** the existing documents remain the specification input without a mandatory native-format copy
- **AND** testability and human-approval obligations remain unchanged
