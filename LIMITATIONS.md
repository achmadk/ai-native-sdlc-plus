# LIMITATIONS.md — read first

## What a green gate does and does not mean

The gate verifies required evidence EXISTS (spec link, trace block, test changes, review notes). It never judges quality. A green gate means "paperwork present", not "change good". The optional `scripts/trace_lint.py` adds heuristic checks for unedited templates, empty fields, broken links and missing test files, but it does not judge quality either.

## What an admin can bypass

Anything. A repo owner can unmark the required check, edit lane-config to downgrade lanes, or merge with `--no-verify` past local hooks. Controls raise the cost of error, not the impossibility of it.

## Not covered

Specialist secret scanning beyond the included Gitleaks workflow (`.github/workflows/gitleaks.yml`), runtime sandboxing, model safety, and legal or compliance determinations. The privacy pattern scan is narrow and a clean result proves nothing about PII.

## Known gaps (published, not hidden)

- Learning-mode edge eval ties baseline on off-scope prompts.
- Reconstruction full replication (different rater, 6-month gap) pending; dry-run only.
- Lane-config Critical defaults need first-repo calibration (`scripts/lane_backtest.py` replays `lane.py` over your history to help).
- `doctor.py` cannot verify required-check status (no network by design); the opt-in `scripts/doctor_online.py` checks it through the `gh` CLI.

## Closed gaps

- Trigger precision: 10 of 10 skills pass the pre-registered >= 0.85 bar (overall 0.97 precision, 0.96 recall; see evals/results-trigger.md). `[measured here]`

## Adoption positions

| Position | Supported today |
|---|---|
| Individual | Yes |
| Pilot team | Yes, with CI check marked required |
| Org-wide | Yes: with policy tiers + readiness scoring adopted |
| Regulated | Mappings provided in `docs/compliance/` (EU AI Act, CRA, NIST AI RMF, SOC 2), usable as supporting evidence alongside required human review. Not legal advice, certification or a conformity assessment: the gate shows evidence exists, not that a control is met |

## Claims ledger (pointers)

Survey figures: [report-stated]. Eval numbers: [measured here] in evals/. Lane overhead and rollout guidance: [extrapolated] from template sizes, flagged per claim in evals/.
