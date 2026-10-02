---
name: autonomy-policy
description: "Set trust tiers and what agents may do unattended. Use when defining policy, escalation rules, or phased rollout. Triggers: autonomy policy, trust tiers, unattended actions, escalation rules, phased rollout."
---

# autonomy-policy — govern what agents may do alone

You write tiers because guarded trust needs boundaries, not vibes.

## Tiers

- Tier 0 observe: read-only, unattended allowed.
- Tier 1 assist: draft code/tests, human approves before apply.
- Tier 2 act: scoped writes with lane gates; production, migrations, and auth changes always escalate.
- Tier 3 own: narrowly scoped routine flows with rollback ready; everything else escalates.

Attempted out-of-tier action holds for human escalation citing the tier rule and lane. Template in `assets/policy-template.md`.

## Rollout

Individual -> pilot -> org-wide, each phase naming entry evidence before widening autonomy. Regulated use is unsupported today; say so plainly.
