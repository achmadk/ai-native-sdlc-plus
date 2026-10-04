# init reference

Sets up the gate for a repo. Idempotent: `install.sh` never overwrites a file you have changed ("kept (local changes)") and is safe to rerun.

## Steps
1. **Install the tooling:** `sh install.sh /path/to/repo` from the toolkit. It copies `scripts/` (lane classifier, evidence check, doctor, config), the PR template, the CI workflow, and both hook files, then runs doctor.
2. **Calibrate `scripts/lane-config.yaml`.** The shipped rules are guesses. Put your riskiest paths under `critical`, keep `version: 1`, and rerun doctor: it reports Critical rules that match nothing and a Critical share that is too high.
3. **Commit the tooling to the default branch first.** The gate reads its scripts from the base branch, so the first PR that adds it has nothing to read.
4. **Require the check.** Mark the status check named `evidence` (the job name; the PR UI may show "sdlc-gate / evidence") as required in branch protection or a ruleset, pinned to the GitHub Actions app.
5. **Protect the gate.** Add CODEOWNERS entries for `.github/workflows/` and `scripts/` and require code-owner review. With the `pull_request` event the workflow file comes from the PR, so owner review is what protects it.
6. **Activate the hook:** `git config core.hooksPath hooks`. Git only runs a file named exactly `pre-push`, so `hooks/pre-push` forwards to `hooks/pre-push.sh`. Standalone alternative: copy `pre-push.sh` to `.git/hooks/pre-push`.
7. **Verify:** `python3 scripts/doctor.py --root . --check-branch-protection` (needs the `gh` CLI), and fix every FAIL. A WARN is a decision, and each should be either fixed or accepted on purpose.

## Other CI systems
Use `assets/ci-generic.sh`. Provide `SDLC_BASE` (the base commit SHA), `SDLC_HEAD` (the change's SHA), and `SDLC_PR_BODY_FILE` (a file holding the PR or MR description). Run it from a checkout of the change with full history. It takes the scripts and config from the base commit, as the GitHub workflow does. Remember the same rules: require the job, protect the gate files, commit the tooling to the default branch first.

## Brownfield rule
Start at the first new change. Never backfill history, decision logs, or specs for prior work.
