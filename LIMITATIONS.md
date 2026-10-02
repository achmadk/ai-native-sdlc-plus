# LIMITATIONS.md — read first

## What a green gate does and does not mean

The gate verifies required evidence EXISTS (spec link, trace block, test changes, review notes). It never judges quality. A green gate means "paperwork present", not "change good".

## What an admin can bypass

Anything. A repo owner can unmark the required check, edit lane-config to downgrade lanes, or merge with `--no-verify` past local hooks. Controls raise the cost of error, not the impossibility of it.

## Not covered

Regulated compliance, specialist secret scanning (pair with Gitleaks), runtime sandboxing, model safety. The privacy pattern scan is narrow and a clean result proves nothing about PII.

## Known gaps (published, not hidden)

- Trigger precision misses pre-registered 0.85 on 4 of 10 skills (keyword harness; see evals/results-trigger.md).
- Learning-mode edge eval ties baseline on off-scope prompts.
- Reconstruction full replication (different rater, 6-month gap) pending; dry-run only.
- Lane-config Critical defaults need first-repo calibration.
- Doctor cannot verify required-check status (no network by design).

## Adoption positions

| Position | Supported today |
|---|---|
| Individual | Yes |
| Pilot team | Yes, with CI check marked required |
| Org-wide | Partial: needs policy tiers + readiness scoring adopted |
| Regulated | No: gaps above disqualify |

## Claims ledger (pointers)

Survey figures: [report-stated]. Eval numbers: [measured here] in evals/. Lane overhead and rollout guidance: [extrapolated] from template sizes, flagged per claim in evals/.
