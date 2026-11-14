# Proposal

## Why
Currently, the SDLC gate verifies that evidence structurally exists, but cannot prove substance: `--present` flags are self-attested, `Approved-by:` is unauthenticated markdown text that an author or agent can forge, and `redgreen.py` compares process exit codes rather than actual test execution results. To achieve defensible merge-time enforcement, the toolkit must record machine-verifiable evidence provenance, cross-check approvals against real GitHub review activity, and prove semantic test execution using JUnit XML test reports.

## What Changes
This change implements Workstream 5 (WS5: `evidence-with-teeth`) across three staged phases:

- **Phase 5a: Evidence Manifest & Provenance (`evidence_check.py --emit-json`)**
  - Add `--emit-json <path>` to `scripts/evidence_check.py` to record an immutable, machine-readable evidence manifest capturing `head_sha`, `base_sha`, computed `lane`, matched rule, and per-item `status` and `verified_how` classification (`tracked-blob`, `pr-body-section`, `attested-flag`, `api-checked`).
  - Label all manual `--present` inputs as `attested` across both JSON and human-readable output, ensuring attested waivers cannot be confused with verified artifacts.
  - Update `.github/workflows/sdlc-gate.yml` to save and upload the generated `evidence-manifest.json` as a workflow artifact.

- **Phase 5b: Approval Cross-Check (`Approved-by:` & `gh api`)**
  - Integrate optional GitHub review cross-checks into `scripts/evidence_check.py` using ambient `gh api` CLI (zero external Python dependencies, stdlib only).
  - Verify that `Approved-by:` matches an actual GitHub user with an `APPROVED` review state who is NOT the PR author.
  - For `Critical` lane changes, require at least two distinct approving reviewers, with at least one reviewer matching path patterns in `CODEOWNERS`.
  - Enforce honest offline fallback: if `gh` is unavailable or unauthenticated, record status as `unverified` (never silently `ok`); emit a prominent warning by default and provide a `--require-approvals` option or Critical CI gate check to fail closed when approvals cannot be verified.

- **Phase 5c: Semantic Test-Run Proof (`redgreen.py --junit`)**
  - Extend `redgreen.py` to accept `--junit <path>` pointing to a JUnit XML report produced during the test run.
  - Parse test report data via Python stdlib `xml.etree.ElementTree` to detect runner collection crashes (distinguishing them from true assertion failures), detect zero-test runs (`tests="0"`), and verify that declared AC-to-test mapping IDs from the spec or `tasks.md` actually executed.
  - Update `LIMITATIONS.md` with an evidence verification matrix documenting what each evidence kind proves and what it still does not prove.
  - Add targeted mutation test entries in `tests/mutate.py` for each phase, ensuring 0 surviving non-equivalent mutants.

## Capabilities

### Modified Capabilities
- `governance`: Add machine-readable evidence manifest emission (`--emit-json`), per-item `verified_how` provenance tracking, and reviewer verification against GitHub PR reviews and CODEOWNERS.
- `verify-evals`: Add JUnit XML test report verification (`--junit <path>`), runner collection error detection, zero-test run detection, and AC-to-test execution cross-checks in `redgreen.py`.

## Impact
- **Affected code**: `scripts/evidence_check.py`, `scripts/redgreen.py`, `skills/verify-and-evals/scripts/redgreen.py`, `scripts/sdlc.py`, `.github/workflows/sdlc-gate.yml`, `LIMITATIONS.md`.
- **Dependencies**: None. Pure Python standard library (>= 3.8); uses ambient `gh` CLI only when available.
- **Breaking changes**: None. Existing CLI flags (`--json`, `--ci`, `--present`) retain complete backward compatibility.

