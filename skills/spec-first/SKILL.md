---
name: spec-first
description: "Turn a vague request into intent, acceptance criteria, and test expectations before any code is written. Use when starting work, writing or reviewing a spec, defining what done means, or when a request is too vague to build. Triggers: write a spec, define done, acceptance criteria, intent statement, test expectations, vague request, what should this do, spec-driven development."
---

# spec-first — intent before code

When implementation gets cheap, ambiguous intent and missing context become the cost, so intent has to be explicit enough that humans and agents work from the same source of truth [report-stated]. Review and verification need something to check against. One approval where judgment is highest beats blanket sign-offs that tax review.

## Where each lane keeps its spec (the PR gate reads these)

| Lane | What you write | What the gate looks for |
|---|---|---|
| Lite | A short `## Intent` section in the PR description (outcome, plan), plus tests and a trace | an Intent section with real content |
| Standard | One spec file from `assets/intent-template.md`, for example `docs/specs/<change>.md`, linked from the PR as `Spec: docs/specs/<change>.md` | the link resolves to a non-empty file |
| Critical | An intent statement (`assets/intent-critical-template.md`), a spec (`assets/spec-critical-template.md`), and a `## Threat note` (`assets/threat-note-template.md`), linked as `Intent link:` and `Spec:` | all three |

## How to specify

1. **Read the context first.** If the right answer depends on history, build a brief with `context-pack` before writing criteria.
2. **State the intent in one sentence:** who benefits and what changes. If the request is too vague to write even that, ask at most three questions. If they cannot be answered, write your assumptions under "Assumptions and open questions" and mark each for a human to confirm. Never invent a requirement, and never pick silently between readings.
3. **Write what you are not doing.** One line under "Out of scope" is what stops an agent from building more than was asked.
4. **Write criteria as `- AC1: observable behavior | pass: measurable condition`.** Rewrite untestable ones: "make login faster" becomes "p95 login latency under 300 ms on fixture warm-cache". See `references/examples.md`.
5. **Map every criterion to a test:** `- AC1 -> tests/test_x.py::test_name | fails-before: why it fails today`. The test must be able to fail before the change; for a new feature that means the behavior does not exist yet. Use `manual:` only for what truly cannot be automated, and say why.
6. **Add constraints:** security, privacy, compatibility, performance budget.
7. **Validate:** `python3 scripts/check_spec.py <spec.md> --lane <lane> --repo-root .` (the script is in this skill's `scripts/` folder). Add `--require-approved` before build and `--require-tests-exist` before merge. For the Critical intent statement add `--kind intent`.
8. **Approval.** Standard and Critical: stop and request exactly one human approval on the spec before build. Record `Status: approved` and `Approved-by: Name (YYYY-MM-DD)`. Lite: no pre-approval.

## Approved specs change by amendment, not silently

If building shows the spec is wrong, stop. Amend the spec, say what changed and why, set `Status: draft`, and get approval again. Review compares the change to the approved spec. A spec rewritten to match the code is evidence of drift, not of correctness.

## Quality bar

- Every criterion maps to a scenario a test could assert. The checker enforces the mapping.
- Specify behavior, not implementation. Name a technology only when it is a real constraint.
- Link instead of copying. If a template field makes you retype something, the template is wrong.
- More than 5 (Lite), 15 (Standard) or 30 (Critical) criteria means the change is too large. Split it.

The checker verifies shape, not truth: it cannot tell whether this is the right spec, and its vague-word check is a tripwire for common phrasings. Never paste secrets or personal data into a spec, since specs are committed.
