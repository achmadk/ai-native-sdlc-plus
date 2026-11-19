# Spec Delta

## Purpose

Keep product version, release notes, verified candidate inputs, and distribution artifacts coherent, and create release tags only for an explicitly authorized candidate.

## ADDED Requirements

### Requirement: Product release identity has one source
The system SHALL use one canonical product version for doctor and CLI output, distribution metadata, wheel filename, dist-info directory, and the planned changelog release. The selected release SHALL be `0.3.0`; client versions and schema versions SHALL remain distinct from the product version.

#### Scenario: Candidate version outputs agree
- **GIVEN** the canonical version `0.3.0` and recorded candidate CLI and wheel metadata
- **WHEN** release identity validation runs offline
- **THEN** all product-version outputs identify `0.3.0` and a mismatch fails validation

#### Scenario: A format version is not a product release
- **GIVEN** installation or result data with its own schema version
- **WHEN** release identity is checked
- **THEN** the schema version remains unchanged and cannot supply a substitute product version

### Requirement: Changelog maintenance preserves release history
The system SHALL add a `0.3.0` candidate entry covering verified changes since the recorded releases, preserve existing dated entries and cumulative patch-note history, and distinguish unreleased work from a tagged release. It SHALL NOT invent historical release dates, tags, or commit mappings.

#### Scenario: Candidate notes extend the existing history
- **GIVEN** existing `0.1.0` and `0.1.1` entries and verified change records
- **WHEN** the candidate changelog is generated or checked
- **THEN** an unreleased `0.3.0` entry describes the verified changes while the existing entries remain intact

#### Scenario: Historical chronology cannot be established
- **GIVEN** a cumulative patch round without a reliable release date or commit mapping
- **WHEN** candidate notes incorporate its relevant changes
- **THEN** the uncertainty is explicit and no historical date or release tag is fabricated

#### Scenario: Release date requires an actual release decision
- **GIVEN** candidate notes without authorized tagging
- **WHEN** release status is reported
- **THEN** the entry remains unreleased and does not imply that a release already exists

### Requirement: Release preflight verifies the candidate and artifacts
Release preflight SHALL require a clean candidate, coherent version and changelog, passing verification bound to all shipped inputs, complete required native-support evidence, and matching artifact metadata and hashes. It SHALL identify tested and release revisions separately and reject untested input changes, unavailable required evidence, or a conflicting target tag.

#### Scenario: Evidence-only commits preserve a verified candidate
- **GIVEN** a passing verification receipt at an ancestor revision and a clean candidate differing only in declared result or release-note outputs
- **WHEN** every verified input hash and native evidence reference matches the candidate
- **THEN** preflight accepts the relationship and reports both revisions without claiming a new execution at the release revision

#### Scenario: A shipped input changed after verification
- **GIVEN** a candidate with a source, policy, manifest, resource, or test input that differs from the recorded verification hashes
- **WHEN** preflight runs
- **THEN** it fails and names the stale input instead of reusing the previous pass

#### Scenario: Artifact identity or required evidence is incomplete
- **GIVEN** an artifact with mismatched metadata or a matrix missing a required native evidence level
- **WHEN** preflight validates release readiness
- **THEN** readiness remains incomplete and no tag is created

### Requirement: Release tags require explicit authorization
The system SHALL create a local annotated `v0.3.0` tag only after explicit authorization naming the release candidate and passing preflight. Existing tags SHALL NOT be moved or overwritten. Tagging SHALL NOT imply remote pushing, package publication, signing, or certification.

#### Scenario: Approved candidate receives a local tag
- **GIVEN** explicit tag authorization for the exact clean candidate and passing preflight results
- **WHEN** the release tag is created
- **THEN** the local annotated `v0.3.0` resolves to that candidate and its identity is recorded

#### Scenario: Tag permission is absent
- **GIVEN** planning or implementation approval without explicit tag authorization
- **WHEN** release preparation completes
- **THEN** no tag or remote publication occurs and the tagging task remains incomplete

#### Scenario: Target tag already exists
- **GIVEN** an existing local `v0.3.0` tag
- **WHEN** a release attempts to reuse the name
- **THEN** the attempt fails without altering the tag or creating a replacement release
