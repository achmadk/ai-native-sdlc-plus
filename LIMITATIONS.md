# LIMITATIONS.md — read first

## What a green gate does and does not mean

The gate verifies required evidence EXISTS and meets its supported structural rules. Local spec/intent links must identify nonempty regular tracked blobs at the evaluated revision; fenced examples and comments do not supply evidence. Automatic documentation exemptions require complete Git path/type/mode facts. None of this authenticates an approval, validates semantic quality, or proves tests passed. External URLs remain explicitly unverified. A green gate is not "change good". The optional `scripts/trace_lint.py` adds separate heuristics and is not equivalent to the core gate.

## What an admin can bypass

An authorized administrator can change required checks, ownership requirements, workflow code, or bypass policies. Custom lane config cannot lower built-in Critical control paths. `--no-verify` bypasses local hooks, not a properly required hosted check. Controls raise the cost of error; they do not make a compromised or authorized administrator incapable of changing the controls.

## Not covered

Specialist secret scanning beyond the included Gitleaks workflow (`.github/workflows/gitleaks.yml`), runtime sandboxing, model safety, and legal or compliance determinations. The privacy pattern scan is narrow and a clean result proves nothing about PII.

## Known gaps (published, not hidden)

- Learning-mode edge eval ties baseline on off-scope prompts.
- Reconstruction full replication (different rater, 6-month gap) pending; dry-run only.
- Lane-config Critical defaults need first-repo calibration (`scripts/lane_backtest.py` replays `lane.py` over your history to help).
- Doctor is offline by default. `--check-branch-protection --require-enforcement` inspects a constrained GitHub profile and fails on missing, unsupported, or unverified prerequisites; arbitrary workflow shapes, invisible bypass settings, and merge queues are not claimed as supported.
- Installation is not activation. It preserves conflicting user files and reports partial failures; it does not configure hooks, register agents, or change hosted protections.
- Native PowerShell/Windows and hosted scanner results require their actual CI/provider runs. Mocked APIs, skipped tests, and local POSIX checkout tests do not substitute for those results.
- Red-to-green currently compares process outcomes and changed-test overlays. Collection errors, unrelated failures, or different test sets require human examination; a `PASS` is not proof of chronological test-first development or semantic test quality.

## Closed gaps

- The recorded lexical trigger experiment reports 0.97 precision and 0.96 recall (see `evals/results-trigger.md`). It does not measure selection by real agents or generalize beyond that corpus. `[measured here]`

## Adoption positions

| Position | Supported today |
|---|---|
| Individual | Yes |
| Pilot team | After installation, calibration, separately authorized protection setup, and supported-profile verification |
| Org-wide | Requires environment-specific controls, verified rollouts, and operational evidence; adopting policy text or readiness scoring alone is insufficient |
| Regulated | Mappings provided in `docs/compliance/` (EU AI Act, CRA, NIST AI RMF, SOC 2), usable as supporting evidence alongside required human review. Not legal advice, certification or a conformity assessment: the gate shows evidence exists, not that a control is met |

## Claims ledger (pointers)

Survey figures: [report-stated]. Eval numbers: [measured here] in evals/. Lane overhead and rollout guidance: [extrapolated] from template sizes, flagged per claim in evals/.
