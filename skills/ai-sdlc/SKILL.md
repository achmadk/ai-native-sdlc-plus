---
name: ai-sdlc
description: "Route any change to its risk lane and next skill. Use when starting a change, choosing ceremony, or asking what evidence a lane needs. Triggers: classify change, which lane, Lite Standard Critical, route change, init repo, doctor check, onboard repo."
---

# ai-sdlc — router and lane selector

You route first because ceremony scales with risk. A typo must not pay for a payments change.

## Hot path (every change)

1. Collect changed paths or diff stat. Never guess the lane by feel.
2. Run the deterministic classifier: `python3 scripts/lane.py --paths <files> --config scripts/lane-config.yaml`. It prints exactly one lane plus the matched rule.
3. Announce lane + rule, then point to the single next skill:
   - Lite -> spec-first (short intent+plan block), tests + trace required, no pre-approval.
   - Standard -> spec-first (combined spec), one human approval before build, evals required.
   - Critical -> spec-first split (intent + spec), threat note, two-person review, staged rollout + rollback.
4. State the evidence this lane owes at merge: spec link, trace block, test changes, review notes. Evidence existence is checked by `scripts/evidence_check.py`; quality is judged by humans.

Why this order: review capacity is the bottleneck, so one gate sits where judgment is highest instead of blanket sign-offs.

## Cold paths (on demand only, detail lives in references/)

- `init`: set up config, templates, CI. See `references/init.md`. Brownfield rule: start at the first new change, never retrofit history.
- `doctor`: verify install. See `references/doctor.md`. It reports verified vs unverified; it cannot prove a CI check blocks until branch protection marks it required.
- Onboarding an existing repo: see `references/onboarding.md`.

## Evidence ladder (honest labels)

Advisory skill -> local hook warns fail-open -> CI check fails closed on missing evidence. A CI check only blocks merges once marked required in branch protection, and it verifies evidence exists, never that it is good. Say so when asked.

## Anti-patterns

- Do not reclassify by model whim when the script already answered.
- Do not load init/doctor detail during normal routing; it breaks the footprint budget.
- Do not promise quality from a green gate.

