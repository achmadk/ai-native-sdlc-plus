## 1. Approval and baseline

- [x] 1.1 Obtain a new explicit request to apply this change and approval of its Critical-lane scope. Record that commits, pushes, PR creation, hosted fixture creation, hook activation, and GitHub-setting changes require separate authorization.
- [x] 1.2 Run `python3 scripts/lane.py --paths <actual implementation paths>` before editing implementation files; record the baseline revision, Critical classification, and the threat/rollout constraints in `design.md`.
- [x] 1.3 Run the existing relevant test suite and record its baseline results. For each subsequent test-first task, retain the specific expected assertion failure before implementing its corresponding fix; collection errors or unrelated failures do not satisfy this prerequisite.

## 2. Risk classification and Git change facts

- [x] 2.1 Add failing tests in `tests/test_lane.py` against the actual shipped configuration for nested auth/payments/security paths, documentation scripts, dependency lockfiles, and the complete built-in execution boundary under a permissive custom config.
- [x] 2.2 Add failing Git-fixture tests for executable-bit changes, symlinks/type changes, malformed filenames, unavailable metadata, and moves out of Critical paths. Preserve coverage for NUL-delimited input and both rename sides.
- [x] 2.3 Extend the shared Git input in `scripts/lane.py` to retain raw paths, normalized matching paths, status, and old/new modes; retain existing path-list entry points and report unavailable metadata without inventing it.
- [x] 2.4 Implement the built-in boundary floors and update `scripts/lane-config.yaml` defaults as specified in `specs/lane-router/spec.md`. Keep config format version 1, prevent executable/indeterminate documentation from becoming Lite, and pass the new and existing classifier tests.

## 3. Structural evidence hardening

- [x] 3.1 Add failing cases in `tests/test_evidence_check.py` for longer backtick/tilde fences, shorter or mismatched closers, forbidden trailing text, unterminated fences, and enclosed headings, links, lane declarations, and waivers.
- [x] 3.2 Update the fence scanner and evidence consumers so only legally closed fences expose later content; pass the fence regressions and existing valid-template tests.
- [x] 3.3 Add failing tests for mixed documentation/control-character filenames, executable-documentation exemptions, missing Git metadata, `.git/config`, untracked references, symlinks, and tracked files absent from the explicitly evaluated revision.
- [x] 3.4 Carry the complete change facts into evidence detection, turn unprocessable CI inputs into tooling errors, and resolve local references as literal nonempty regular Git blobs at the evaluated revision. Preserve local warnings, explicitly unverified URL handling, and presence-only review/waiver semantics.
- [x] 3.5 Run `tests/test_evidence_check.py` and `tests/test_templates.py`; confirm valid Lite/Standard/Critical examples still behave as specified and rejected input diagnostics do not reveal file contents or enable workflow-command injection.

## 4. Trusted CI and secret scanning

- [x] 4.1 Add failing integration tests for adjacent standard-library shadow modules and ambient `PYTHONPATH`/user-site injection in both the GitHub-style gate invocation and `skills/ai-sdlc/assets/ci-generic.sh`. Assert that candidate checker/config changes cannot replace trusted base tooling.
- [x] 4.2 Implement isolated Python gate execution and exact-path loading of the trusted lane module without restoring the whole scripts directory to import precedence. Pass the import-isolation and base-policy regression tests without executing candidate code.
- [x] 4.3 Add failing workflow contract tests for the missing scanner token, PR read permissions, optional comments, mutable action references, persisted checkout credentials, skipped required steps, and ignored failures. Verify expected settings against the exact pinned action source.
- [x] 4.4 Repair `.github/workflows/gitleaks.yml` and pin the evidence workflow's actions to reviewed full SHAs. Retain read-only events/permissions, disable comments, preserve PR/body-edit triggers and timeout, and propagate scanner/setup failures without a privileged-event fallback.
- [x] 4.5 Pass the workflow and generic-runner tests. Record the scanner prerequisites and a hosted clean/seeded, fork, and private-repository verification procedure; do not label mocked or source-inspection results as successful hosted scans.

## 5. Complete and non-destructive installation

