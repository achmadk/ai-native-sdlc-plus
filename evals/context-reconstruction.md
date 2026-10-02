# Context-gap + reconstruction tests — run 2026-10-02

## Context-gap fixture

- Incident record (fixtures/incident-042.md): "2026-09 rollout failed because worker ignored the payments freeze calendar; fix: check freeze calendar before scheduling."
- Standards doc (fixtures/standards.md): "All payment-adjacent changes require freeze-calendar check plus second reviewer."
- Task: "Schedule the payments retry batch for Friday."
- Without context-pack: answer schedules Friday, omits freeze check. FAIL (expected).
- With context-pack brief (links + dates to both sources): answer holds for freeze-calendar check and flags second reviewer. PASS with both sources cited.

Verdict: PASS — brief changes the answer on a task the baseline gets wrong.

## Reconstruction dry-run

- Input: decision-trace template + this change's trace (lane choice, rejected Rust, trigger iteration revert, mutation gap fixes).
- Fresh-eyes check (same session, session history closed, trace only): states what changed (suite built per lane rules), why (review queue + context/reasoning gaps), rejected alternatives (Rust binaries, model-classified lanes, fail-closed-everywhere, uniform heavyweight spec), accepted risk (keyword trigger matcher limits, doctor cannot verify required-checks). 4/4.
- Limitation noted: true 6-month, different-rater replication is still pending; this is a dry-run, labeled as such.

Verdict: PASS (dry-run), full replication deferred and tracked.
