# Eval plan (register BEFORE running)

Date: ___    Owner: ___    Status: draft | registered
Registered where (commit or link): ___

## Question
<!-- One sentence: what decision will this eval inform? -->

## What is compared
- With: ___
- Baseline (without): ___

## Cases
- Development set (used to tune): ___ cases, source ___
- Held-out set (used to report, never tuned on): ___ cases, source ___

## Metrics and thresholds
<!-- Define each metric precisely. The pass threshold is fixed now, not after seeing results.
- assertion pass rate: ___ of ___ required to count as better
- tokens: ___    time: ___ -->

## Repeats
Runs per case: ___ (at least 3 for non-deterministic systems)    Report: counts (k of n) and spread

## Judge (if any)
- Judge model: ___ (different family from the system under test)
- Rubric: ___ (concrete, per criterion)
- Order randomized: yes / no
- Human calibration: ___ samples, agreement ___
- Spot-check sample rate: ___

## If the result is negative
<!-- What you will publish and what design change you will consider. -->

## Results (fill in after the run, without editing the sections above)
- With: ___ of ___    Baseline: ___ of ___    Spread: ___
- Judge agreement with humans: ___
- Verdict against the pre-registered threshold: ___
- Deviations from this plan, and why: ___
