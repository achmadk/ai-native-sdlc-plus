# Metrics beyond velocity

Pick at most five, one per theme. Baseline for four weeks before targeting. Team-level only.
Source tags: [report-stated] = Atlassian "The Agentic Pivot" (2026); [general] = common industry practice, not from the report.

| Theme | Metric | Definition and source | Goodhart warning (how optimizing it distorts behavior) | Counter-metric |
|---|---|---|---|---|
| Confidence | Change confidence | Survey item, 1-5: "How confident are you changing this code without breaking things?" Quarterly, anonymous. | Pressure to look confident inflates answers. Keep it anonymous and never tie it to reviews. | Change failure rate |
| Confidence | Maintainability perception | Survey item, 1-5: "How easy is this code to understand?" Watch it **against** change confidence. | Same as above. | Change confidence |
| Flow | Review latency | Median hours from PR ready to first substantive review, and to merge. | Rubber-stamp reviews hit the number. | Rework rate, and a sampled review-depth check |
| Quality | Rework rate | Share of merged changes needing a follow-up fix or revert within 14 days. | People relabel fixes or bundle them into new work. | Throughput of merged changes |
| Quality | Change failure rate [general] | Share of deploys causing an incident or rollback. | Incidents go undeclared. | Incident reporting rate, MTTR |
| Learning | Time to Nth merged PR | Median days for new engineers to reach their Nth merged PR (the report uses N=10). | Trivial PRs to hit N. | Defect rate on early PRs, plus an explain-back check |
| Allocation | Innovation ratio | Share of effort on new feature work vs maintenance, toil, and operations. | Work is relabeled as "feature". | Defect escape rate |
| Traceability | Trace coverage | Share of merged PRs whose trace section passes the gate and a sampled read. | Boilerplate traces. | Reconstruction pass rate |
| Traceability | Reconstruction pass rate | Share of sampled PRs a fresh reader can explain from the record alone. Slow and expensive; use small samples. | Authors write for the sample. Sample randomly and unannounced. | Trace coverage |

## What the report says about some of these [report-stated]
- Between Q1 and Q2 2026, Atlassian DX data shows code maintainability up 3.8% while change confidence fell 6.1%: developers find code easier to understand yet trust changes less. Track the two together.
- Time to 10th PR fell to a median of 30 days in Q2 2026, a drop of more than half since Q1 2024. A small minority (about 4-5%) say AI slowed juniors down, possibly because they learn to generate code without learning to understand it. Pair this metric with an explain-back check.
- The innovation ratio has been flat for 12 months. Read that carefully: it is consistent with reinvesting AI gains in quality and operations rather than features, and is not by itself a sign of failure.

## Dividend planning
Leaders who were asked how they would spend a doubled engineering capacity put quality and testing first (65% of leaders, 62% of ICs) [report-stated]. Default to that unless the team has a reason. Before widening agent autonomy, write down the dividend: what the extra capacity buys, and which metric above will show it. If no metric moves in a quarter, that is information, not a failure of the people.
