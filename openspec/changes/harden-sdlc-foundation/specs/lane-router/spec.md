## MODIFIED Requirements

### Requirement: Deterministic lane classification

The system SHALL classify every change into exactly one lane, Lite, Standard, or Critical, using published deterministic path rules and available Git change-type and mode information, never model judgment alone. The highest applicable risk SHALL win. The full gate execution, installation, CI adapter, and documented agent-control boundary SHALL have a non-overridable Critical floor, including newly added files. Shipped configurable rules SHALL cover root and nested authentication, payment, migration, infrastructure, and security directories. Directory names alone MUST NOT establish that executable or indeterminate content is documentation-only, and dependency lockfiles SHALL default to at least Standard. Custom configuration format version 1 SHALL remain supported without silently replacing local rules.

#### Scenario: Typo classified as Lite
- **WHEN** a change touches only recognized documentation text with no executable mode, type change, or behavior/security-sensitive path
- **THEN** the classifier outputs Lite with the matched rule cited

#### Scenario: Auth change classified as Critical
- **WHEN** a change touches authentication, payment, migration, infrastructure, or security paths recognized by the published defaults or repository calibration, including `src/auth/login.py` and `src/payments/charge.py`
- **THEN** the classifier outputs Critical with the matched rule cited

#### Scenario: Ambiguous change defaults upward
- **WHEN** no rule matches unambiguously or an input path is malformed
- **THEN** classification outputs Standard or Critical, never Lite, and preserves the reason without hiding any valid Critical path

#### Scenario: New execution dependency remains Critical
- **WHEN** a change adds an importable file such as `scripts/json.py`, modifies an installer or its manifest, or changes a shipped CI runner or agent instruction file
- **THEN** the built-in boundary rule makes the change Critical even when a custom configuration otherwise matches it as Lite

#### Scenario: Executable documentation is not Lite
- **WHEN** a change adds `docs/deploy.sh`, changes a documentation file to executable mode, or introduces a symlink or indeterminate file type under a documentation directory
- **THEN** it receives at least Standard and is not eligible for a documentation-only test exemption

#### Scenario: Lockfile does not inherit documentation ceremony
- **WHEN** a change modifies only a dependency lockfile such as `yarn.lock`
- **THEN** the shipped policy classifies it as at least Standard rather than Lite

#### Scenario: Rename retains the original risk
- **WHEN** a change moves a file out of a Critical path into a lower-risk path
- **THEN** both sides of the move remain visible to classification and the change stays Critical

### Requirement: Evidence ladder enforcement

The system SHALL require lane-appropriate evidence with advisory guidance locally, visible warnings on local mismatch, and a blocking verdict in CI. The verdict SHALL establish evidence presence and supported structure, never semantic quality, authenticated approval, or successful test execution. Fenced-code content and template comments MUST NOT supply headings, links, lane declarations, or waivers. Automatic non-executable exemptions MUST account for every changed path and available type/mode information; an unprocessable path SHALL cause a CI tooling error rather than disappear from that calculation. Local spec and intent references SHALL resolve to nonempty regular tracked blobs in the evaluated revision, not Git metadata, untracked working files, or escaping links. External URLs SHALL remain explicitly unverified references rather than authenticated evidence.

#### Scenario: Missing trace blocks merge in CI
- **WHEN** a Standard change reaches the CI check without its required trace block
- **THEN** the check fails with a message naming the missing artifact and the lane rule that requires it

#### Scenario: Local mismatch warns without blocking
- **WHEN** the same missing evidence is detected on a developer machine
- **THEN** the check emits a visible warning and exits without blocking local work

#### Scenario: Longer Markdown fence encloses apparent evidence
- **WHEN** a PR body places apparent evidence between shorter backtick or tilde lines inside a longer matching fence
- **THEN** none of the enclosed headings, keys, lane declarations, or waivers satisfy evidence requirements

#### Scenario: Invalid closing fence does not expose evidence
- **WHEN** an apparent closing fence has a different marker, is shorter than the opener, or contains forbidden trailing text
- **THEN** the parser keeps the following apparent evidence inside the original fence

#### Scenario: Malformed source path cannot disappear from exemption checks
- **WHEN** a diff contains a documentation path and a source filename containing a newline or another unprocessable control character
- **THEN** CI reports the malformed path safely and exits with a tooling error without granting the documentation-only exemption

#### Scenario: Repository metadata or untracked file is linked as a spec
- **WHEN** a PR links `.git/config`, an untracked file, a symlink, or a path absent from the evaluated revision as local spec or intent evidence
- **THEN** that reference fails validation even if a nonempty file exists in the checkout

#### Scenario: Tracked candidate evidence is accepted structurally
- **WHEN** a local reference identifies a nonempty regular tracked blob in the evaluated revision and remains within the repository
- **THEN** it satisfies the presence check without asserting that its content is a good spec or an approved intent

#### Scenario: Presence-only limitations remain visible
- **WHEN** a valid external URL, a review-notes section, or a syntactically valid test waiver is present
- **THEN** the result states the corresponding unverified or human-review limitation and does not claim authenticated approval or behavioral test proof
