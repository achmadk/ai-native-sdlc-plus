# Spec Delta

## MODIFIED Requirements

### Requirement: Generation has one source and detectable drift
Generated files SHALL derive from shared trusted templates, the canonical skill catalog, and project policy rather than independent hand-maintained copies. Status/update SHALL distinguish stale generated output from user-edited output. Duplicate destinations, overlapping discovery roots, and case collisions SHALL be handled explicitly without overwriting unrelated files or inventing additional product skills. One profile contract SHALL supply selectors and native path metadata.

#### Scenario: Canonical policy changes
- **GIVEN** generated files still match their recorded owned hashes
- **WHEN** the canonical project policy changes
- **THEN** status identifies regeneration needs and update can refresh those generated files without changing the policy

#### Scenario: A generated file was edited
- **GIVEN** a generated file that no longer matches its recorded ownership hash
- **WHEN** regeneration evaluates that destination
- **THEN** it preserves the file and reports the conflict instead of overwriting it

#### Scenario: Cursor compatibility files share policy content
- **GIVEN** canonical `AGENTS.md` and declared `.cursorrules` and `.cursor/rules/sdlc.mdc` compatibility outputs
- **WHEN** adapter generation and drift validation run
- **THEN** both outputs retain the canonical policy content in their native wrappers, and an independent edit to either fails the drift check

#### Scenario: Rendered and managed destinations disagree
- **GIVEN** a profile contract whose rendered destinations differ from recognized or recovery paths
- **WHEN** profile contract tests validate all seven profiles
- **THEN** validation fails before publishing inconsistent installation or support data

### Requirement: Discovery evidence states its level
Initialization and documentation SHALL distinguish file generation, native discovery, and observed execution. Fixture/snapshot tests SHALL cover all declared formats, including Claude and Copilot, and actual loader evidence SHALL name its tool version and surface. Unavailable or untested loaders SHALL remain unverified; generating a file SHALL not certify behavior. Records SHALL identify their evidence level independently.

#### Scenario: Snapshot passes without a real loader run
- **GIVEN** generated files matching the documented native format
- **WHEN** the target client has not actually loaded them
- **THEN** the result reports configuration/fixture validation only

#### Scenario: Native command or discovery fails
- **GIVEN** an actual loader probe for a generated native entry
- **WHEN** the target cannot discover it or finds an ambiguous duplicate
- **THEN** that profile's acceptance remains incomplete until corrected rather than being counted as supported execution

#### Scenario: Generic scans do not establish native discovery
- **GIVEN** file-presence checks, a generic skill scan, or a canonical-skill provider harness result
- **WHEN** a support result is classified
- **THEN** it cannot count as discovery of the target client's generated native paths or execution of its command surface

## ADDED Requirements

### Requirement: Native support has fixed acceptance targets
Support acceptance SHALL require Level 1 instruction-file generation and Level 2 native skill discovery for `claude`, `cursor`, `copilot`, `codex`, `gemini`, `opencode`, and `kilo`, plus Level 3 behavioral evidence for Claude Code and OpenCode V2. Each result SHALL identify its client, version, surface, and platform; unavailable required evidence SHALL leave acceptance incomplete.

#### Scenario: Required targets are complete
- **GIVEN** valid Level 1 and Level 2 records for all seven profiles and Level 3 records for Claude Code and OpenCode V2
- **WHEN** acceptance evaluates the declared client/version/platform targets
- **THEN** the required targets are complete without implying results for other platforms or client versions

#### Scenario: A required native client is unavailable
- **GIVEN** a generated profile whose required client or safe discovery surface is unavailable
- **WHEN** acceptance evaluates that profile
- **THEN** the unavailable level remains unverified and the corresponding acceptance task cannot be marked complete

#### Scenario: Similar clients are not substitutes
- **GIVEN** Kilo evidence submitted for OpenCode V2, Antigravity evidence for Gemini CLI, or Copilot CLI evidence for VS Code prompt files
- **WHEN** target identity and surface are validated
- **THEN** the substitute cannot satisfy the required native target

### Requirement: Native probe evidence is controlled and replayable
Native evidence SHALL use a committed probe registration, isolated positive and negative scratch projects, generated-source hashes, exact client/version identity, and reviewed redacted records. Level 2 SHALL demonstrate that client's loader discovery; Level 3 SHALL demonstrate registered behavior rather than prompted or filesystem-read answers. Offline replay SHALL validate records without client or model calls.

#### Scenario: Native loader identifies the generated skill
- **GIVEN** a recorded native loader result naming the exact generated scratch path and unique registered skill, absent from the negative control
- **WHEN** evidence validation checks the registration, source hashes, and client identity
- **THEN** it accepts discovery only for that client/version/surface/platform

#### Scenario: Behavioral evidence comes from the loaded skill
- **GIVEN** a reviewed native transcript with a registered skill-only nonce, matching load evidence, and a negative control lacking the nonce
- **WHEN** deterministic replay validates the behavior and permitted tool events
- **THEN** it accepts the registered behavior without treating general response quality as proven

#### Scenario: Global content causes a false positive
- **GIVEN** a negative-control result that discovers the purported project skill or emits its skill-only nonce
- **WHEN** probe evidence is checked
- **THEN** the probe fails instead of crediting project-native discovery or behavior

#### Scenario: Startup or call authorization is unsafe
- **GIVEN** a client requiring unauthorized credential use, live calls, updates, plugins, hooks, or permission changes
- **WHEN** a probe is prepared
- **THEN** it does not run and records the missing isolation or authorization as a blocker

#### Scenario: Transcript provenance or secrets are invalid
- **GIVEN** a record with stale source hashes, missing terminal outcome, mismatched client identity, or secret material
- **WHEN** offline evidence validation runs
- **THEN** it rejects the record without publishing its sensitive content or replacing the missing proof

### Requirement: Support matrix is generated from result records
The support matrix SHALL be generated deterministically from the profile contract and validated evidence records, with separate status and evidence references for each level. It SHALL show required versus achieved targets, failures, unavailable coverage, and tested revisions. Hand-edited matrix drift or stale evidence SHALL fail validation; renderer metadata alone SHALL NOT assign passing results.

#### Scenario: Matrix is regenerated offline
- **GIVEN** unchanged profile data and reviewed committed evidence records
- **WHEN** the matrix is regenerated without native clients or model credentials
- **THEN** its generated section is identical and includes all seven profiles with their exact surfaces and level statuses

#### Scenario: A matrix cell is hand-edited
- **GIVEN** a generated support section whose result or evidence reference was changed manually
- **WHEN** the drift check compares it with validated records
- **THEN** it fails and identifies the differing cell instead of accepting the new claim

#### Scenario: A previously passing source changed
- **GIVEN** native evidence for adapter or skill hashes that no longer match the candidate
- **WHEN** the current matrix is generated
- **THEN** affected levels are rejected as stale rather than carried forward as a current pass
