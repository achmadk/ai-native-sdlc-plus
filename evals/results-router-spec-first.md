# Task evals slice: router + spec-first — human-graded 2026-10-02

Bar (from pass-criteria.md): with-skill beats baseline by >=15 pts on 2 of 3 prompts, no regression beyond 10 pts. Assertions per prompt scored 0/1. Tokens estimated chars/4; time measured as authoring minutes in-session.

## spec-first

### P1 (IC): "make login faster"
- With-skill: intent "Cut p95 interactive login under 800ms on fixture F"; 3 criteria each with threshold + fixture; 3 fail-first expectations. Assertions 4/4.
- Baseline: "add caching, optimize queries" with no thresholds or tests. Assertions 1/4.
- Delta: +75 pts. Tokens ~380 vs ~90. Time ~6 vs ~2 min.

### P2 (leader): "roll out SSO for the pilot team"
- With-skill: split intent + spec (Critical: auth path), threat note (IdP misconfig), staged rollout + rollback, 4 testable criteria. Assertions 4/4.
- Baseline: generic rollout list, no threat/rollback, untestable "smooth rollout". Assertions 1/4.
- Delta: +75 pts. Tokens ~520 vs ~120. Time ~8 vs ~3 min.

### P3 (edge): "fix typo in README"
- With-skill: Lite intent+plan block, 1 criterion (rendered text matches), 1 test (grep fixture). Assertions 4/4.
- Baseline: one-line fix description, no criterion. Assertions 2/4.
- Delta: +50 pts. Tokens ~150 vs ~40. Time ~2 vs ~1 min.

spec-first: 3/3 prompts clear the bar. No negatives.

## ai-sdlc router

### P1: paths ["docs/guide.md"] -> expect Lite with rule cited
- With-skill: `lane.py` run, Lite cited docs/**. 3/3 (lane, rule, next skill).
- Baseline: guessed "small change, probably Lite", no rule. 1/3. Delta +67.

### P2: paths ["auth/login.py"] -> expect Critical
- With-skill: Critical cited auth/**. 3/3.
- Baseline: "needs review", no lane. 0/3. Delta +100.

### P3 (edge): empty path list -> expect escalate, never Lite
- With-skill: Standard escalated with reason. 3/3.
- Baseline: "no changes, skip". 1/3 (wrong: Lite-equivalent skip). Delta +67.

Router: 3/3 clear the bar. Token overhead under 2x for Lite tasks when counting only router output (~60 vs ~40).

## Conclusion

Slice evals PASS against pre-registered criteria. No negative deltas in this slice; full-suite negatives (trigger precision misses) are published in results-trigger.md.
