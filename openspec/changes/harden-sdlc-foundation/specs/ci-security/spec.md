## ADDED Requirements

### Requirement: Working least-privilege PR secret scanning

The GitHub secret-scanning workflow SHALL supply the credentials explicitly required by its pinned scanner action, with read-only repository and pull-request permissions sufficient for scanning. It MUST disable optional PR comments rather than request write access and MUST NOT require privileged execution of untrusted PR code. A clean completed scan, a detected secret, and scanner failure SHALL remain distinguishable. Secret findings and scanner errors MUST fail the check.

#### Scenario: Clean pull request is scanned
- **WHEN** a clean PR is scanned in a supported repository with required scanner prerequisites available
- **THEN** the scanner completes successfully rather than exiting because its token environment variable is absent

#### Scenario: Secret or scanner error blocks the check
- **WHEN** a scan detects a seeded non-production secret fixture or cannot execute because a required credential, license, or API permission is unavailable
- **THEN** the check fails with the corresponding finding or setup diagnostic and does not report a clean scan

#### Scenario: Fork and private-repository constraints are honored
- **WHEN** the workflow handles a supported fork PR or private-repository PR
- **THEN** it performs the scan with read-only credentials, does not post comments, and does not require `pull_request_target` or execute PR test/setup commands with elevated privileges

### Requirement: Immutable enforcement actions

Every external action used by the evidence and secret-scanning workflows SHALL be pinned to a full immutable commit SHA. Checkout credentials MUST NOT remain persisted in the inspected repository. Changes to action pins SHALL be reviewed as changes to the enforcement boundary.

#### Scenario: Mutable action reference is introduced
- **WHEN** an enforcement workflow uses a branch, release tag, or abbreviated commit instead of an approved full action SHA
- **THEN** the workflow contract test fails and doctor reports the pinning gap

#### Scenario: Enforcement checkout does not retain credentials
- **WHEN** either enforcement workflow checks out repository content
- **THEN** checkout is configured not to persist its credentials in the checkout

### Requirement: Isolated trusted gate execution

The GitHub evidence workflow and generic CI runner SHALL execute the checker and lane policy from the trusted base commit while inspecting the explicit candidate revision. Their Python execution MUST exclude ambient repository, user-site, and environment-supplied import paths. Loading the required lane module MUST NOT make unrelated files in its directory importable ahead of standard-library modules. Evidence extraction MUST NOT execute candidate code.

#### Scenario: Candidate edits its own checker or policy
- **WHEN** a PR changes the gate implementation or lane configuration
- **THEN** its evidence verdict still uses the trusted base implementation and configuration

#### Scenario: Adjacent module attempts to shadow a dependency
- **WHEN** a file named like a standard-library dependency exists next to trusted checker scripts or is supplied through an ambient Python path
- **THEN** enforcement does not import that file and cannot return success because its top-level code exits early

#### Scenario: Candidate code is not executed to inspect evidence
- **WHEN** a candidate contains executable files, symlinks, or test setup commands
- **THEN** the presence gate inspects Git metadata and evidence without invoking those files or commands

### Requirement: Enforcement failures propagate on supported PR events

The supported GitHub profile SHALL run evidence validation for PR open, synchronization, reopen, description edit, and ready-for-review events. Neither the gate nor scanner SHALL ignore failed execution through `continue-on-error`, unconditional success fallbacks, or a skipped required step. A rerun of an older event MUST NOT be documented as evaluating a newly edited PR body. Merge queues SHALL be reported as outside this profile until a separately specified merge-group evidence contract exists.

#### Scenario: Gate step is skipped or its failure ignored
- **WHEN** a supported workflow is altered so the gate step is skipped or a nonzero exit no longer fails the job
- **THEN** the workflow contract test fails and strict enforcement readiness cannot succeed

#### Scenario: PR description changes
- **WHEN** a contributor updates required evidence in a PR description
- **THEN** a new evidence run is triggered, and the documentation directs the contributor to that run rather than a rerun carrying an old event body
