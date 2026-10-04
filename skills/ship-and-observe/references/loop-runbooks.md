# Loop runbooks

Each runbook is a starting point: first move, default lane, what to capture, and how the loop closes. "Default lane" is only a default; run `lane.py` on the actual fix.

## Production incident
1. **Mitigate first:** roll back, flag off, or fail over. Do not wait for process.
2. Preserve evidence: logs, timeline, the change that shipped (use the deploy annotation to find the PR and its trace).
3. Fix lane: the lane of the paths the fix touches. A fix to auth, data, or infrastructure is Critical.
4. Close the loop: incident intent, regression case captured before the fix, blameless review, link both from the trace.
5. If the cause was an agent action, apply the demotion triggers in `autonomy-policy`.

## Security finding
1. Triage severity and exposure. If a secret leaked, rotate it now. Removing it from the text does not undo exposure.
2. Default lane: Critical. A routine patch-level dependency fix may be a named Tier 3 flow if your policy defines one.
3. Close the loop: threat note updated, regression test or scanner rule, and a check whether the same pattern exists elsewhere.

## Test failure on the default branch
1. Find the change that introduced it (bisect, or the last green commit). Revert it if the fix is not obvious: a red default branch blocks everyone.
2. Default lane: that of the reverted or fixed paths.
3. Close the loop: if the failure revealed a missing test, add one red-first.

## Flaky build or test
1. Do not retry until it goes green. That hides the signal. Quarantine the test with an owner and an expiry date, and track it.
2. Default lane: Lite or Standard, by the paths touched.
3. Find the cause: shared state, time, ordering, network, resource limits. Prove the fix with `redgreen.py --repeat 5` where it can fail intermittently.
4. Close the loop: remove the quarantine, and add the cause class to the review checklist if it recurs.

## Agent misbehavior
1. Stop the flow and revoke or narrow its access.
2. Record what it did, with what context, from the activity log.
3. Treat it as an incident: demotion per `autonomy-policy`, and a regression case for the failure mode.
