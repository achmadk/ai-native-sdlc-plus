---
name: spec-first
description: "Turn a vague request into intent, acceptance criteria, and test expectations before code. Use when starting work, writing a spec, or asking what done means. Triggers: write intent, acceptance criteria, define done, test expectations, vague request to spec."
---

# spec-first — intent before code

You write intent first because review and verification need something to check against.

## Lane shape

- Lite and Standard: one file with intent, acceptance criteria, constraints, test expectations.
- Critical: split intent statement plus detailed spec with threat considerations and rollout constraints. See `assets/` templates.

## How to specify

1. Restate the requester's outcome in one sentence (intent).
2. Write each acceptance criterion as observable behavior with a pass condition. Reject untestable ones with a rewrite, e.g. "make login faster" becomes "p95 login under X on fixture Y".
3. Add constraints (security, privacy, compatibility) and at least one test expectation per criterion that fails before the fix and passes after.
4. For Standard: stop and request exactly one human approval on the spec before build. For Lite: no pre-approval; intent+plan block in the PR suffices with tests + trace at merge.

Why: one approval where judgment is highest beats blanket sign-offs that tax review.

## Quality bar

Every criterion maps to a scenario a test could assert. If a template field makes you copy text you already wrote, the template is wrong — link instead of duplicating. Examples in `references/examples.md`.

