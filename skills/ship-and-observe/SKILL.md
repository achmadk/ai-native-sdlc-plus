---
name: ship-and-observe
description: "Ship AI-assisted changes safely, make them attributable in production, and handle unplanned loops such as incidents, security findings, test failures, and flaky builds. Use when planning a rollout or rollback, deciding how much release process a change needs, monitoring agents, or responding to an incident. Triggers: rollout plan, rollback, staged rollout, canary, agent visibility, incident, flaky build, break glass."
---

# ship-and-observe — the right of code

Teams are shipping more, so more code reaches production against monitoring practices that are largely unchanged from before AI [report-stated]. Most risk appears after merge, which is why rollout and observation get their own skill.

## Rollout by lane

- **Lite:** standard merge checks. No plan needed.
- **Standard:** a short `## Rollout plan` in the PR: what ships, how you will tell it works, how to revert. The gate does not require it for Standard, but reviewers should ask.
- **Critical:** the gate requires a `## Rollout plan`. Use `assets/rollout-plan-template.md`: stages with an audience and bake time, signals with thresholds and abort criteria, a rollback that says how long it takes and whether it was tried, and a named owner. A missing plan means not ship-ready.

Flag anything irreversible (migrations, deletes, sent messages) explicitly. Prefer expand, then contract, so old and new code can both run during rollout, and confirm a backup exists before a destructive step.

## Make changes attributable

When a symptom appears in production, someone must be able to map it to a change without access to the author's session.
- Record provenance in the PR trace and as a commit trailer such as `Assisted-by: <tool> <model>`, which `git log` can verify later.
- Put the PR number and lane in the deploy annotation or release tag.
- Per-hunk attribution is rarely recoverable. Record it at commit granularity, add paths only where known, and write "unknown" rather than guess.

## Watch the agents too

With agentic workflows running, teams need to see which agents are active, what context they used, where they are blocked, and where a human must step in, and to keep a trace from prompt through review and deploy to production signals [report-stated]. At minimum keep an activity log (who or what, when, scope) for triage, and know which named autonomous flows exist (see `autonomy-policy`).

## Unplanned loops

Incidents, security findings, test failures, and flaky builds each follow a runbook in `references/loop-runbooks.md`. All of them end the same way: a new intent from `assets/incident-intent-template.md`, a lane from `lane.py`, the lane's gates, and a regression case from `verify-and-evals`. A breach writes a new intent. That is the loop closing, not bureaucracy.

**Mitigate first.** During an active incident, restore service before paperwork. The emergency path is a team policy: an admin merge, an entry in the exceptions log from `autonomy-policy`, and full evidence within an agreed window afterward (for example two business days). The gate does not implement a bypass, and admins can bypass branch protection, so every use must be logged and reviewed. Write the intent after mitigation, not before.
