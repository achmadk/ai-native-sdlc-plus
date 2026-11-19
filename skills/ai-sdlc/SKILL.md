---
name: ai-sdlc
description: "Classify a repository change into Lite, Standard, or Critical and route it to the next workflow with the evidence owed at merge. Use it when starting or onboarding a change, diagnosing SDLC gate evidence failures, or checking repository enforcement readiness."
---

# ai-sdlc — router and lane selector

You route first because ceremony scales with risk. A typo must not pay for a payments change, and a payments change must not get away with a typo's paperwork.

## Hot path (every change)

1. Use the classifier's Git diff input so raw paths, file modes/types, and both rename sides remain available. Do not turn a line-delimited filename list into proof of a documentation-only change. Never guess the lane by feel. If this repository has only skills installed and `scripts/sdlc.py` / `scripts/lane.py` is absent, tell the user to initialize the owned runtime first (`sdlc init --root .` or `python3 <tool-root>/scripts/sdlc.py init --root .`) rather than improvising classification.
2. Run the classifier via the front door: `python3 scripts/sdlc.py lane --base <base> --strict` (or `python3 scripts/lane.py --base <base> --strict`, or `--paths <files>` before anything is committed). It prints one lane and the matched rule. The change takes the **highest** lane of any path, and a path that matches no rule is Standard, so Lite means every path was Lite.
3. If the classifier errors or reports an invalid config (exit code 3 with `--strict`), stop and tell the user. Do not pick a lane yourself: a broken config is exactly when guessing downgrades risk silently.
4. Announce lane + rule, then point to the single next skill:
   - Lite -> spec-first (short intent+plan block). Tests and trace owed. No pre-approval.
   - Standard -> spec-first (combined spec). One human approval before build. Evals owed.
   - Critical -> spec-first split (intent + spec), threat note, two-person review, staged rollout + rollback.
5. State the evidence this lane owes at merge, exactly (this is what `python3 scripts/sdlc.py check evidence` / `scripts/evidence_check.py` enforces):
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

A PR can escalate itself with a `Lane: Critical` line but cannot downgrade. The built-in boundary includes the entire `scripts/` tree, installers/state, attributes, CI definitions/adapters, CODEOWNERS, hooks, and supported skill/agent controls. Custom config cannot lower it. Documentation scripts, executable modes, and indeterminate file kinds do not qualify for Lite documentation treatment; lockfiles default to Standard. Keep config format `version: 1` while calibrating repository rules.

## When the gate fails

Read the `MISSING` lines and tooling errors. Local spec/intent links must be nonempty regular tracked blobs at the evaluated head, not untracked files, metadata, or symlinks. Fenced examples do not provide evidence. CI needs `--base`/`--head` change facts; malformed paths are not silently dropped. Fix the actual gap rather than padding prose or weakening rules. Review notes and test waivers still do not authenticate a person's approval.

## Cold paths (on demand only, detail lives in references/)

- `init` / `status` / `update` / `uninstall`: set up or reconcile config, templates, CI (GitHub workflow, or `assets/ci-generic.sh` for other CI), canonical user-owned `AGENTS.md`, and optional project-local `--agents` profiles with `python3 scripts/sdlc.py init --root .`. See `references/init.md`. Brownfield rule: start at the first new change, never retrofit history.
- `doctor` / `explain`: inspect local health with `python3 scripts/sdlc.py doctor --root .` (or `python3 scripts/doctor.py`) and inspect check details with `python3 scripts/sdlc.py explain <check-id> --root .`; use `--check-branch-protection --require-enforcement` for the supported hosted profile. See `references/doctor.md`. Missing or unverified prerequisites fail strict readiness; installation, optional-hook status, and a generic exit 0 do not prove merge protection.
- Onboarding an existing repo: see `references/onboarding.md`.

## Evidence ladder (honest labels)

Advisory skill -> advisory local hook -> fail-closed CI check. CI uses complete Git change facts, tracked evidence, and isolated base-revision tooling. The workflow definition still needs externally required owner review or a supported trusted workflow. Require the exact evidence and scanner checks with the other readiness controls; installation never activates them. The gate verifies presence and supported structure, not semantic quality, authenticated approvals, or passing tests. Say so when asked.

## Anti-patterns

- Do not reclassify by model whim when the script already answered.
- Do not write evidence the person has not produced (a trace of reasoning that did not happen). Ask what actually happened.
- Do not load init/doctor detail during normal routing; it breaks the footprint budget.
- Do not promise quality from a green gate.
