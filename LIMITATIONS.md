# LIMITATIONS.md — read first

## What a green gate does and does not mean

The gate verifies required evidence EXISTS and meets its supported structural rules. Local spec/intent links must identify nonempty regular tracked blobs at the evaluated revision; fenced examples and comments do not supply evidence. Automatic documentation exemptions require complete Git path/type/mode facts. None of this authenticates an approval, validates semantic quality, or proves tests passed. External URLs remain explicitly unverified. A green gate is not "change good". The optional `scripts/trace_lint.py` adds separate heuristics and is not equivalent to the core gate.

## Evidence verification matrix

| Evidence kind | How it is verified | What it proves | What it still does not prove |
|---|---|---|---|
| PR sections (`Intent`, `Trace`, `Review notes`, `Threat note`, `Rollout plan`) | Markdown headings parsed outside fences and comments; placeholders, sub-heading titles and filler lines removed; at least 20 meaningful characters required | A non-placeholder section exists in the PR description | Who wrote it, whether it is true, or whether a human reviewed it |
| `Spec:` and `Intent link:` | Target resolved as a nonempty regular tracked blob at the evaluated commit; URLs are accepted only as explicitly `unverified`; repository traversal, symlinks, Git metadata and empty blobs are rejected | A tracked file exists at that commit and the link stays inside the repository | Document quality, approval, or that the content matches the change |
| Test changes | Git diff shows a changed test path, a reasoned `Tests: none - <reason>` waiver, or a prose-only exemption backed by complete path/type/mode metadata | Test paths changed or a waiver was stated | That the tests cover the change, run, or fail for the right reason |
| `--present` attestations | Manual assertion; the manifest records status `attested` with `verified_how: attested-flag` | Someone asserted the item locally | No independent verification; never equivalent to `verified` |
| Evidence manifest (`--emit-json`) | JSON records `head_sha`, `base_sha`, computed lane, matched rule, and each required item's `status` and `verified_how` (`tracked-blob`, `pr-body-section`, `attested-flag`, `api-checked`) | An audit snapshot anchored to the evaluated commits | The manifest is produced by the same gate; it is not signed, hosted, or tamper-proof |
| `Approved-by:` reviews | Ambient `gh api` reads PR reviews; declared approvers must have `APPROVED` reviews and cannot be the author; Critical requires two distinct non-author reviewers and a reviewer matching an applicable CODEOWNERS owner | A hosted review record matched the declaration at query time | Account compromise, dismissed or stale reviews, team membership for `@org/team` owners, or branch-protection enforcement |
| CODEOWNERS coverage | Last matching pattern in the repository CODEOWNERS file selects owners for changed paths | A direct owner login matches an approving reviewer | That GitHub requires code-owner review, or that the owner still exists |
| Red-to-green exit codes | Base run fails and head run passes, with optional repeats | The command failed before and passed after | That it failed for the stated reason, test quality, or chronological test-first development |
| JUnit report (`--junit`) | Stdlib `xml.etree.ElementTree` parses `<testcase>` records; collection `<error>` crashes are distinguished from assertion `<failure>` states; zero-test runs are rejected; mapped AC test identifiers must appear | The configured tests executed, did not merely crash during collection, and the mapped identifiers ran on head | Runner correctness, skipped tests, coverage, semantic test quality, or that every acceptance criterion has a test |

## What an admin can bypass

An authorized administrator can change required checks, ownership requirements, workflow code, or bypass policies. Custom lane config cannot lower built-in Critical control paths. `--no-verify` bypasses local hooks, not a properly required hosted check. Controls raise the cost of error; they do not make a compromised or authorized administrator incapable of changing the controls.

## Not covered

Specialist secret scanning beyond the included Gitleaks workflow (`.github/workflows/gitleaks.yml`), runtime sandboxing, model safety, and legal or compliance determinations. The privacy pattern scan is narrow and a clean result proves nothing about PII.

## Known gaps (published, not hidden)

- Learning-mode edge eval ties baseline on off-scope prompts.
- Reconstruction full replication (different rater, 6-month gap) pending; dry-run only.
- Lane-config Critical defaults need first-repo calibration (`scripts/lane_backtest.py` replays `lane.py` over your history to help).
- Doctor is offline by default. `--check-branch-protection --require-enforcement` inspects a constrained GitHub profile and fails on missing, unsupported, or unverified prerequisites; arbitrary workflow shapes, invisible bypass settings, and merge queues are not claimed as supported.
- Installation is not activation. `sdlc init`, `sdlc update`, and `sdlc uninstall` preserve user-owned canonical `AGENTS.md` and conflicting local files, and report partial failures honestly; they do not configure global agent settings, override model/permission policies, activate hooks, or change hosted protections. Generating native profile files is configuration evidence, not proof of live agent discovery or behavioral compliance.
- Windows self-tests include native PowerShell installation, actual Git-dispatched hooks, and the full suite. Local Windows/POSIX results are separate from the configured Python 3.8/3.13 Windows jobs and macOS CI; inspect the [compatibility record](docs/COMPATIBILITY.md) before claiming those versions passed. Hosted scanner results still require actual provider runs.
- Platform-specific tests can skip when symlink privilege, POSIX executable permissions, pseudo-terminals, or literal filename support is unavailable. Windows-only invocation, parsing, and junction tests do not execute on POSIX. Raw-path classification, literal pathspec, and Git-index metadata assertions retain portable coverage; a skipped physical fixture is not evidence that its platform branch passed.
- Windows command doubles use the existing Python interpreter rather than newly compiled executables. Fake `gh` discovery and command selection are injected only in tests; responses still come from a real child process. This does not verify a real Windows `gh` installation or its PATH binding, signature trust, hosted authentication, or branch enforcement. The interpreter must be permitted to run; tests do not install tools, add allow-list entries, or relax execution policy.
- ShellCheck is unavailable in the local verification environments for this candidate. The configured CI matrix, real hosted scanner cases, and independent human approvals still need their own evidence. Commit-bound red/green proof cannot be claimed from an uncommitted working tree.
- Red-to-green currently compares process outcomes and changed-test overlays. Collection errors, unrelated failures, or different test sets require human examination; a `PASS` is not proof of chronological test-first development or semantic test quality.

## Closed gaps

- The recorded `lexical overlap` experiment reports 0.97 precision and 0.96 recall (see `evals/results-trigger.md`). It does not measure selection by real agents or generalize beyond that corpus. `[measured here]`

<!-- verify-all:start {"id":"limitations-max-lane","label":"maximum lane load","status_path":"footprint.status","unit":"tokens","value_path":"footprint.max_lane_tokens"} -->
Current measured maximum lane load: `unverified tokens`; status `skipped`; tested revision `9054870abd657ac6f8c49842eacde8999e1a1333`.
<!-- verify-all:end limitations-max-lane -->

## Adoption positions

| Position | Supported today |
|---|---|
| Individual | Yes |
| Pilot team | After installation, calibration, separately authorized protection setup, and supported-profile verification |
| Org-wide | Requires environment-specific controls, verified rollouts, and operational evidence; adopting policy text or readiness scoring alone is insufficient |
| Regulated | Mappings provided in `docs/compliance/` (EU AI Act, CRA, NIST AI RMF, SOC 2), usable as supporting evidence alongside required human review. Not legal advice, certification or a conformity assessment: the gate shows evidence exists, not that a control is met |

## Claims ledger (pointers)

Survey figures: [report-stated]. Eval numbers: [measured here] in evals/. Lane overhead and rollout guidance: [extrapolated] from template sizes, flagged per claim in evals/.
