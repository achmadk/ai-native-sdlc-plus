# Tasks

## 1. Phase 5a: Evidence Manifest & Provenance

- [x] 1.1 Add failing-first contract tests in `tests/test_evidence_check.py` asserting `--emit-json <path>` writes a structured manifest with `head_sha`, `base_sha`, `lane`, matched rule, and per-item `verified_how` taxonomy.
- [x] 1.2 Implement `--emit-json <path>` and `verified_how` taxonomy (`tracked-blob`, `pr-body-section`, `attested-flag`, `api-checked`) in `scripts/evidence_check.py`, ensuring `--present` inputs are labeled `attested`.
- [x] 1.3 Update `.github/workflows/sdlc-gate.yml` to generate `--emit-json evidence-manifest.json` and upload it via `actions/upload-artifact`.
- [x] 1.4 Add targeted mutation checks in `tests/mutate.py` for manifest provenance fields, `verified_how` classifications, and `attested` labeling; confirm all mutants are killed.

## 2. Phase 5b: Approval Cross-Check

- [x] 2.1 Add failing-first contract tests in `tests/test_evidence_check.py` covering hosted approval verification with test doubles: author self-approval rejection, Critical 2-reviewer + CODEOWNER rules, and offline `unverified` status.
- [x] 2.2 Implement approval verification in `scripts/evidence_check.py` using ambient `gh api` calls, reconciling `Approved-by:` entries against PR reviews and matching CODEOWNERS patterns from `doctor.py`.
- [x] 2.3 Implement offline fallback logic that records `unverified` with an informative warning when `gh` is unavailable, and implement strict enforcement for Critical CI gates when configured.
- [x] 2.4 Add targeted mutation checks in `tests/mutate.py` for non-author enforcement and CODEOWNER matching; confirm all mutants are killed.

## 3. Phase 5c: Semantic Test-Run Proof

- [x] 3.1 Add failing-first contract tests in `tests/test_redgreen.py` asserting `--junit <path>` detects runner collection crashes, rejects zero-test executions (`tests="0"`), and cross-checks AC-to-test mapping IDs.
- [x] 3.2 Implement standard-library JUnit XML parsing (`xml.etree.ElementTree`) in `skills/verify-and-evals/scripts/redgreen.py`, distinguishing collection `<error>` crashes from valid assertion `<failure>` states on the base commit.
- [x] 3.3 Implement cross-referencing between mapped acceptance criteria test identifiers in `tasks.md` and executed `<testcase>` records in the JUnit XML report.
- [x] 3.4 Add targeted mutation checks in `tests/mutate.py` for collection crash detection, zero-test rejection, and AC mapping verification; confirm all mutants are killed.

## 4. Integration Verification & Honest Documentation

- [x] 4.1 Update `LIMITATIONS.md` with the comprehensive evidence verification matrix detailing how each evidence kind is verified, what it proves, and what it still does not prove.
- [x] 4.2 Run full test discovery and mutation testing (`python tests/mutate.py`) on Windows and WSL, confirming zero test failures and zero surviving non-equivalent mutants.
- [x] 4.3 Validate the change with `openspec validate evidence-with-teeth --strict --no-interactive` and verify all planning artifacts conform to repository guidelines.

## Workflow follow-up

- Obtain named human approval on the Critical scope before implementing code.
- Implement and deliver each phase as a discrete pull request (5a, 5b, 5c).
- Archive the change after all three phases are merged into trunk.

