# Trigger eval results — measured 2026-10-02 (scripts/trigger_eval.py)

Method: 8 should-trigger + 8 near-miss queries per skill (160 total), keyword-overlap matcher (>=2 content words from query present in SKILL.md). Pre-registered bar: precision >= 0.85 and recall >= 0.85 per skill.

| Skill | TP | FN | TN | FP | Precision | Recall | Bar |
|---|---|---|---|---|---|---|---|
| ai-sdlc | 8 | 0 | 6 | 2 | 0.80 | 1.00 | MISS (precision) |
| spec-first | 8 | 0 | 6 | 2 | 0.80 | 1.00 | MISS (precision) |
| context-pack | 7 | 1 | 5 | 3 | 0.70 | 0.88 | MISS |
| review-by-intent | 7 | 1 | 8 | 0 | 1.00 | 0.88 | PASS |
| decision-trace | 8 | 0 | 8 | 0 | 1.00 | 1.00 | PASS |
| verify-and-evals | 8 | 0 | 7 | 1 | 0.89 | 1.00 | PASS |
| ship-and-observe | 8 | 0 | 8 | 0 | 1.00 | 1.00 | PASS |
| learning-mode | 7 | 1 | 6 | 2 | 0.78 | 0.88 | MISS |
| autonomy-policy | 8 | 0 | 8 | 0 | 1.00 | 1.00 | PASS |
| ai-readiness-and-metrics | 8 | 0 | 8 | 0 | 1.00 | 1.00 | PASS |
| OVERALL | 77 | 3 | 70 | 10 | 0.89 | 0.96 | — |

## Iteration log

- Iteration 1: appended "Not for ..." guard lines to the 4 missing skills. Result: overall precision fell 0.89 -> 0.84 because the naive matcher cannot honor negations (added words created more hits). Reverted.
- Design correction recorded: keyword matchers need negation handling before guardrail wording can score; model-graded trigger eval is the follow-up. Descriptions keep their pushy trigger phrases; the 4 misses stay published, not hidden.
