## Purpose

Let teams validate existing OpenSpec and Spec Kit documents as lane-appropriate evidence without rewriting their specifications, while retaining native compatibility and revision-bound trust checks.

## ADDED Requirements

### Requirement: OpenSpec change folders are specification inputs
The validators SHALL accept a supported OpenSpec folder containing an authored proposal, delta specifications, design, and tasks as one specification input. Standard evidence SHALL use the specification bundle; Critical intent evidence SHALL resolve to its proposal. Acceptance SHALL NOT require moving files or producing a native-format copy.

#### Scenario: Standard OpenSpec adoption
- **GIVEN** a complete supported OpenSpec change with source-linked test expectations and the other Standard PR evidence
- **WHEN** the folder is supplied to the spec validator and as the PR's `Spec:` reference
- **THEN** both checks accept the input without modifying its documents or locations

#### Scenario: Missing member is not a complete bundle
- **WHEN** a selected OpenSpec folder lacks its proposal, design, tasks, or any delta specification
- **THEN** validation reports the missing member and does not treat directory existence as sufficient specification evidence

#### Scenario: An explicit invalid intent is not hidden
- **GIVEN** a Critical PR references a valid OpenSpec bundle and also supplies an invalid explicit intent link
- **WHEN** its evidence is checked
- **THEN** the explicit intent fails validation rather than silently falling back to the bundle's proposal

### Requirement: Spec Kit feature folders are specification context
The validators SHALL accept a supported Spec Kit feature folder containing authored `spec.md`, `plan.md`, and `tasks.md` as one specification-context input. They SHALL retain the native story, requirement, and success-criterion references rather than require native AC rows. A Critical Spec Kit input SHALL retain the explicit intent-reference requirement.

#### Scenario: Standard Spec Kit adoption
- **GIVEN** a complete supported Spec Kit feature with test expectations and the other Standard PR evidence
- **WHEN** its feature folder is supplied to the validators
- **THEN** the specification, plan context, and task mappings are read in place and the checks accept the Standard input

#### Scenario: Incomplete or ambiguous layout
- **WHEN** a folder is incomplete, unsupported, or matches conflicting upstream layouts
- **THEN** the validators identify the layout problem without silently selecting another dialect or accepting the input as a native file

### Requirement: Native acceptance units retain source traceability
Every imported acceptance scenario SHALL have a unique source reference, observable outcome, test expectation, and non-placeholder fails-before explanation. OpenSpec references SHALL preserve capability path, delta operation, requirement, and scenario; Spec Kit references SHALL preserve the source story and scenario. Test mappings SHALL NOT require renumbering these units as native AC identifiers.

#### Scenario: Multiple capabilities reuse a scenario title
- **WHEN** two OpenSpec capabilities contain a scenario with the same title
- **THEN** the mappings remain distinct through their source paths and requirement context

#### Scenario: Mapping is missing or stale
- **WHEN** an imported scenario lacks a mapping or a mapping names an unknown source unit
- **THEN** validation reports the affected file and source unit rather than silently dropping it

#### Scenario: Evidence hidden in examples
- **WHEN** a required scenario or mapping appears only inside a comment or fenced example
- **THEN** it does not satisfy the imported contract

### Requirement: Operation-only deltas cannot pass vacuously
Imported OpenSpec ADDED and MODIFIED requirements SHALL expose their scenarios. REMOVED and RENAMED operations SHALL retain their native identities and require explicit transition expectations and test mappings. Duplicate or unsupported operations SHALL be diagnosed, not discarded to manufacture a zero-criterion success.

#### Scenario: Removal-only change
- **WHEN** a change only removes a requirement
- **THEN** validation requires its removal rationale, migration information, and a mapped observable regression expectation

#### Scenario: Rename-only change
- **WHEN** a change only renames a requirement
- **THEN** the original and replacement identities remain visible in the mapping and an explicit transition expectation is required

