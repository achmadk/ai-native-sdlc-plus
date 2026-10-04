---
name: ai-sdlc
description: "Route any change to its risk lane and next skill, and say what evidence the lane owes at merge. Use when starting a change, choosing how much process a change needs, writing or fixing a PR description for the sdlc-gate, or when the gate fails. Triggers: classify change, which lane, Lite Standard Critical, route change, what evidence do I need, sdlc-gate failing, PR evidence, init repo, doctor check, onboard repo."
---

# ai-sdlc — router and lane selector

You route first because ceremony scales with risk. A typo must not pay for a payments change, and a payments change must not get away with a typo's paperwork.

## Hot path (every change)

1. Collect the changed paths: `git diff --name-only --no-renames <base>...HEAD`. Use `--no-renames` so a file moved out of a risky directory still counts. Never guess the lane by feel.
2. Run the classifier: `python3 scripts/lane.py --base <base> --strict` (or `--paths <files>` before anything is committed). It prints one lane and the matched rule. The change takes the **highest** lane of any path, and a path that matches no rule is Standard, so Lite means every path was Lite.
3. If the classifier errors or reports an invalid config (exit code 3 with `--strict`), stop and tell the user. Do not pick a lane yourself: a broken config is exactly when guessing downgrades risk silently.
4. Announce lane + rule, then point to the single next skill:
   - Lite -> spec-first (short intent+plan block). Tests and trace owed. No pre-approval.
   - Standard -> spec-first (combined spec). One human approval before build. Evals owed.
   - Critical -> spec-first split (intent + spec), threat note, two-person review, staged rollout + rollback.
5. State the evidence this lane owes at merge, exactly (this is what `scripts/evidence_check.py` enforces):
   - Lite: intent section, test changes, trace section.
   - Standard: spec link, test changes, trace section, review notes.
   - Critical: intent link, spec link, threat note, test changes, trace section, review notes, rollout plan.
6. Point to `.github/pull_request_template.md`. The gate reads the PR description, so headings must match the template and each section must contain real content.

Why this order: review capacity is the bottleneck, so one gate sits where judgment is highest instead of blanket sign-offs.

Related skills, only when the situation calls for them:
- Standard or Critical work whose right answer depends on history (past incidents, prior decisions, standards): build a brief first with `context-pack`.
- Questions about what an agent may do without approval, escalation, or demoting autonomy after an incident: `autonomy-policy`.
- Whether a team is ready for agents, or which metrics to track: `ai-readiness-and-metrics`.
- A newer engineer who must understand AI-generated code before submitting or reviewing it: `learning-mode`.

## Lanes only go up

A PR can escalate itself with a `Lane: Critical` line. It can never downgrade: a declared lane below the computed one is ignored. Changes to the gate itself (`scripts/lane.py`, `scripts/evidence_check.py`, `scripts/lane-config.yaml`, `.github/workflows/`, CODEOWNERS, `hooks/`) are always Critical. Do not bundle them into a feature change; send them as their own PR.

## When the gate fails

Read the `MISSING` lines; each has a one-line fix. Typical causes: a heading that does not match the template, a section that is only template filler, a `Spec:` link that does not resolve to a file in the change, no test path changed and no `Tests: none - <reason>` waiver. Fix the real gap. Do not pad a section with filler to clear the length check: that defeats the purpose and the human reviewer will see it.

## Cold paths (on demand only, detail lives in references/)

- `init`: set up config, templates, CI (GitHub workflow, or `assets/ci-generic.sh` for other CI). See `references/init.md`. Brownfield rule: start at the first new change, never retrofit history.
- `doctor`: verify install with `python3 scripts/doctor.py`. See `references/doctor.md`. Statuses: verified, FAIL (gate broken or unsafe), WARN (risk or drift), unverified (cannot know from here; never a pass). It cannot prove a CI check blocks merges unless you pass `--check-branch-protection` (needs the `gh` CLI).
- Onboarding an existing repo: see `references/onboarding.md`.

## Evidence ladder (honest labels)

Advisory skill -> local pre-push hook (reports the lane and what the PR description owes; never blocks; skipped by `--no-verify`) -> CI check fails closed. In CI the lane is computed from the diff and the evidence is read from the PR description and the repo, not self-declared. The gate scripts and lane config are read from the base branch so a PR cannot weaken the gate judging it. A CI check only blocks merges once marked required in branch protection. It verifies that evidence exists and is structurally real, never that it is good. Say so when asked.

## Anti-patterns

- Do not reclassify by model whim when the script already answered.
- Do not write evidence the person has not produced (a trace of reasoning that did not happen). Ask what actually happened.
- Do not load init/doctor detail during normal routing; it breaks the footprint budget.
- Do not promise quality from a green gate.
