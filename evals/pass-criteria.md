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

## WS6 selection registration

- Freeze `selection-cases.json`, both catalogs, three repeats, and these criteria in Git before any provider call or description rewrite.
- Require at least 30 should-trigger and 30 semantic near-miss cases spanning all ten product skills, with development and held-out cases reported separately.
- Primary selection thresholds are overall precision >= 0.85 and recall >= 0.95. Always publish per-skill confusion counts, every repeat, and every miss even when the aggregate passes.
- Score only preregistered expected, allowed, and forbidden IDs. Do not use a model judge or edit labels after seeing results.
- Run held-out cases once after descriptions are frozen. A held-out-driven edit invalidates the comparison and requires a new registration rather than relabeling the old run.

## WS6 paired task registration

- Freeze exactly three cases per product skill (leader, IC, edge), their condition-independent assertions, three repeats, condition randomization, and the judge policy before recording outputs.
- Pass if the with-skill assertion rate exceeds baseline by at least 15 points on two of three cases per skill, with no case regressing more than 10 points.
- Provider request, input-token, and monetary caps are hard pre-call limits. Missing token, time, or cost evidence is `unverified`, never zero or `chars/4`.
- Persist negative deltas and incomplete runs. A model judge must use a different model family, a fixed rubric, 24 human-rated calibration samples with kappa >= 0.60, and a 20% human spot-check.
