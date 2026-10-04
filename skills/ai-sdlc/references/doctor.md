# doctor reference

`python3 scripts/doctor.py [--root DIR] [--strict] [--json] [--check-branch-protection] [--check-name NAME]`

Verifies the installation and says exactly how sure it is. Each line is `name: status - detail`.

## Statuses
- `verified`: checked here and true.
- `FAIL`: checked here and wrong. The gate will not work or is unsafe.
- `WARN`: it works, but there is a risk or drift to look at. With `--strict` a WARN fails the run.
- `unverified`: cannot be known from here, and the detail says why. Never a pass and never a failure.
- `info`: context only.

Exit codes: 0 no FAIL (and no WARN with `--strict`), 1 any FAIL, 2 usage error.

## What it checks
- **Environment and files:** Python >= 3.8; the gate scripts, lane config, workflow, PR template, and hook files exist.
- **Config:** `config-valid` parses the lane config strictly with the `lane.py` next to doctor, so a typo'd section or wrong `version:` is a FAIL. `config-critical`, `config-catch-all`, and `config-non-executable` flag configs that weaken the defaults. `builtin-protection` confirms the gate files are always Critical.
- **Calibration:** `rule-coverage` (files per lane), `rule-dead-critical` (Critical rules that match no tracked file), `rule-critical-share` (a heuristic: over 30% Critical means alert fatigue).
- **Workflow:** no `pull_request_target`; runs on `pull_request` and re-runs on `edited`; full history; runs the scripts from the base-commit checkout; least-privilege token; `persist-credentials: false`; actions pinned to commit SHAs.
- **Hook:** `hook-active` asks git where it will look for `pre-push` and requires an executable file named exactly `pre-push` that is this hook. `hooks/pre-push.sh` alone is never run by git.
- **Repository state:** CODEOWNERS covers the gate files; gate files are committed; the tooling exists on the default branch (as of the last fetch); the clone is not shallow.
- **`script-drift`:** the repo's scripts compared with the copies next to doctor. The repo's own scripts are hashed, never executed.

## `required-check`
Unverified by default: nothing local can show that merges are actually blocked. With `--check-branch-protection` doctor makes read-only `gh api` requests and reports whether the check named `evidence` is required, whether it is pinned to the GitHub Actions app, whether code-owner review is required, and whether admins are bound. Positive evidence wins. A source it cannot read (permissions, no `gh`, an odd response) gives `unverified`, not a false pass or fail. The branch-protection code was tested against a fake `gh`, not live GitHub.

## What doctor never does
Write into the repo, execute the repo's scripts, or use the network unless you pass `--check-branch-protection`.
