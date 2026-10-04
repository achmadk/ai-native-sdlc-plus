# Incident intent: ___ (title)

Lane: ___
Author: ___
Status: draft
Approved-by:

<!--
Closes the loop: every incident, security finding, test failure or flaky build becomes a new intent.
Write it AFTER mitigation. Classify the lane with scripts/lane.py. Validate with check_spec.py (spec-first).
The fix must go red-to-green: capture the failing case first (verify-and-evals).
-->

## Trigger
<!-- Link the alert, incident, finding or failing build. -->

## Impact
<!-- Who or what was affected, since when, until when. -->

## Mitigation
<!-- What was done to restore service, by whom, and when. -->

## Intent
<!-- One sentence: the outcome of the permanent fix. -->

## Out of scope
<!-- What this fix deliberately does not address. -->

## Acceptance criteria
<!-- - AC1: observable behavior | pass: measurable condition. Include one criterion that the failure cannot recur. -->

## Constraints
<!-- Security, privacy, compatibility, performance budget. Critical incidents: also add the Threat considerations
     and Rollout constraints sections from spec-first/assets/spec-critical-template.md. -->

## Test expectations
<!-- - AC1 -> evals/regressions/ID.md or tests/test_x.py::test_name | fails-before: why it fails on today's code -->

## Plan
<!-- The approach to the permanent fix. -->

## Follow-ups
<!-- Related risks found, with owners and dates. -->
