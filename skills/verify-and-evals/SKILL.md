---
name: verify-and-evals
description: "Prove changes with failing-first tests and durable evals. Use when verifying a fix, writing evals, or judging with an LLM. Triggers: red to green, test first, eval criteria, LLM judge, incident to eval."
---

# verify-and-evals — measured, not asserted

You test first because a test that never failed proves nothing.

## Verification

Every behavior change needs a test observed to fail before the fix and pass after. No red-to-green, no complete. Paste the failing then passing output into the PR.

## Evals

Define criteria before running. With/skill vs baseline on assertion pass rate, tokens, time — publish negatives with design fixes, never retune to flatter. Pre-register pass criteria first.

## LLM judges

Document the judge's blind spots and spot-check a sample by hand. Report judge limits, sample rate, and spot-check outcome with every result.

## Incidents to evals

Each incident, security finding, flaky build, or test failure becomes a permanent regression eval capturing the failure mode. Recurrence must be detected automatically next time.
