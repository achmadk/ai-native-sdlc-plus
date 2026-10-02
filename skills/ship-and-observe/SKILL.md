---
name: ship-and-observe
description: "Ship AI-generated changes safely and handle unplanned loops. Use when rolling out, monitoring, or responding to incidents and flaky builds. Triggers: rollout plan, rollback, staged rollout, agent visibility, incident loop, flaky build."
---

# ship-and-observe — right of code

You govern rollout because most risk appears after merge.

## Rollout by lane

- Lite: standard merge checks only.
- Standard: rollout note (what ships, how to tell it works, how to revert).
- Critical: staged rollout plus monitoring plus rollback plan. Missing plan denies ship readiness.

## Visibility

Record which hunks were agent-generated vs human-written with model and tool identifiers, so incident triage works without session access.

## Unplanned loops

Incidents, test failures, security findings, flaky builds: open a new intent capturing the finding, classify its lane, and run it through that lane's gates. A breach writes a new intent — that is the loop closing, not bureaucracy.
