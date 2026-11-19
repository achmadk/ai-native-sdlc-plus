# sdlc-front-door Specification

## Purpose

Provide one discoverable interface to the existing SDLC checks and project lifecycle without duplicating policy or overstating what a local check has verified.

## Requirements

### Requirement: One CLI exposes the supported operations
The front door SHALL provide `init`, `lane`, `check spec`, `check brief`, `check evidence`, `doctor`, `update`, `uninstall`, `status`, and `explain <check-id>`. Source and installed entry points SHALL use the same command contract. Unknown operations SHALL fail with useful help rather than selecting or executing an arbitrary module.

#### Scenario: Discover the interface
- **GIVEN** an available source or installed front-door entry point
- **WHEN** a user requests top-level or subcommand help
- **THEN** the supported commands, required inputs, and delegated helper options are identified without modifying the project

#### Scenario: Unsupported command
- **GIVEN** an unknown command, including an unimplemented future alias
- **WHEN** the front door parses that command
- **THEN** it returns a usage error and does not report a check or operation as completed

### Requirement: Delegation preserves existing policy and results
Lane and check commands SHALL delegate to the existing implementations and preserve their arguments, stdin behavior, machine-readable output, and exit meanings. Legacy installer and checker entry points SHALL remain usable. A wrapper SHALL NOT turn a missing-evidence or inspector failure into success or promote a manual attestation into verified evidence.

#### Scenario: Evidence is incomplete
- **GIVEN** a CI-mode fixture with missing required evidence
- **WHEN** `check evidence` evaluates it
- **THEN** the result matches the direct checker, including its nonzero exit and missing-evidence details

#### Scenario: Native helper options
- **GIVEN** valid or invalid existing helper arguments and stdin bodies
- **WHEN** the front door forwards them
- **THEN** the observed result matches the helper contract without a stdout prefix corrupting JSON

### Requirement: Tooling and inspected data have separate roots
The CLI SHALL resolve executable helpers and resources from its selected trusted runtime, not from the repository it is inspecting. It SHALL work from unrelated working directories with explicit target inputs and SHALL fail when a required runtime component is unavailable. Repository content, PATH shadows, or ownership claims SHALL NOT supply replacement policy code.

#### Scenario: Inspect a hostile target
- **GIVEN** a target or working directory containing same-named fake helper modules
- **WHEN** the front door inspects the target
- **THEN** it uses its own runtime and retains the evaluated target only as data

#### Scenario: Missing runtime component
- **GIVEN** an installed runtime missing a required component
- **WHEN** a command needs that component
- **THEN** the CLI reports it and exits nonzero rather than silently omitting a check or searching the target for substitute code

### Requirement: Doctor guidance preserves findings
The front-door doctor SHALL group results into blocking, needs-human, and informational actions while retaining original check IDs, statuses, details, and raw counts. Each actionable finding SHALL identify an exact next command or an explicit discovery step when human input is missing. Strict-mode failures and unverified enforcement SHALL NOT be relabeled as passing results.

#### Scenario: A real blocker is present
- **GIVEN** a backend check failure or a warning made fatal by strict mode
- **WHEN** the front-door doctor groups the results
- **THEN** it retains the failure and nonzero result with an actionable next step

#### Scenario: Explain a finding
- **GIVEN** a recognized doctor check ID
- **WHEN** the user requests its explanation
- **THEN** the explanation describes the evidence, limitation, and next action without executing remediation

#### Scenario: Grouped counts remain honest
- **GIVEN** multiple findings sharing one actionable cause
- **WHEN** the doctor groups them
- **THEN** the group preserves each finding and reports both raw findings and action counts rather than hiding unrelated work

### Requirement: Fresh initialization has a verified local path
The documented empty-repository fixture SHALL reach a passing local Lite evidence check after explicit initialization and a genuine Lite change. Fresh-init doctor output SHALL have zero FAIL and at most three genuine needs-human action groups. Setup, unresolved hosted actions, and actual commands SHALL be recorded; installation changes themselves SHALL NOT be relabeled Lite.

#### Scenario: Fresh setup smoke test
- **GIVEN** the declared empty-repository setup and genuine Lite fixture on a supported platform
- **WHEN** the setup and Lite check are executed
- **THEN** the local check passes and the doctor target is verified from retained findings and commands without claiming hosted enforcement

#### Scenario: Setup target is missed
- **GIVEN** a fresh setup with a real FAIL or more needs-human groups than the declared target
- **WHEN** acceptance is evaluated
- **THEN** it remains incomplete and reports the result instead of changing severities or the measurement boundary

### Requirement: The wheel contains the complete offline runtime
A locally prepared wheel SHALL expose `sdlc`, declare Python 3.8+ compatibility and no runtime package dependencies, and include the allowlisted helpers/resources needed by its commands. Installation and execution SHALL not require a source checkout or Node. Packaging SHALL not publish an artifact or imply an untested package-runner result.

#### Scenario: Run the local wheel
- **GIVEN** a locally prepared wheel installed in an authorized isolated environment
- **WHEN** it is invoked outside the source checkout
- **THEN** the documented commands and resource lookups work, and dependency and file-record checks pass

#### Scenario: Optional runner is unavailable
- **GIVEN** an unavailable planned `uvx` or `pipx` smoke-test runner
- **WHEN** package-runner coverage is reported
- **THEN** that result remains unverified rather than being inferred from wheel metadata or another runner
