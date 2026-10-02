# Mutation + security report — measured 2026-10-02

## Mutation testing (gate logic)

Harness: 5 hand-seeded mutants, killed iff `python3 -m unittest discover -s scripts/tests` exits non-zero.

| Mutant | Result (final) |
|---|---|
| M1 first-match Critical->Standard reorder | KILLED |
| M2 empty input escalates to Lite | KILLED |
| M3 traversal guard removed | KILLED |
| M4 Lite trace requirement dropped | KILLED (after adding test_lite_requires_trace; SURVIVED first run — gap fixed honestly) |
| M5 CI returns 0 on missing evidence | KILLED (after adding test_ci_exit_codes; SURVIVED first run — gap fixed honestly) |

Final: 5 killed, 0 survivors. Initial run was 3/5; the two survivors exposed real missing tests, which were added.

## Static scan

- Secret-pattern grep (AWS, private-key headers, sk-live, ghp_) over .py/.sh/.md: no matches.
- `python3 -m compileall scripts/`: clean.
- Network calls in scripts: none (stdlib only; verified by import audit: argparse, fnmatch, os, sys, re).
- Finding: trigger_eval.py uses word-overlap heuristic with no negation handling — documented as eval-harness limitation, not shipped as a gate.

## SBOM

See docs/SBOM.md. Zero third-party runtime dependencies.
