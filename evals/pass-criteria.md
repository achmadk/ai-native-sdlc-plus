# Pass Criteria — pre-registered 2026-10-02

Committed before any eval run. If a result misses, report it and fix the design; never retune evals to flatter.

## Task evals (per skill: 1 leader, 1 IC, 1 edge case; with and without skill)

- Pass if with-skill assertion pass rate >= baseline + 15 points on at least 2 of 3 prompts, with no prompt regressing more than 10 points.
- Report tokens and wall time deltas for every pair; token overhead must stay under 2x baseline for Lite-lane tasks.
- Negative deltas publish with design correction note.

## Trigger evals (per skill: 8 should-trigger, 8 near-miss should-not-trigger)

- Pass if precision >= 0.85 and recall >= 0.85 per skill.
- Iterate descriptions until target met; record iteration count and what changed.

## Ceremony benchmark (Lite, Standard, Critical vs flat approval chain)

- Pass if Lite ships with 0 pre-approvals and under 5 minutes overhead; Standard needs exactly 1 pre-approval; Critical needs 2-person review plus rollout plan.
- Report approval counts and minutes for both paths.

## Context-gap test

- Agent gets a task whose correct answer depends on an incident record plus a standards doc.
- Pass if with-context-pack answer cites both sources and matches expected resolution, while without-context baseline fails or omits a cited source.

## Reconstruction test

- Fresh agent with no session history reads only the merged trace six simulated months later.
- Pass if it states what changed, why, rejected alternatives, and accepted risk (4 of 4).

## Footprint report

- Total always-loaded tokens (names plus descriptions) reported; per-SKILL.md size limit 250 lines enforced.
- Pass if total stays under 4000 tokens and every SKILL.md is under the line limit.
