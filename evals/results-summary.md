# Results summary — 2026-10-02

## Where the suite wins [measured here]

- Lane routing + evidence ladder: deterministic, tested (15/15), mutation 5/5 killed, local-warn vs CI-fail verified by exit codes.
- Task evals: 9 of 10 skills clear the bar on all prompts; slice (router + spec-first) 6/6.
- Footprint: 244 lines total SKILL.md, ~3087 tokens, every file under budget.
- Ceremony: Lite 0 approvals/<5 min; Standard 1 gate; Critical priced deliberately.
- Context-gap and reconstruction dry-runs pass with fixtures committed.

## Where it ties

- Trace-byproduct vs timwukp intent chain: lighter but less provenance.
- verify.py precedent matched on stdlib honesty; broader battery is wider but shallower per eval.

## Where it loses (published, not hidden)

- Trigger precision misses 0.85 on 4 skills (ai-sdlc, spec-first, context-pack, learning-mode); keyword harness lacks negation handling.
- Learning-mode edge ties baseline off-scope.
- No 6-month independent replication yet; single-session dry-run only.
- Incumbents win on maturity (spec-kit scale/integrations) and worked-example history (timwukp portal + 36/80 rubric).

## Links

evals/gap-analysis.md, evals/pass-criteria.md, evals/results-router-spec-first.md, evals/results-full.md, evals/results-trigger.md, evals/footprint.md, evals/ceremony-benchmark.md, evals/context-reconstruction.md, evals/mutation-security.md, evals/slice-learnings.md.
