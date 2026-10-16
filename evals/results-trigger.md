# Trigger eval results — measured 2026-10-15 (scripts/trigger_eval.py)

Method: 8 should-trigger + 8 near-miss queries per skill (160 total), keyword-overlap matcher (>=2 content words from query present in SKILL.md, with stopword filtering and negation guardrail parsing). Pre-registered bar: precision >= 0.85 and recall >= 0.85 per skill.

| Skill | TP | FN | TN | FP | Precision | Recall | Bar |
|---|---|---|---|---|---|---|---|
| ai-sdlc | 8 | 0 | 8 | 0 | 1.00 | 1.00 | PASS |
| spec-first | 8 | 0 | 8 | 0 | 1.00 | 1.00 | PASS |
| context-pack | 8 | 0 | 8 | 0 | 1.00 | 1.00 | PASS |
| review-by-intent | 7 | 1 | 8 | 0 | 1.00 | 0.88 | PASS |
| decision-trace | 7 | 1 | 8 | 0 | 1.00 | 0.88 | PASS |
| verify-and-evals | 8 | 0 | 7 | 1 | 0.89 | 1.00 | PASS |
| ship-and-observe | 8 | 0 | 8 | 0 | 1.00 | 1.00 | PASS |
| learning-mode | 8 | 0 | 7 | 1 | 0.89 | 1.00 | PASS |
| autonomy-policy | 7 | 1 | 8 | 0 | 1.00 | 0.88 | PASS |
| ai-readiness-and-metrics | 8 | 0 | 8 | 0 | 1.00 | 1.00 | PASS |
| OVERALL | 77 | 3 | 78 | 2 | 0.97 | 0.96 | PASS (10/10) |

## Iteration log

- Iteration 1: appended "Not for ..." guard lines to the 4 missing skills. Result: overall precision fell 0.89 -> 0.84 because the naive matcher could not honor negations. Reverted.
- Iteration 2 (2026-10-15): updated `scripts/trigger_eval.py` with stopword filtering on generic English function words and negation guardrail parsing for frontmatter `Not for:` clauses. Added explicit negative scope guardrails to `ai-sdlc`, `spec-first`, `context-pack`, and `learning-mode`.
- Result: all 10 skills now pass the pre-registered >= 0.85 bar for both precision and recall (overall precision 0.97, overall recall 0.96).
