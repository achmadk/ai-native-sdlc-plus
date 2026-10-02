# doctor reference

Verifies installation. Each line reports verified or unverified.

- config: lane config parses and has rules.
- hook-template: local hook template present (warn-only).
- ci-template: CI workflow present.
- required-check: always unverified locally. It becomes a gate only when marked required in branch protection, which needs API access this script does not have (no network by design).

Exit 0 when all verifiable checks pass, 1 otherwise. Unverified required-check never fails the run by itself.
