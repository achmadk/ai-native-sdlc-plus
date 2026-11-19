# Design: Evidence with Teeth (WS5)

## Context
See [proposal.md](proposal.md) for problem statement and requirements.
Currently, `scripts/evidence_check.py` verifies presence but does not record an immutable audit manifest, treats self-attested `--present` flags uniformly with verified blobs, and accepts unverified `Approved-by:` text strings. Meanwhile, `skills/verify-and-evals/scripts/redgreen.py` evaluates process exit codes without verifying test execution semantics or collection integrity.

## Goals / Non-Goals

**Goals:**
- **PR 5a (Manifest)**: Emit a machine-readable JSON manifest recording commit provenance, lane, matched rule, and per-item `verified_how` classifications; upload in CI.
- **PR 5b (Approvals)**: Validate `Approved-by:` against GitHub reviews via ambient `gh` CLI (non-author check; 2 reviewers + CODEOWNER on Critical; `unverified` fallback when offline).
- **PR 5c (Test Proof)**: Support `--junit <path>` in `redgreen.py` to detect collection crashes, reject 0-test runs, and verify executed test names against declared AC mappings.
- Document capabilities and boundaries in `LIMITATIONS.md`.

**Non-Goals:**
- No direct network or HTTP dependencies in Python: all GitHub queries use the ambient `gh` CLI.
- No mandatory test runner wrapping: the user or CI script provides the JUnit XML path to `redgreen.py`.
- No automated authorization bypass or synthetic review generation.

## Decisions

### 1. Separation of `--json` and `--emit-json <path>`
- Keep `--json` for emitting machine-readable output to stdout for CLI pipelines.
- Add `--emit-json <path>` to write the complete evidence manifest file independently of stdout formatting, allowing standard verbose logging in CI while saving the artifact.

### 2. Evidence Verification Taxonomy (`verified_how`)
Each evidence entry in the manifest carries a `verified_how` field:
- `tracked-blob`: Blob tracked at evaluated commit, read via Git revision reader.
- `pr-body-section`: Markdown section parsed with meaningful content (>= 20 characters).
- `attested-flag`: Explicit user assertion via `--present <item>` (labeled `attested`, never `verified`).
- `api-checked`: External verification via ambient `gh api` inspection.

### 3. Reviewer Verification via Ambient `gh`
Following the pattern established in `scripts/doctor.py:713`:
- Check for `gh` CLI availability before querying.
- Query pull request reviews via `gh api repos/{owner}/{repo}/pulls/{number}/reviews`.
- Verify approving user != PR author.
- For Critical changes: verify at least 2 distinct approving reviews, and check CODEOWNERS coverage using existing path-matching logic from `doctor.py:637`.
- Fallback: When `gh` is missing, unauthenticated, or run offline, record status as `unverified` and emit a warning. When `--require-approvals` is passed (or on Critical CI gate), fail closed.

### 4. Semantic JUnit XML Parsing via Stdlib
- Use Python standard library `xml.etree.ElementTree` (zero external dependencies).
- Inspect `<testsuite>` and `<testcase>` nodes:
  - Base run: Verify test failed with `<failure>` (assertion failure); reject if only `<error>` collection crash occurred.
  - Head run: Verify `tests > 0`, `failures == 0`, and `errors == 0`.
  - AC Mapping: Cross-check `Unit` / `Test` entries from spec evidence tables against `<testcase name="..." classname="...">`.

### 5. Staged Delivery Across Three PRs
- **PR 5a**: Manifest schema, `--emit-json`, `attested` labeling, and CI workflow artifact upload.
- **PR 5b**: `gh api` review verification, non-author check, Critical 2-reviewer + CODEOWNER rules.
- **PR 5c**: `redgreen.py --junit`, collection crash detection, AC-to-test matching, `LIMITATIONS.md` update.

## Risks / Trade-offs

- **[Risk] `gh` CLI absent in minimal/offline environments**  
  → *Mitigation*: Record status as `unverified` with explicit explanation. The gate warns by default, preventing unexpected breaks on local hooks while remaining honest.
- **[Risk] Heterogeneous JUnit XML dialect variations across test runners**  
  → *Mitigation*: Restrict parsing to standard JUnit XML elements (`<testsuite>`, `<testcase>`, `<failure>`, `<error>`), supported across `pytest`, `jest-junit`, and `unittest-xml-reporting`.
- **[Risk] Divergence between PR body text and Git metadata**  
  → *Mitigation*: Evidence manifest records both `head_sha` and `base_sha`, anchoring the audit record to the exact Git commit.

## Migration & Rollout
- Fully additive: existing CLI flags and exit codes remain untouched.
- `--present` continues to work for local overrides, but is accurately labeled `attested` in manifest reports.

