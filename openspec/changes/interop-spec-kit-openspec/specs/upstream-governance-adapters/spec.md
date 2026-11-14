## Purpose

Provide opt-in governance packages that fit native OpenSpec and Spec Kit workflows, with explicit compatibility boundaries and evidence that distinguishes package registration from actual gate execution.

## ADDED Requirements

### Requirement: OpenSpec governance uses native schema mechanisms
The distribution SHALL provide an `sdlc-governed` schema accepted by the declared OpenSpec compatibility profile. It SHALL retain native proposal/spec/design/task artifacts and define Critical-only threat-note and rollout-plan artifacts through supported instructions and dependencies. It SHALL NOT invent conditional schema fields or equate file-existence status with policy enforcement.

#### Scenario: Schema is selected explicitly
- **WHEN** a project uses the distributed schema with the supported OpenSpec CLI
- **THEN** schema validation succeeds and artifact instructions resolve to the distributed templates

#### Scenario: Standard artifact omission
- **WHEN** the evaluated change is Standard
- **THEN** the instructions permit explicitly skipping the Critical-only artifacts without generating fake completed notes
- **AND** any remaining CLI file-existence status is reported honestly rather than presented as an enforced policy result

#### Scenario: Critical artifact obligation
- **WHEN** the evaluated change is Critical
- **THEN** the instructions require meaningful threat-note and rollout-plan artifacts and the independent gate rejects their absence

### Requirement: Operation guidance is opt-in and non-enforcing
The package SHALL provide an additive project-configuration fragment for OpenSpec apply/archive guidance that invokes the canonical gate with an identified repository, revision range, and evidence body. Adoption instructions SHALL preserve existing project configuration and require explicit selection. Guidance SHALL be described as instructions, not an automatic hook, approval, or hosted enforcement.

#### Scenario: Existing project configuration
- **WHEN** a maintainer adopts the documented fragment in a project with existing schema, context, rules, and operation guidance
- **THEN** the adoption procedure preserves those settings and adds only the selected governance guidance

#### Scenario: Gate inputs or runtime are unavailable
- **WHEN** operation guidance cannot identify its evaluation inputs or locate the canonical gate
- **THEN** it reports the missing prerequisite rather than claiming success, installing tools, or bypassing the check

### Requirement: Spec Kit gate integration delegates policy
The distribution SHALL provide a native Spec Kit extension with a namespaced gate command and declared workflow hook. When invoked, its executable delegate SHALL call WS3's published evidence-check interface and preserve its output and exit status. It SHALL NOT assume an unpublished command alias, duplicate lane/evidence policy, or claim that a registered hook was executed.

#### Scenario: Native extension registration
- **WHEN** the extension is installed in an isolated initialized project using the supported Spec Kit CLI and active integration
- **THEN** the CLI accepts its manifest, registers the namespaced command/hook, and resolves all declared files

#### Scenario: Gate rejects evidence
- **WHEN** the command's delegate invokes the canonical gate on incomplete evidence
- **THEN** the nonzero result is preserved without printing or recording a passing gate result

#### Scenario: Gate is not installed
- **WHEN** the delegate cannot locate the required gate runtime
- **THEN** it exits nonzero with a prerequisite diagnostic and does not substitute another policy engine or install dependencies

### Requirement: Spec Kit presets augment upstream templates
The distribution SHALL provide a separate native preset that composes governance additions with the upstream plan and task templates. It SHALL retain core template content and command identity, declare needed extension/version information, and avoid copying or replacing the core `speckit.*` commands. Dependency metadata SHALL NOT be treated as proof that the gate is installed or functional.

#### Scenario: Template composition
- **WHEN** the supported CLI resolves the preset's plan and task templates
- **THEN** the effective content contains both the current core content and the governance additions, including source-native test mapping guidance

#### Scenario: Core content changes
- **WHEN** a compatible upstream template changes beneath the preset
- **THEN** resolution uses that core template rather than a frozen command/template fork shipped by this project

#### Scenario: Preset is removed
- **WHEN** the maintainer removes the preset through the upstream CLI
- **THEN** the surviving template layers are restored and project specifications are not rewritten into this toolkit's native format

### Requirement: One guide maps workflow steps to lane evidence
One adoption guide SHALL map the supported native OpenSpec and logical Spec Kit workflow steps to their produced artifacts, lane-evidence roles, and verification levels. It SHALL identify remaining gate and human checks and distinguish integration-specific command spellings. This workflow mapping SHALL be separate from scenario-to-test mappings and SHALL NOT require a duplicate specification.

#### Scenario: Follow either upstream workflow
- **WHEN** a maintainer follows the guide for a supported OpenSpec or Spec Kit project
- **THEN** each relevant workflow step identifies what evidence it produces and which checks or approvals remain

#### Scenario: A step only declares evidence
- **WHEN** a workflow step scaffolds or configures an artifact without executing its check
- **THEN** the guide does not mark that evidence as tested, approved, or enforced

### Requirement: Clean-room adoption has measured step counts
Adding the gate to each supported upstream project SHALL be reproducible by script with a recorded adoption step count. The start/end boundary, prerequisite state, exclusions, and counting rule SHALL be declared before execution. Results SHALL retain executed commands/configuration actions and outcomes; estimates or unexecuted steps SHALL NOT be reported as measurements.

#### Scenario: Adopt into existing projects
- **WHEN** the adoption scripts run against isolated existing OpenSpec and Spec Kit fixtures
- **THEN** each run records its actual steps and count, tool versions, evaluation revision, and resulting Standard gate outcome under the declared boundary

#### Scenario: Adoption does not finish
- **WHEN** a prerequisite or adoption action fails
- **THEN** the record identifies the failure and any executed steps without claiming completed adoption or a count for unexecuted work

### Requirement: Compatibility claims require real upstream CLI evidence
Every declared compatibility profile SHALL have recorded real-CLI scaffolding, package validation, and fixture provenance, including versions, commands, source templates, and subsequent fixture edits. Template placeholders SHALL require authored content before positive gate checks. Unavailable tools or mock-only fixtures SHALL leave compatibility acceptance pending.

#### Scenario: Standard fixtures from both tools
- **WHEN** authored fixtures derived from actual OpenSpec and Spec Kit CLI scaffolds are checked
- **THEN** both pass the documented Standard contract and their records distinguish CLI-generated content from later fixture authoring

#### Scenario: Critical fixture transitions
- **WHEN** a supported Critical fixture is checked with neither required risk artifact, with either one missing, and with both populated
- **THEN** the incomplete cases fail and the complete case passes only when the other Critical evidence is also present

#### Scenario: Authoring tools are unavailable
- **WHEN** a required CLI or the declared version is unavailable
- **THEN** records identify the unexecuted acceptance work instead of claiming that static fixtures, a different version, or skipped tests establish compatibility

### Requirement: Adapter evidence distinguishes verification levels
The packages and their documentation SHALL distinguish schema/manifest acceptance, command materialization, direct delegate execution, local gate results, real-agent behavior, and hosted enforcement. Passing one level SHALL NOT attest another. The gate runtime SHALL remain usable without installing either authoring tool.

#### Scenario: Offline installed runtime
- **WHEN** the toolkit's owned runtime bundle is installed without the upstream CLIs
- **THEN** its documented fixture checks remain executable with the core runtime requirements and do not attempt network bootstrap

#### Scenario: Configuration is not execution
- **WHEN** an extension hook, operation guide, or evidence command is merely declared or materialized
- **THEN** the result is reported as configuration evidence, not as proof that an agent ran it or that repository protection enforces it
