# Current paired task evaluation

- Tested revision: `e692000a16984e824c759dc7bd09a5c150eb990b`
- Registration: `real-evals-tasks-v1` at `569eec7a51e8b8f7ee78c26601560dfd15d3b866`
- Provider/model: `Agent Router` / `agentrouterr/gpt-5.6-sol`
- Cases/repetitions: 30 cases, 3 repeats, baseline and with-skill conditions
- Recorded at: `2026-11-13T05:12:29.740567Z`; cost status: `verified`
- Overall registered verdict: **FAIL**

## Conditions

| Condition | Assertions | Pass rate | Input tokens | Output/reasoning tokens | Time (s) | Cost (USD) | Per-response spread |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 6/180 | 3.333% | 617304 | 77367 | 2348.092 | 0 | 0% to 50% |
| With skill | 23/180 | 12.778% | 699870 | 91080 | 2461.303 | 0 | 0% to 100% |

With-skill minus baseline: **9.444 percentage points**, **+82566 input tokens**, **+13713 output/reasoning tokens**, **+113.212 seconds**, **0 USD**.

## Per-skill registered verdicts

| Skill | Improved cases | Regressed cases | Verdict |
|---|---:|---:|---|
| ai-readiness-and-metrics | 0 | 1 | FAIL |
| ai-sdlc | 1 | 0 | FAIL |
| autonomy-policy | 1 | 0 | FAIL |
| context-pack | 0 | 0 | FAIL |
| decision-trace | 1 | 1 | FAIL |
| learning-mode | 2 | 1 | FAIL |
| review-by-intent | 2 | 0 | PASS |
| ship-and-observe | 2 | 0 | PASS |
| spec-first | 2 | 0 | PASS |
| verify-and-evals | 2 | 0 | PASS |

## Negative deltas

| Case | Skill | Delta |
|---|---|---:|
| task-ai-readiness-and-metrics-ic | ai-readiness-and-metrics | -16.7 pp |
| task-decision-trace-leader | decision-trace | -50.0 pp |
| task-learning-mode-ic | learning-mode | -16.7 pp |

## Judge and human evidence

- Automated judge used: `false`.
- Registered human calibration samples: `24`; spot-check fraction: `0.2`.
- Caveat: Automated judge scores are supporting evidence only and were not used for deterministic assertions.

## Evidence boundary

Deterministic string/JSON assertions are narrow supporting evidence only. They do not establish overall response quality, human approval, live loader behavior, or causation. Historical manual reports remain dated and unchanged.
