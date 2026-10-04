# onboarding reference (brownfield)

Adopt on an existing repo without disturbing it. The aim of the first two weeks is a working gate and a few honest data points, not full coverage.

## Steps
1. **Run init** (`references/init.md`) on the repo as it is. Do not touch history.
2. **Pick a small first change.** Lite or Standard, with a clear outcome. Avoid a Critical change first: you would be learning the process and the risk at once.
3. **Classify it with `lane.py`** (`python3 scripts/lane.py --base origin/main --strict`). That change is the first governed one.
4. **Write its intent with `spec-first`.** Prior work needs no spec.
5. **Add a `context-pack` brief only if** the change depends on history: a past incident, a prior decision, a standard. Include dates and freshness rules.
6. **Prove the tests** with `redgreen.py` and paste the evidence into the PR trace.
7. **After 5 to 10 governed PRs, calibrate.** Look at which lane each PR got, which evidence was missing most often, and what doctor's `rule-dead-critical` and `rule-critical-share` say. Move rules, not people. If one evidence item keeps failing, fix the template before blaming authors.
8. **Baseline before you target.** Measure for four weeks (see `ai-readiness-and-metrics`) before setting any goals, and keep metrics at team level.
9. **Start agents at Tier 1** (see `autonomy-policy`) and raise a tier only against written entry evidence.

## Done when
- The required check is proven (`doctor --check-branch-protection`), not assumed.
- At least five PRs have gone through the gate with real evidence.
- The lane config has been changed at least once because of what you saw.
- Someone other than the person who installed it can explain what each lane requires.
