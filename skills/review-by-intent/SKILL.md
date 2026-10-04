---
name: review-by-intent
description: "Review a change against its intent and risk instead of reading line by line. Use when reviewing AI-generated changes, checking whether code matches the spec, or writing review notes for the PR. Triggers: review change, check intent, intent mismatch, review notes, failure checklist, explain-back, second reviewer."
---

# review-by-intent — judge the delta against its promise

Reading every line does not scale: about 78% of teams still review AI-generated code through the same manual PR process as before [report-stated], and line reading misses intent drift. You review the promise first, then the evidence.

## You recommend; a human decides

You produce review notes and a recommendation. A named human approves or requests changes, and records that they did. Do not approve a PR.

## How to review

1. **Establish the promise.** Read the intent: the PR's `## Intent` (Lite), the spec linked as `Spec:` (Standard), or the intent statement plus spec (Critical). Also read any linked context brief. If there is no intent, say so and stop. Never infer the intent from the diff: that is circular.
2. **Check scope before content.** Map the changed files to the spec. List files the intent does not explain (scope creep). Gate files (`scripts/`, `.github/workflows/`, CODEOWNERS, `hooks/`) are always Critical and belong in their own PR.
3. **Give each criterion a verdict:** met, violated, uncovered (no test or evidence), or unverified (you could not check it; say what is needed). Never write "met" without evidence you actually looked at: a test, an output, a line.
4. **Run the AI failure checklist** in `assets/review-checklist.md`: invented APIs and packages, weakened or fake tests, swallowed errors, scope creep, leaked secrets. Link every finding to a file and line or a test.
5. **Check the evidence exists:** red-to-green output (from `verify-and-evals`), green CI, the trace. Do not re-run what CI ran.
6. **Write the notes** into the PR under `## Review notes` using `assets/review-notes-template.md`. They are required evidence for Standard and Critical.

## Explain-back

Ask the author to say, in their own words and separate from any generated summary: what changed and why, what would break first if a key assumption were wrong, and how a regression would be noticed. Record "pass" or "follow-up needed" in the notes. It is a check on understanding, not an exam. For a junior author use guided questions instead (see `learning-mode`). A small minority (about 4-5%) report AI slowed juniors down, possibly because they learn to generate code without learning to understand it [report-stated].

## Lane mapping and size

- Lite: a short note. One line per criterion, and the top five checklist items.
- Standard: the full verdict table and checklist.
- Critical: the full review, plus a second human reviewer who signs off by name. That person is neither the author nor the agent that wrote the change. The threat note is reviewed too.
- Over roughly 400 changed lines or 15 files, ask for a split unless the change is mechanical. This is a heuristic, not a rule, and review capacity is the bottleneck.

## Independence

An agent reviewing its own output shares its blind spots. Prefer a different session or model for AI-assisted review, keep a human accountable, and record who or what reviewed in the notes. An AI reviewer without organizational context can only check syntax and quality [report-stated], so supply the context brief.
