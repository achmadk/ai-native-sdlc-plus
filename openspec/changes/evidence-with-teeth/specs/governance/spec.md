# Spec Delta: governance

## ADDED Requirements

### Requirement: Machine-readable evidence manifest
The system SHALL support an `--emit-json <path>` flag on `evidence_check.py` to record an immutable, machine-readable evidence manifest documenting `head_sha`, `base_sha`, computed `lane`, matched rule, and per-item `status` and `verified_how` classification (`tracked-blob`, `pr-body-section`, `attested-flag`, or `api-checked`).

#### Scenario: Manifest records provenance and verification taxonomy
- **WHEN** `evidence_check.py --emit-json manifest.json` executes against an evaluated commit
- **THEN** the output JSON file contains `head_sha`, `base_sha`, `lane`, and each required evidence item labeled with its explicit `verified_how` method

#### Scenario: Manual present input is labeled attested
- **WHEN** `--present <item>` is passed to attest an evidence item
- **THEN** the item's `verified_how` is recorded as `attested-flag` and `status` as `attested`, never as `verified`

### Requirement: Approval cross-check with non-author verification
The system SHALL support cross-checking `Approved-by:` entries against hosted GitHub review states via `gh api` when available, verifying that approvals come from accounts distinct from the author, and requiring two distinct reviewers including at least one matching CODEOWNER for Critical lane changes.

#### Scenario: Author self-approval is rejected
- **WHEN** `Approved-by:` names the author of the pull request
- **THEN** approval verification fails and reports that authors cannot approve their own change

#### Scenario: Critical lane requires two distinct reviewers and CODEOWNER
- **WHEN** a Critical change is evaluated for approval verification
- **THEN** approval passes only if at least two distinct non-author approving reviews exist and at least one approving reviewer matches an applicable CODEOWNERS rule

#### Scenario: Offline execution reports unverified without false pass
- **WHEN** `gh` CLI is absent, unauthenticated, or network is unavailable
- **THEN** approval status is recorded as `unverified` with an informative warning, never falsely recorded as `verified`

