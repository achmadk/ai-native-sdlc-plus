---
name: ai-readiness-and-metrics
description: "Score an engineering org's AI readiness from observable evidence and pick metrics beyond velocity. Use when someone asks whether a team is ready for agents, wants a maturity or readiness score, an adoption backlog, which metrics to track for AI-assisted development, or how to reinvest AI time savings. Triggers: readiness score, maturity assessment, system of record gap, metrics beyond velocity, measure AI impact, Goodhart, reinvest dividend."
---

# ai-readiness-and-metrics — measure what you can point to

Usage is not readiness. Survey respondents report that 94% of leaders use AI and 36% run agentic workflows, but only 6% have AI formally and extensively integrated [report-stated]. So the useful question is not "are you using AI" but "can you provide context, trace decisions, trust the gates, and say what agents may do alone". Survey percentages are perception: use them for framing, never as benchmarks to score a team against.

## Workflow

1. Confirm scope (one team, one repo, or an org) and what evidence can be shown: repo, CI config, a few recent PRs, policy docs. Ask at most one question, then proceed with what you have.
2. Score the four dimensions 0-3 using `references/rubric.md`. Score only what you can point to and cite the artifact. If there is no evidence, write "not scored". Unknown is not zero and is never guessed.
3. Turn gaps into an adoption backlog: at most five items, ordered by risk reduced per effort, each with a concrete next step and a re-score date (default 8 weeks).
4. Choose at most five metrics from `references/metrics.md`, one per theme. Baseline for four weeks before setting any target. Pair every speed metric with a quality counter-metric.
5. Name the dividend: where saved capacity goes (quality and testing first unless the team has a reason) and which metric will show it.

## Output format

```
Readiness scorecard: <scope>, <date>
| Dimension | Score 0-3 | Evidence (artifact you can point to) | Gap |
Adoption backlog: 1..5 (next step, expected effect, re-score date)
Metric plan: metric | data source | baseline start | counter-metric | Goodhart warning
Dividend: where it goes | metric | review date
Not scored / unknown: <list, with what evidence would settle each>
```

## Guardrails

- Team-level only. Never per-person metrics (review latency or rework per developer): they corrode trust and invite gaming.
- No single composite number and no ranking of teams. The scorecard exists to decide what to fix next.
- Do not claim AI caused an outcome. Report the trend, name confounders (team change, seasonality, tooling), and say what would test causation.
- Quote the report accurately: leaders who say they need a governed system of record are reported at 88% in the overview and 84% in the report's own SDLC table, against 19% who have one. Cite "84-88%". The 65% quality-and-testing figure is leaders (62% of ICs).

Detail: `references/rubric.md` (scoring levels) and `references/metrics.md` (definitions, Goodhart warnings, counter-metrics).
