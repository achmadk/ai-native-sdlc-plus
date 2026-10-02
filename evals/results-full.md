# Full task evals (remaining skills) — human-graded 2026-10-02

Same bar as slice: +15 pts on 2 of 3 prompts, no regression beyond 10. Three prompts per skill (leader, IC, edge); 4 assertions each. With-skill path followed the SKILL.md; baseline answered without reading skills.

| Skill | Leader | IC | Edge | Verdict |
|---|---|---|---|---|
| context-pack | 4/4 vs 1/4 (+75) | 4/4 vs 2/4 (+50) | 3/4 vs 2/4 (+25) | PASS |
| review-by-intent | 4/4 vs 1/4 (+75) | 4/4 vs 2/4 (+50) | 4/4 vs 1/4 (+75) | PASS |
| decision-trace | 4/4 vs 1/4 (+75) | 3/4 vs 1/4 (+50) | 4/4 vs 2/4 (+50) | PASS |
| verify-and-evals | 4/4 vs 2/4 (+50) | 4/4 vs 1/4 (+75) | 3/4 vs 2/4 (+25) | PASS |
| ship-and-observe | 4/4 vs 1/4 (+75) | 4/4 vs 2/4 (+50) | 4/4 vs 2/4 (+50) | PASS |
| learning-mode | 3/4 vs 2/4 (+25) | 4/4 vs 2/4 (+50) | 3/4 vs 3/4 (+0) | MIXED (edge ties; no regression; noted, not hidden) |
| autonomy-policy | 4/4 vs 1/4 (+75) | 4/4 vs 2/4 (+50) | 4/4 vs 1/4 (+75) | PASS |
| ai-readiness-and-metrics | 4/4 vs 1/4 (+75) | 3/4 vs 1/4 (+50) | 4/4 vs 2/4 (+50) | PASS |

Notes: learning-mode edge ("quiz night trivia" style off-scope) ties because the skill correctly scopes to change understanding while baseline entertains — scored as tie with design note, not a failure of the skill's purpose. Token overhead highest on Critical templates (~4x baseline output) and justified by threat/rollout content. No eval retuned after scoring.
