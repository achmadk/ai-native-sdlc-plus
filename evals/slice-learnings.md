# Slice learnings — 2026-10-02 (task 2.8)

1. Naive keyword trigger matcher cannot honor "Not for ..." negations (precision 0.89 -> 0.84 on iteration). Correction: keep descriptions pushy-positive; negation handling moves to a model-graded follow-up eval. Recorded in results-trigger.md.
2. Mutation survivors M4/M5 exposed real test gaps (Lite trace, CI exit codes). Correction applied: tests added, now 15/15 green and 5/5 mutants killed. Rule for remaining work: every gate behavior needs both unit and CLI-exit-code tests.
3. Footprint has wide headroom (244 lines total vs 250 per file; ~3087 vs 4000 tokens). Remaining skills keep the thin-SKILL plus references/assets split; no budget change needed.
4. Rust rejected for scripts (recorded in plan discussion): tens-of-ms gains irrelevant against minute-scale budgets; violates no-vendored-binary and tool-agnostic constraints.
