---
name: verify-and-evals
description: "Prove a change works with failing-first tests, and measure AI behavior with pre-registered evals. Use when verifying a fix or feature, showing red-to-green evidence, writing evals, using an LLM as a judge, or turning an incident into a regression test. Triggers: red to green, test first, failing test, prove it works, eval plan, LLM judge, regression eval, incident to eval."
---

# verify-and-evals — measured, not asserted

A test that never failed proves nothing. More code at higher velocity means more surface area to verify, and leaders say they would spend extra capacity on quality and testing first [report-stated]. So verification here produces evidence, not a claim.

## Verify a change

1. **Write the test first**, from the spec's test expectations. Run it and watch it fail, for the right reason.
2. **Implement**, then run it again until it passes.
3. **Prove it:** `python3 scripts/redgreen.py --base origin/main --cmd "<your test command>" --repeat 3` (the script is in this skill's `scripts/` folder). It checks out the starting commit in a throwaway worktree, overlays your new tests, and requires a failure there, then requires a pass on your head. Your working copy is untouched.
4. **Read the RED output.** It must fail for the stated reason, not a typo or a missing dependency. The tool cannot judge that: you can.
5. **Paste the evidence block** into the PR under `## Trace`, in "Test evidence". Verdicts: `PASS`, `NOT_RED` (the test passes without the change, so it proves nothing), `NOT_GREEN`, `FLAKY`, `NO_TESTS`.

If tests need installed dependencies, use `--setup "<command>"` so each worktree is prepared. `--cmd` and `--setup` run with your environment and network: use a sandbox for code you would not otherwise run.

### When red-first does not apply
Say so in the PR; do not skip silently.
- **Pure refactor:** the same tests pass before and after (green-green). Run the command on both commits and state it.
- **Docs, config, or comments only:** `Tests: none - <reason>`.
- **Cannot be tested:** explain why, give the manual verification steps, and name who ran them.

### What does not count as a test
Assertions that cannot fail; mocking the thing under test; editing existing tests to fit new behavior without a spec change; new `skip` or `xfail`; deleting a failing test; snapshots regenerated blindly. For critical logic, break the code on purpose (flip a condition) and confirm a test fails.

## Evals (for AI behavior, prompts, and skills)

Register the plan **before** running anything, using `assets/eval-plan-template.md`. Then:
- Compare with the skill against a baseline without it, on assertion pass rate, tokens, and time.
- Report counts (k of n), not only percentages. Repeat non-deterministic runs at least three times and report the spread.
- Tune on a development set and report on a held-out set.
- Publish negative results and the design change they led to. Never change cases, thresholds, or the judge after seeing results to flatter them.

## LLM judges

A judge has blind spots: it favors the first answer shown, longer answers, and its own model family. Randomize order, score against a concrete rubric, and use a different model family from the one that produced the output. Calibrate against human labels on at least 20 to 30 samples and report agreement. Report the judge model, the rubric, the sample rate, and the spot-check outcome with every result. A judge is never the only evidence for a Critical change.

## Incidents become evals

Every incident, security finding, flaky build, or test failure becomes a permanent regression case under `evals/regressions/`: id, failure mode, triggering input, expected behavior, how it is detected. Capture the failing case before the fix, so the fix goes red-to-green. Run it in CI so a recurrence is detected automatically, and link the incident from the trace.
