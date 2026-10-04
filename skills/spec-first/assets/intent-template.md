# Spec: ___ (title)

Lane: ___
Author: ___
Status: draft
Approved-by:

<!--
Lite: paste the Intent and Plan sections into the PR description. Standard: save this as docs/specs/<change>.md and link it from the PR.
Header: Status is "draft" or "approved". When approved, write "Approved-by: Name (YYYY-MM-DD)", one named human.
Validate: python3 scripts/check_spec.py <this file> --lane <lane> --repo-root .
-->

## Intent
<!-- One sentence: who benefits and what changes. -->

## Out of scope
<!-- At least one thing you are deliberately NOT doing. -->

## Acceptance criteria
<!-- One line each, observable behavior plus a measurable pass condition:
- AC1: behavior a user or test can observe | pass: condition a test can assert -->

## Constraints
<!-- Security, privacy, compatibility, performance budget. -->

## Test expectations
<!-- Every criterion needs at least one test, and the test must fail today:
- AC1 -> tests/test_x.py::test_name | fails-before: why it fails today -->

## Assumptions and open questions
<!-- Anything you guessed. Each one needs a human answer before approval. -->

## Plan
<!-- Lite: 2-4 lines. Standard: the approach, approved together with the spec. -->