### Requirement: Imported Critical evidence follows the computed lane
A Critical upstream bundle SHALL contain meaningful `threat-note.md` and `rollout-plan.md` artifacts. Standard bundles SHALL NOT require them. A bundle's declared lane, upstream completion status, or conditional-artifact skip SHALL NOT lower computed risk or waive required PR trace, review, and test evidence.

#### Scenario: Critical artifacts are absent
- **GIVEN** a Standard-valid bundle in a change whose computed lane is Critical
- **WHEN** neither risk artifact is present, or only one is present
- **THEN** Critical validation fails and identifies each missing artifact, even if inline PR text or task checkboxes suggest completion

#### Scenario: Critical artifacts are populated
- **GIVEN** both Critical artifacts contain substantive content and the remaining intent, spec, test, trace, and review requirements are satisfied
- **WHEN** the Critical change is evaluated
- **THEN** the folder's artifacts satisfy the corresponding evidence obligations with their sources identified

#### Scenario: Empty artifacts cannot satisfy the lane
- **WHEN** a required artifact contains only headings, comments, or placeholder text
- **THEN** it fails validation rather than counting as completed Critical evidence

### Requirement: CI evaluates constituent blobs at the selected revision
CI bundle validation SHALL read every selected local member from the evaluated commit as a nonempty regular tracked blob. It SHALL reject unsafe references and selected symlink, gitlink, or escaping members. Checkout contents and newer revisions SHALL NOT substitute for that snapshot, and operational Git failures SHALL remain distinguishable from missing evidence.

#### Scenario: Working-tree completion does not repair a candidate
- **GIVEN** a required bundle member is absent or empty in the evaluated commit
- **WHEN** the working tree or a later commit supplies a valid replacement
- **THEN** the evaluated candidate still fails

#### Scenario: Untrusted member or path
- **WHEN** a selected member is untracked, a symlink or gitlink, traverses outside the bundle/repository, or refers to Git metadata
- **THEN** it is rejected rather than followed or executed

#### Scenario: Lookup fails
- **WHEN** Git cannot resolve the evaluated revision or read the required metadata or content
- **THEN** CI reports an inspector/tooling failure, not a passing or merely absent-evidence result

### Requirement: Bundle validation is bounded and offline
Bundle checks SHALL enforce documented input limits and reject malformed text with actionable, sanitized diagnostics. They SHALL NOT require upstream CLIs, network access, execution of document instructions, or execution of mapped test commands. A valid mapping SHALL be described as a test expectation, not proof that the test ran or passed.

#### Scenario: Upstream tools are absent
- **WHEN** a supported committed fixture is validated offline without OpenSpec or Spec Kit installed
- **THEN** normal bundle validation still works

#### Scenario: Hostile or excessive input
- **WHEN** a bundle exceeds the documented limits or contains invalid encoding, unsafe diagnostic text, or attempted executable instructions
- **THEN** the check fails safely or treats instructions as data, without emitting secrets or workflow commands

### Requirement: Existing native behavior remains compatible
Native file inputs SHALL retain existing validation rules, approval requirements, criterion caps, command options, and result/exit semantics. Existing URL evidence SHALL remain explicitly unverified. Local warnings SHALL NOT become CI passes, and importing upstream documents SHALL NOT imply human approval or real-agent validation.

#### Scenario: Native regression fixtures
- **WHEN** the existing native valid and invalid fixtures are checked after interoperability is added
- **THEN** their outcomes and native machine-readable output contract are unchanged

#### Scenario: Approval is requested explicitly
- **WHEN** an upstream draft is checked with approval required, or claims approval with invalid approval metadata
- **THEN** it fails the approval check instead of deriving approval from an upstream status or completed task list

#### Scenario: Evidence remains incomplete
- **WHEN** an imported bundle is valid but required PR trace, review, or test-change evidence is absent
- **THEN** CI still fails and local mode still reports the missing evidence according to the existing mode contract
