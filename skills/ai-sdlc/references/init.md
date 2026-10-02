# init reference

Sets up config, templates, and CI for a repo. Idempotent; safe to rerun.

1. Copy `scripts/lane-config.yaml` to the repo (or keep the default and pin the version).
2. Install the CI workflow from `.github/workflows/sdlc-gate.yml` (GitHub) or `assets/ci-generic.sh` (other CI).
3. Optionally install the local hook from `hooks/pre-push.sh` (warn-only, fail-open).
4. Run `python3 scripts/doctor.py --root .` and address verified failures.

Brownfield rule: start at the first new change. Never backfill history, decision logs, or specs for prior work.
