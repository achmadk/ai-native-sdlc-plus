# LIMITATIONS.md — read first

## What a green gate does and does not mean

The gate verifies required evidence EXISTS (spec link, trace block, test changes, review notes). It never judges quality. A green gate means "paperwork present", not "change good".

## What an admin can bypass

Anything. A repo owner can unmark the required check, edit lane-config to downgrade lanes, or merge with `--no-verify` past local hooks. Controls raise the cost of error, not the impossibility of it.

## Not covered

Specialist secret scanning (pair with Gitleaks; see .github/workflows/), runtime sandboxing, model safety. The privacy pattern scan is narrow and a clean result proves nothing about PII.

## Known gaps (published, not hidden)

- Trigger precision: 10 of 10 skills pass pre-registered >= 0.85 bar (overall 0.97 precision, 0.96 recall; see evals/results-trigger.md).
- Learning-mode edge eval ties baseline on off-scope prompts.
- Reconstruction full replication (different rater, 6-month gap) pending; dry-run only.
- Lane-config Critical defaults need first-repo calibration.
- Doctor cannot verify required-check status (no network by design).

## Adoption positions

| Position | Supported today |
|---|---|
| Individual | Yes |
| Pilot team | Yes, with CI check marked required |
| Org-wide | Yes: with policy tiers + readiness scoring adopted |
| Regulated | Supported when paired with `docs/compliance/` packs (EU AI Act, CRA, NIST AI RMF, SOC 2) + required human review |

## Claims ledger (pointers)

Survey figures: [report-stated]. Eval numbers: [measured here] in evals/. Lane overhead and rollout guidance: [extrapolated] from template sizes, flagged per claim in evals/.