- [x] 5.1 Add failing installer invocation tests in a focused installer test module for clean targets, unrelated working directories, spaces in paths, identical reruns, legacy installs without state, and existing custom policy/workflow/template/hook files.
- [x] 5.2 Add failing tests for missing sources or interpreter, malformed install state, symlink/junction escapes, post-preflight destination edits, partial I/O failures, and execution of stale destination doctor code. Assert no payload writes on preflight conflicts and no successful completion record after partial failure.
- [x] 5.3 Implement `scripts/install.py` and `scripts/install-manifest.json` as the shared standard-library install plan described in `design.md`. Include explicit payload files, containment checks, managed content/mode hashes, compare-before-replace, per-file atomic writes, trusted source-side verification, and completed-state publication last.
- [ ] 5.4 Convert `install.sh` and `install.ps1` to source-relative launchers that validate an available supported Python interpreter and propagate failures. Preserve current target arguments and do not activate hooks, register agents, download dependencies, or mutate hosted settings.
- [x] 5.5 Add failing source/installed-layout tests, then provide the root `check_spec.py`, `check_brief.py`, and `redgreen.py` entry points delegating to their existing skill-local implementations. Verify argument/output/exit-code parity without changing the helpers' semantic contracts.
- [x] 5.6 Complete and verify the manifest payload, including referenced skill resources, generic CI runner, CI adapter templates, both foundation workflows, and hook implementations. Exclude local sessions/caches, self-test CI, and repository-specific owner identities; exercise documented commands after the original source checkout is unavailable.
- [x] 5.7 Run the installer suite against clean, owned-upgrade, locally modified, interrupted, and legacy targets. Confirm identical reruns preserve existing bytes and modification times, including unchanged install state, and that every failure returns an actionable nonzero result.

## 6. Read-only merge-protection readiness

- [x] 6.1 Add failing `tests/test_doctor.py` cases for exact check/app identities, absent evidence or scanner requirements, unenforced owner review, stale-review controls, branch freshness, unavailable bypass information, merge queues, skipped/ignored workflow steps, and inaccessible provider settings.
- [x] 6.2 Implement the supported profile and `--check-branch-protection --require-enforcement` behavior described in `specs/governance/spec.md`. Resolve expected application identity authoritatively and distinguish observed settings, recognized workflow shape, and unverified controls.
- [x] 6.3 Reject strict readiness for false, missing, unsupported, or unverified prerequisites. Preserve default offline/no-network behavior and existing non-strict CLI usage; reject the strict-enforcement option without explicit remote opt-in.
- [x] 6.4 Pass both negative and complete-profile fixtures. Use GET for REST inspection and allow only the fixed read-only GraphQL POST query needed for merge-queue state; never issue mutations or change GitHub/hook settings, and never treat optional local-hook inactivity or a generic zero exit code as a hosted merge-enforcement verdict.

## 7. Platform integration and affected documentation

- [ ] 7.1 Add failing tests for the actual Git-dispatched Windows hook path with `python` available and `python3` unavailable; implement the smallest interpreter/dispatch adjustment and managed `.gitattributes` LF rules with manifest, Critical-classification, and checkout-roundtrip coverage, while keeping the hook advisory and preserving existing hook-manager configuration.
- [x] 7.2 Add Windows installer and hook-dispatch coverage to `.github/workflows/ci.yml`, retaining existing Linux/macOS coverage and the supported Python floor. Assert installed-target behavior rather than only template strings.
- [x] 7.3 Update affected README, init/doctor guidance, limitations, compatibility notes, and CI adapter guidance for the payload, canonical helper paths, installer conflicts, config schema compatibility, scanner prerequisites, and supported readiness profile.
- [x] 7.4 Publish the separately authorized activation checklist for required checks, expected app identity, owner coverage, review freshness, branch freshness, and bypass review. Document unsupported merge queues, stale-event reruns, and the remaining presence-only limits without changing any live setting.

## 8. Verification and review handoff

- [ ] 8.1 Run `python3 -m unittest discover -s tests -v`, the relevant platform integration jobs, `python3 tests/mutate.py`, and `shellcheck install.sh hooks/pre-push hooks/pre-push.sh`. Fix failures and record unavailable platform/tool coverage rather than claiming it passed.
- [x] 8.2 Run `python3 scripts/lane_backtest.py --limit 50` and review the changed classifications against the labeled security/prose fixtures. Record false escalations and intentional tightening; do not use lane distribution alone as evidence of classifier accuracy.
- [ ] 8.3 Produce and inspect red-to-green evidence using the existing skill-local helper or the new root entry point against an explicitly authorized committed candidate/CI revision. Keep commit-bound proof pending if only an uncommitted candidate exists; do not commit or invent revision evidence to complete this task.
- [x] 8.4 Prepare the Critical review package with intent/spec links, threat note, test evidence, trace, known limitations, and the staged rollout/rollback plan. Record two independent human reviews only when actually received; leave external approval or hosted-smoke gaps explicit.
- [ ] 8.5 Run `openspec validate harden-sdlc-foundation --strict --no-interactive` and the applicable local evidence check using actual collected evidence. Confirm the final diff remains within the approved change and stop before unauthorized commits, pushes, hosted pilots, or protection activation.
