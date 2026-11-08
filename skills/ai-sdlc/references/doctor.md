# doctor reference

`python3 scripts/doctor.py [--root DIR] [--strict] [--json] [--check-branch-protection] [--require-enforcement] [--check-name NAME]`

Verifies the installation and says exactly how sure it is. Each line is `name: status - detail`.

## Statuses
- `verified`: checked here and true.
- `FAIL`: checked here and wrong. The gate will not work or is unsafe.
- `WARN`: it works, but there is a risk or drift to look at. With `--strict` a WARN fails the run.
- `unverified`: a fact cannot be established here. It is never positive evidence; a required unverified fact prevents strict enforcement readiness.
- `info`: context only.

Exit codes: 0 no FAIL (and no WARN with `--strict`), 1 any FAIL, 2 usage error. `--require-enforcement` adds a failing overall result when any required profile fact is false, missing, unsupported, or unverified. It requires explicit `--check-branch-protection`; a generic exit 0 is not an enforcement verdict.

## What it checks
- **Environment and files:** Python >= 3.8; the gate scripts, lane config, workflow, PR template, and hook files exist.
- **Config:** `config-valid` parses the lane config strictly with the `lane.py` next to doctor, so a typo'd section or wrong `version:` is a FAIL. `config-critical`, `config-catch-all`, and `config-non-executable` flag configs that weaken the defaults. `builtin-protection` confirms the gate files are always Critical.
- **Calibration:** `rule-coverage` (files per lane), `rule-dead-critical` (Critical rules that match no tracked file), `rule-critical-share` (a heuristic: over 30% Critical means alert fatigue).
- **Workflow:** no `pull_request_target`; runs on `pull_request` and re-runs on `edited`; full history; runs the scripts from the base-commit checkout; least-privilege token; `persist-credentials: false`; actions pinned to commit SHAs.
- **Hook:** `hook-active` asks git where it will look for `pre-push` and requires an executable file named exactly `pre-push` that is this hook. `hooks/pre-push.sh` alone is never run by git.
- **Repository state:** CODEOWNERS covers the gate files; gate files are committed; the tooling exists on the default branch (as of the last fetch); the clone is not shallow.
- **`script-drift`:** the repo's scripts compared with the copies next to doctor. The repo's own scripts are hashed, never executed.

## Hosted inspection

Unverified by default: local files cannot establish hosted protection. `--check-branch-protection` preserves the narrower legacy check, including custom `--check-name`. For the supported profile use both `--check-branch-protection --require-enforcement`; custom check names are not accepted in that profile.

The strict profile observes exact `evidence` and `gitleaks` identities and the expected GitHub Actions application, applicable protection sources, PR/owner/fresh-review and branch-freshness controls, and bypass visibility. It checks a constrained hosted workflow/tooling/ownership snapshot, not merely regex strings in the current checkout. Unsupported conditions, unavailable source data, mismatched tooling, or uncertain ownership coverage remain unverified. Root anchoring and case-sensitive owner patterns cannot be treated as covering every future case-insensitive Critical path.

Requests target GitHub.com through authenticated `gh`. REST inspection uses GET. The only POST is a constant read-only GraphQL query with variables to inspect merge-queue state; mutations and arbitrary query text are not accepted. Errors or missing data are not proof of no queue. Merge queues are not supported by the PR-only enforcement profile.

Provider mocks test inspector behavior, not a live target's protections. An actual public query can establish the transport contract without proving any user's repository ready. Follow `references/init.md` for separately authorized activation and hosted scanner smoke checks.

## What doctor never does
Change GitHub settings, activate hooks, execute inspected candidate scripts, or use the network without `--check-branch-protection`. It cannot prove semantic code correctness, authenticated spec approval, or runtime agent isolation.
