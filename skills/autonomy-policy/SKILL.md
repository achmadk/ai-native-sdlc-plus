---
name: autonomy-policy
description: "Set trust tiers and decide what agents may do unattended, per risk lane. Use when defining or reviewing an agent autonomy policy, deciding what needs human approval, writing escalation rules, planning a phased rollout, or after an agent incident. Triggers: autonomy policy, trust tiers, what can agents do without approval, unattended actions, agent permissions, escalation rules, human in the loop, phased rollout, demote autonomy."
---

# autonomy-policy — govern what agents may do alone

Guarded trust is the dominant posture and full autonomy is nearly absent: survey respondents report roughly 60% guarded trust and about 1% full autonomy, and 80% of leaders still rely more on human judgment than AI for security and compliance [report-stated]. A policy turns "guarded" from a feeling into boundaries a team can check. Survey figures are perception, never a target.

## Workflow

1. Ask at most three questions (which repos and agents, whether lanes are configured, who owns incidents). Then proceed and state your assumptions.
2. Set the tier per lane from the cap table below. The lane caps the tier: an agent's tier for a change can never exceed its lane's cap, whatever the team's general tier.
3. Walk `references/action-catalog.md` and fix, per action, the tier needed, whether it may run unattended, and **what enforces it**. An action with no enforcing control is a norm, and the policy must say "norm", not "rule".
4. Write escalation, demotion triggers, and a review date.
5. Output the policy using `assets/policy-template.md`, plus the rollout plan.

## Tiers

- **0 observe**: read-only. No writes, no effects outside the session.
- **1 assist**: drafts code, tests, and docs in a working copy or branch. A human reviews and applies.
- **2 act**: scoped writes inside lane gates: commits to feature branches, opens PRs, runs tests and builds. Never merges, deploys, or changes permissions, secrets, CI, or the gate itself.
- **3 own**: named, narrow, routine flows only (for example patch-level dependency bumps or known lint fixes), with rollback ready. May merge only when the gate is green. Anything outside the named flow escalates.

## Lane caps (defaults; change them only with a written reason)

| Lane | Max tier | Why |
|---|---|---|
| Lite | 3 for named routine flows, otherwise 2 | Small blast radius, easy to reverse |
| Standard | 2 | A human approves the spec before build and merges after review |
| Critical | 1 | A human applies the change. Agents draft and review, they do not act |

## Escalation

An agent that hits a boundary stops and submits: the action it attempted, the tier rule and lane that stopped it, why it needs the action, what goes wrong if it is mistaken, and how to roll it back. A named human owner answers. No answer within the window means **no**: the action stays blocked. The agent does not look for another route to the same effect; routing around a denial is itself a policy violation.

## Demotion: autonomy drops fast and rises slowly

Drop the affected scope by one tier (to Tier 1 for Critical areas) on any of: an incident traced to an agent action, a gate bypass, a secret exposure, an unreviewed Critical change found after merge, or a failed reconstruction test. Restore only when a review closes the cause. Raise a tier only after the entry evidence for the next phase has held for a full review cycle.

## Rollout

Individual -> pilot -> org-wide. Use the readiness rubric from `ai-readiness-and-metrics` as entry evidence: pilot needs gate honesty >= 2 (required check proven, for example with `python3 scripts/doctor.py --check-branch-protection`) and trace durability >= 1; org-wide needs >= 2 on all four dimensions and a passed reconstruction sample. Regulated use is unsupported today: this suite is not designed or tested against any compliance regime, so involve the compliance owner and never claim a policy satisfies a regulation.

## Guardrails

- Do not write rules the team cannot enforce. Prefer least-privilege tokens, protected branches, and required checks as the mechanism, and say which control backs each row.
- Do not call a policy "safe". It reduces and bounds risk, and says who decides the rest.
- Gate files (`scripts/lane.py`, `scripts/evidence_check.py`, `scripts/lane-config.yaml`, `.github/workflows/`, CODEOWNERS, `hooks/`) are always human-owned, at every tier.
