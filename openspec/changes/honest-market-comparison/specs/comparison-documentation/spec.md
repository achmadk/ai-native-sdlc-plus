## Purpose

Helps users choose and combine development tools using traceable, versioned comparison claims and a reproducible example of this toolkit's enforcement behavior, without presenting documentation checks as evidence of market superiority.

## ADDED Requirements

### Requirement: Versioned primary-source comparison

The project SHALL publish a detailed comparison covering Spec Kit, OpenSpec, Kiro, BMAD, Superpowers, and Tessl. Every tool row SHALL identify the reviewed version or explicitly qualified rolling surface, primary source URLs, and an actual checked date. The comparison SHALL address documented capabilities, adoption constraints, fit, and limits on comparable terms. Missing or conflicting evidence MUST be reported as scoped uncertainty, not converted into a claim that a feature is absent.

#### Scenario: Required comparison is complete
- **WHEN** a user reads the detailed comparison
- **THEN** all six named tools have substantive rows with version/surface, primary-source, and checked-date metadata

#### Scenario: Capability could not be verified
- **WHEN** reviewed sources do not establish a capability or conflict about it
- **THEN** the row states what was reviewed and what remains unverified rather than claiming the capability does not exist

#### Scenario: Tool has several product surfaces
- **WHEN** IDE, CLI, cloud, or release-channel versions differ
- **THEN** the row identifies the relevant surfaces separately rather than presenting one version as proof about the entire product

### Requirement: Claims retain evidence qualification

Comparative facts, local results, and recommendations SHALL use the project's `[report-stated]`, `[measured here]`, and `[extrapolated]` distinctions. Local measurements SHALL identify their command, revision or input identity, environment, date, and limitations. Source-reported results MUST NOT be represented as measurements performed by this project, and recommendations MUST NOT be represented as proven superiority, certification, or exclusive capabilities without supporting evidence.

#### Scenario: Publisher reports behavior or a benchmark
- **WHEN** a comparison cites an upstream feature description or evaluation result
- **THEN** the source and evidence classification remain visible and the text does not imply an independent reproduction

#### Scenario: Project publishes a local measurement
- **WHEN** the project includes a timing or other measured result
- **THEN** readers can identify the actual invocation, evaluated state, environment, and what the result does not establish

#### Scenario: Existing user chooses a tool
- **WHEN** recommendations describe where another tool or this toolkit is useful
- **THEN** they distinguish documented facts from fit judgments and do not imply that planned WS2-WS8 capabilities are already implemented

### Requirement: Grounded README entry point

The README SHALL provide one concise positioning paragraph, a pointer for existing OpenSpec and Spec Kit users, a five-tool summary of the detailed comparison, and a blocked Critical-evidence demonstration using implemented commands. The summary SHALL retain source/date metadata for its rows. The demonstration SHALL state prerequisites, actual inputs, expected exit status, and the difference between local replay and hosted PR enforcement. A sixty-second claim MUST be supported by measurement within the declared prepared-checkout boundary, not by excluding undisclosed setup or weakening the failing check.

#### Scenario: Incomplete evidence is demonstrated
- **WHEN** the documented demo evaluates an identified Critical change with incomplete PR evidence
- **THEN** the real CI-mode checker returns the expected missing-evidence failure rather than a manual attestation, mocked success, or unrelated setup error

#### Scenario: Historical PR behavior is replayed locally
- **WHEN** the demo uses recorded PR revisions with a simplified body
- **THEN** it identifies those inputs and simplification, and does not claim to have created, edited, or rerun a hosted PR

#### Scenario: Setup or timing requirement is not met
- **WHEN** required history/tools are missing or the measured run exceeds the stated target
- **THEN** the limitation is visible and the demonstration is not reported as a completed sixty-second result

### Requirement: Comparison metadata is checked offline

Normal project verification SHALL include an offline documentation check that rejects missing required rows and invalid or absent version/surface, primary-source URL, checked-date, and evidence-qualification metadata. It SHALL cover the detailed comparison and README summary, including malformed and empty inputs. Passing this check MUST NOT be described as independent validation of a publisher's statements or as proof that an agent or hosted integration was tested.

#### Scenario: Incomplete metadata is introduced
- **WHEN** a required row loses a source, date, version/surface, or evidence qualification
- **THEN** the documentation check fails with the affected document and row identified

#### Scenario: Table is empty or structurally malformed
- **WHEN** a required comparison table is absent, empty, duplicated ambiguously, or malformed
- **THEN** verification fails instead of passing because no rows were parsed

#### Scenario: Review is run without network access
- **WHEN** the local or CI documentation check runs offline
- **THEN** it validates the recorded contract without fetching third-party content or claiming those sources were freshly reviewed
