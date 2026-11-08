# init reference

Installs the foundation without silently overwriting local work. The POSIX and PowerShell launchers use one manifest-driven installer. Identical files and ownership state are retained without rewriting; differing unowned or locally modified files stop preflight with a conflict. Missing sources, escaping paths, and later copy failures return nonzero. A partial failure is not a successful installation.

## Steps
1. **Install:** invoke `sh /path/to/toolkit/install.sh /path/to/repo` or PowerShell `install.ps1 -Root <repo>`. Sources are resolved from the distribution, not the working directory. The explicit payload includes core/optional tools, skill resources, root helper entry points, CI templates and runner, both enforcement workflows, hooks, and LF attributes. Verification uses source-side hashes, never an arbitrary destination doctor.
2. **Resolve conflicts:** preserve `.sdlc-install.json` ownership state. A legacy installation with no valid state has no implied overwrite permission. Reconcile differing config/templates/workflows/attributes explicitly, then rerun. No force-update, automatic rollback, or uninstall interface is promised.
3. **Check local health and calibrate:** run `python3 scripts/doctor.py --root .`. Inspect shipped nested security rules against labeled examples and `scripts/lane_backtest.py` results. Keep config format `version: 1`; built-in control paths cannot be downgraded. Distribution alone does not measure classifier accuracy.
4. **Bootstrap only with authorization:** review and commit the tooling to the default branch through the repository's approved process. The first hardening PR still uses the previous base checker, so verify a subsequent fixture against the hardened base as well. Installation itself does not commit or push.
5. **Configure hosted protection separately:** use the activation checklist below. Neither installer nor doctor changes these settings.
6. **Activate a hook only if authorized:** inspect existing hook-manager configuration first. `git config core.hooksPath hooks` is one explicit option, not an installer action. Git needs the extensionless `hooks/pre-push` dispatcher; `pre-push.sh` alone is not that dispatcher. Managed LF rules must survive checkout.
7. **Inspect enforcement:** run `python3 scripts/doctor.py --root . --check-branch-protection --require-enforcement` with authenticated `gh`. Missing, inaccessible, or unsupported prerequisites fail this profile. An offline doctor exit code or inactive optional hook does not establish hosted merge enforcement.

## Separately authorized activation checklist

- Select the real target branch and authorized owner identities. Do not copy this toolkit repository's maintainer identity into another project.
- Require PR-based changes and exact `evidence` and `gitleaks` checks from the expected GitHub Actions application. A similarly named check or any arbitrary nonzero app ID is insufficient.
- Require approving code-owner review across the entire built-in boundary, including future scripts, installers/state, attributes, CI definitions/adapters, hooks, and agent instructions. Root-only patterns do not cover nested basename rules; unsupported pattern shapes remain unverified. A reviewed global owner fallback is one conservative option, not an identity to invent.
- Require fresh review after reviewable pushes through stale-review dismissal or last-push approval, and up-to-date required-check evaluation after base changes.
- Inspect applicable repository/organization rulesets, classic protection, administrative exceptions, and bypass actors. Missing visibility is not an empty bypass list. The supported no-unreviewed-bypass profile does not silently approve intentional exceptions.
- Keep merge queues outside this PR-only profile until a separate merge-group evidence contract is implemented. Read-only inspection may query queue state with a fixed GraphQL POST; it never issues mutations.
- Re-run strict readiness after authorized activation and retain the observed branch/check identities and remaining limitations. Local or hosted inspection is not semantic code review or runtime agent isolation.

## Scanner setup and hosted verification

Gitleaks requires the generated `GITHUB_TOKEN` explicitly in its environment. The workflow grants only read permissions and disables PR comments. Organization accounts additionally need `GITLEAKS_LICENSE`; fork-event secret availability may prevent scanning. Treat missing licensing, token, or API access as setup failure, never a clean scan or justification for privileged PR execution.

Use an explicitly authorized disposable repository for hosted smoke verification; local API mocks do not establish these results:

1. Open a clean fixture PR against a bootstrapped base, with valid lane evidence; confirm the evidence and scanner jobs complete successfully at the expected head SHA.
2. Add a scanner's published non-production secret fixture in a disposable branch; confirm the scan fails for detection rather than authentication/setup. Never use a live credential or paste matched values into the trace.
3. Repeat the applicable fork, private-repository, and organization-license cases. Record unsupported or unexecuted cases explicitly instead of bypassing checks.
4. Edit the PR body and confirm a new evidence run uses the edit. A rerun of an old event reuses its original body; it is not freshness proof.
5. Retain run URLs, revisions, action pins, observed outcomes, and environment limits. Creating fixtures, opening PRs, or changing settings requires separate permission.

## Other CI systems
Use `assets/ci-generic.sh`, included with its adapter templates in the installed payload. Provide `SDLC_BASE` and `SDLC_HEAD` as full commit SHAs plus `SDLC_PR_BODY_FILE`. Run from the candidate checkout with full history. The runner uses isolated Python and base-revision scripts and configuration; CI needs complete Git change facts, not a manually supplied path list. Require the job and protect its definition using provider-specific controls. The GitHub strict-readiness profile does not verify other CI providers.

## Brownfield rule
Start at the first new change. Never backfill history, decision logs, or specs for prior work.
