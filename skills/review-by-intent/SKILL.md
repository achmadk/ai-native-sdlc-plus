---
name: review-by-intent
description: "Review against intent and risk, not line by line. Use when reviewing AI-generated changes or asking if code matches spec. Triggers: review change, check intent, intent mismatch, approve PR, failure checklist."
---

# review-by-intent — judge the delta against its promise

You review the promise first because line-by-line reading does not scale and misses intent drift.

## How to review

1. Read the approved intent and acceptance criteria before the diff.
2. Verdict each criterion: met, violated, or uncovered. Name violated criteria with evidence; request correction before approval.
3. Apply the AI failure checklist: hallucinated APIs, ignored constraints, untested edge cases, leaked secrets. Link each finding to a line or test.
4. Record verdict plus gaps in the PR. Review notes are required evidence for Standard and Critical.

## Explain-back

Require the author to state why the change works in their own words, separate from generated summaries. It checks understanding and preserves skill. In learning mode expand to guided questions. Why: a small minority risk shipping code they cannot explain.

## Lane mapping

Lite: short note suffices. Standard: full verdict. Critical: verdict plus second reviewer sign-off.
