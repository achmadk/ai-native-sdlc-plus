## Context

This is a proposed **Critical-lane** implementation, not approval to implement or change hosted settings. The formal intent is to make the existing foundation install without destroying local work, reject the demonstrated structural bypasses, and describe exactly which merge protections have been observed. Two independent human reviews remain required before a Critical implementation is merged.

The 2026-11-05 read-only audit of revision `8377942` established the following baseline. These observations are not claims that the proposed fixes already exist:

| Area | Observed behavior | Relevant source |
| --- | --- | --- |
| Installation | Both entry points overwrite files, suppress failures, resolve sources from the caller's directory, and execute the destination doctor | `install.sh`, `install.ps1` |
| Payload | Root helper paths used by guidance do not exist; installer omits the skill-local helpers and generic CI runner | `README.md`, `skills/*/scripts/`, `skills/ai-sdlc/assets/ci-generic.sh` |
| Classification | `scripts/json.py`, `src/auth/login.py`, and `src/payments/charge.py` classify Standard; `docs/deploy.sh` classifies Lite | `scripts/lane.py`, `scripts/lane-config.yaml` |
| Evidence | Shorter fence markers expose enclosed evidence; a malformed source path is dropped before automatic exemption; `.git/config` passes the local-file check | `scripts/evidence_check.py` |
| CI | Gitleaks lacks its required token environment; the gate still uses mutable checkout tags | `.github/workflows/gitleaks.yml`, `.github/workflows/sdlc-gate.yml` |
| Enforcement | The online doctor reported that `evidence` was not required on `main`; regex-based local checks and loose app/context matching can overstate other properties | `scripts/doctor.py`, audit command output |

The existing design has protections worth preserving: base-SHA tooling and policy, explicit head SHA, NUL-delimited rename-aware risk input, highest-risk-wins classification, a standard-library runtime, advisory local hooks, and an honest presence-only evidence contract. The root lane-router specification already owns classification and evidence; governance owns adoption controls. New installation and CI-security capabilities make the missing contracts explicit without changing unrelated review, learning, or shipping requirements.

Planning uses the confirmed existing local OpenSpec root and the user's approved legacy CLI workflow. OpenSpec 1.4.1 lacks `context`, but its scaffold/status/instructions commands resolve this change to the repository. No tool upgrade, schema modification, or main-spec synchronization is part of this proposal.

## Goals / Non-Goals

**Goals:**

- Install the documented foundation from any working directory without overwriting local modifications or executing untrusted destination tooling.
- Make the installed payload independent of the source checkout and give documented helpers the same entry points in source and installed layouts.
- Cover the complete execution boundary and common nested security paths with deterministic conservative risk rules.
- Reject the demonstrated malformed-path, Markdown-fence, and local-reference false positives while preserving presence-only semantics.
- Repair and pin the existing security workflows, isolate their Python imports, and retain read-only PR execution.
- Publish and inspect a narrowly supported merge-protection profile without activating it automatically.

**Non-Goals:**

- Authenticating review prose or test waivers, proving semantic spec quality, or changing red-to-green verdict semantics.
- A new evidence database, agent runtime, real-agent benchmark system, general release manager, or uninstall command.
- Automatic hook activation, agent registration, repository-setting mutation, dependency installation, merge-queue support, or privileged `pull_request_target` execution.
- Rewriting unrelated OpenSpec capabilities or asserting regulatory compliance.

## Decisions

### 1. Share installation behavior through a small standard-library installer

Keep `sh install.sh <root>` and the PowerShell `-Root` interface. Make them thin source-relative launchers for a new `scripts/install.py`, with a checked-in `scripts/install-manifest.json` defining explicit source/destination files and executable-mode requirements. Validate a usable Python interpreter before copying. Use the existing Python floor of 3.8 for this change; do not silently raise it while adding Windows coverage.

The manifest is an allowlist, not a recursive copy of the repository. Include supported root tools, both foundation workflows, the PR template, hook implementations, the skill files/assets/references needed by the copied suite, and CI adapter templates plus their generic runner. Do not copy the toolkit's self-test `ci.yml`, repository-specific CODEOWNERS identities, Git metadata, local agent settings, sessions, or caches into another project. Copying skill files does not register them with an agent.

Record successful ownership in a destination `.sdlc-install.json` with a schema version, source-manifest identity, and installed content/mode hashes. This is installation state, not a security attestation. Treat malformed or missing state conservatively. Classify the installer, its source manifest, and installation-control state as Critical because they govern future managed writes.

The install sequence is: resolve and validate sources; build the complete destination plan; reject conflicts and escaping paths; stage verified files; compare each destination again immediately before atomic replacement; verify the payload using trusted source-side tooling; publish completed state last. Report any later partial failure and the paths already changed. Do not promise cross-file transactional rollback or overwrite concurrent edits during recovery.

Missing destinations are installable. An existing file identical to the incoming file is retained without rewriting. An existing managed file matching its last installed version can be upgraded. Differing unowned or locally modified files abort the plan before payload writes. Legacy installs without state do not authorize replacement; operators reconcile conflicts explicitly. An interrupted run can be retried because already-copied identical files are retained, while remaining conflicts are still refused.

**Rejected alternatives:** keeping two independent copying implementations risks platform drift; unconditional `--force` defeats the safety goal; preserving conflicts silently while reporting success hides an incomplete upgrade; a full package manager or transactional filesystem layer is unnecessary for this scope.

### 2. Keep one implementation per helper and stabilize public paths

Add small root entry points at `scripts/check_spec.py`, `scripts/check_brief.py`, and `scripts/redgreen.py`. They resolve and execute the existing skill-local implementations from the toolkit root and preserve arguments, output, and exit codes. The manifest includes those implementations and their referenced resources, so removing the source checkout cannot break an installed command. Existing skill-local entry points remain usable because skills already distribute them to external consumers.

Include `skills/ai-sdlc/assets/ci-generic.sh` and its referencing CI adapter templates at their existing relative paths. Keep the hook advisory and do not alter `core.hooksPath` or `.git/hooks`. Inspect and test the actual Git-dispatched Windows path, including environments with `python` but no `python3`; copying `pre-push.ps1` alone is not Windows integration proof.

Distribute a managed root `.gitattributes` containing LF rules only for the attributes file and the shell entry points (`install.sh`, `hooks/pre-push`, shell hook implementations, and the generic runner). Include it in the install manifest and Critical boundary. Existing differing attributes are conflicts, not permission to overwrite user policy. Verify an actual installed checkout roundtrip under `core.autocrlf=true`; installation-time normalization alone is insufficient.

**Rejected alternatives:** duplicating helper implementations creates drift; moving them without preserving skill-local entry points breaks shipped consumers; documenting source-only paths does not fix the installed-target contract.

### 3. Make risk floors cover execution and change metadata

Expand built-in Critical coverage to the full `scripts/` import boundary, installers and manifests, hooks, enforcement workflows, CODEOWNERS locations, shipped CI runners/adapters, skill executable instructions/scripts, and documented agent-control files. Enumerate supported agent-control paths from the existing adapters and guidance; do not treat every Markdown file as executable. Test every declared execution-boundary path against a deliberately permissive custom configuration.

Update shipped configurable defaults for root and nested auth/authentication, payment/payments, migration, infrastructure, and security directories. Remove the shipped Lite rule for dependency lockfiles in favor of a Standard floor. Preserve config format `version: 1`: it is the parser schema, not a counter to increment for every policy edit. Existing installations retain their calibrated config; doctor and migration guidance identify newly recommended rules rather than silently replacing them.

Carry Git status, old/new modes, and raw paths alongside normalized matching paths. Preserve NUL-delimited input, both sides of renames, and literal path handling. Use raw paths for exact Git lookup and normalized paths only for classification. Executable mode, symlink/type changes, executable-looking suffixes, and unknown file kinds cannot receive documentation-only exemptions. Recognized prose formats and static documentation patterns are a published convention, not a claim that content was semantically proven harmless.

Keep existing path-list CLI calls usable for planning. They report a path-based lane and unavailable metadata; CI must obtain metadata for its evaluated diff before granting a non-executable exemption. Required metadata that cannot be read is a tooling error, not an exemption. A malformed path can still produce the existing conservative local classification, but the CI evidence calculation must not drop it.

**Rejected alternatives:** model-only classification is not reproducible; root-only auth patterns miss common layouts; globally classifying all files Critical defeats proportionality; replacing calibrated configs during installation can weaken a user's policy.

### 4. Tighten structural evidence without claiming semantic verification

Use a fence scanner that records the delimiter character and complete opening length. Close only on the same marker with at least that length and permitted trailing whitespace. Keep comments, fenced headings, key/value links, declarations, and waivers out of evidence detection. Cover longer backtick and tilde blocks, mismatched markers, invalid closers, and unterminated fences. This remains a documented supported Markdown subset, not a general Markdown rendering engine.

Retain every changed-path diagnostic through `detect`. Invalid or indeterminate required CI input becomes the existing tooling-error exit class. A documentation exemption requires the complete diff and acceptable path/type/mode facts, not a filtered subset of paths.

Resolve local spec/intent references against the explicit evaluated Git revision using literal paths. Require a nonempty regular tracked blob; reject metadata, symlinks, missing paths, and untracked checkout files before reading or describing their content. If Git membership cannot be established, report unverified locally and fail as a tooling error in CI. Continue to accept external URL references only with the existing explicit unverified limitation.

Review prose and well-formed test waivers remain presence-only evidence, and configured test-path changes do not become proof of a passing test run. These are deliberate limits, not silently upgraded guarantees.

**Rejected alternatives:** checking only `isfile`/size admits Git metadata and untracked files; silently dropping malformed inputs invalidates all-path assertions; semantic judging or authenticated approval lookup would expand this change into a different evidence system.

### 5. Harden the existing CI execution model rather than elevating privileges

At the selected pinned Gitleaks action version, supply the documented token environment explicitly, grant only the required `contents: read` and `pull-requests: read`, disable optional comments, and set checkout credential persistence to false. Verify the exact action inputs and disable-comment setting against its pinned source. Organization licensing and fork-secret availability remain explicit deployment prerequisites; an unsupported or unlicensed topology fails with a setup diagnostic, never a clean result or a privileged-event workaround.

Pin external enforcement actions to reviewed full SHAs while retaining human-readable version comments. Preserve PR event coverage, the five-minute evidence timeout, trusted base and candidate checkouts, and direct propagation of gate/scanner failures. Contract tests reject mutable pins, persisted credentials, skipped required steps, and ignored failures.

Run the GitHub and generic gates with Python isolated mode. Load the required trusted `lane.py` by its exact path without re-adding the surrounding directory to the import search path. Isolated mode alone is insufficient if code subsequently inserts the entire scripts directory. Exercise shadow names that the gate imports both before and after loading the lane module, and ambient `PYTHONPATH`/user-site cases. Do not execute candidate code while classifying paths or resolving evidence.

**Rejected alternatives:** `pull_request_target` changes the credential trust boundary; pinning only the scanner leaves the gate's checkout mutable; protecting a few filenames misses newly added import dependencies; isolated mode followed by unrestricted `sys.path` insertion is incomplete isolation.

### 6. Add explicit strict readiness while retaining offline doctor behavior

Keep `doctor.py --root <repo>` offline and preserve `--check-branch-protection`. Add `--require-enforcement` for use with the remote-inspection option; using it without explicit remote opt-in is a usage error. This profile-specific result must not equate an inactive optional hook with missing hosted enforcement, nor treat generic doctor exit zero as proof of merge protection.

The supported profile requires exact `evidence` and `gitleaks` check contexts from the expected GitHub Actions app, PR-only protected-branch changes, required code-owner review across the complete boundary, a supported fresh-review control, and up-to-date check evaluation. Resolve the expected application's identity from authoritative provider metadata rather than accepting any nonzero app ID. Inspect effective branch rules, applicable rulesets, and relevant bypass settings; any inaccessible prerequisite remains unverified. Disclosed bypasses require a separate operator decision and cannot silently satisfy the no-unreviewed-bypass profile.

REST transport remains GET-only. The sole POST exception is a constant read-only GraphQL query for `repository.mergeQueue`, with owner, repository, and branch supplied as variables. GitHub does not execute this query via GET. Do not accept arbitrary query text, use a mutation, or broaden REST methods. Missing/unsupported queue data remains unverified.

For local execution, recognize a constrained supported workflow profile rather than attempting a complete YAML interpreter. Unsupported conditions, permission expressions, indirection, or workflow shapes remain unverified. Strings matching a command or `contents: read` are never sufficient on their own. Test skipped steps, ignored failures, wrong app IDs, similar context names, incomplete API responses, and unreadable bypass settings. Support for arbitrary customized workflows and merge queues is not claimed.

Provide a manual activation checklist and read-only verification commands. Do not copy owner identities from this toolkit into downstream repositories or issue GitHub mutation calls. The earlier audit's missing required check is a dated observation; operators must re-check current settings when activation is separately authorized.

**Rejected alternatives:** treating a present CODEOWNERS file as required review, matching arbitrary context suffixes, accepting inaccessible settings as success, or automatically enabling branch protection would overstate evidence or cross the authorization boundary.

### 7. Verify user journeys and the actual shipped contract

Add focused failing-first regressions before each implementation area. Existing tests remain the base: `tests/test_lane.py`, `tests/test_evidence_check.py`, `tests/test_doctor.py`, `tests/test_hook.py`, `tests/test_check_spec.py`, `tests/test_check_brief.py`, `tests/test_redgreen.py`, `tests/test_templates.py`, and `tests/test_ci_adapters.py`. Add installer and security-workflow integration tests where no real invocation coverage exists. Do not substitute synthetic lane configs for tests of `scripts/lane-config.yaml`.

| Contract | Required verification |
| --- | --- |
| Non-destructive install | Actual POSIX/PowerShell invocation into temporary clean and brownfield Git repositories; conflicts, unrelated cwd, spaces, missing sources, escaping paths, retries, and injected I/O failure |
| Complete payload | Manifest-to-installed-tree comparison, helper CLI smoke tests, referenced-resource checks, and generic runner use after source checkout removal |
| Classification | Shipped-policy table plus executable/type changes, malformed filenames, both rename sides, nested security paths, and permissive custom-config boundary tests |
| Evidence | Long/mixed fences, invalid closers, malformed mixed diffs, tracked/untracked/metadata/symlink references, and existing valid lane templates |
| CI trust | Base-policy preservation, shadow-module and ambient-import attacks, full action pins, least privilege, token/comment contract, and nonzero propagation |
| Readiness | Offline/no-network behavior, exact source identities, absent requirements, stale-review settings, bypass visibility, unsupported shapes, and a fully observed profile fixture |

Keep the existing Linux and macOS jobs and add a Windows job that actually invokes PowerShell installation and Git hook dispatch. Use fake non-production secret data in isolated test fixtures; do not add live credentials to the repository. Provider API mocks establish local behavior, not successful hosted scans. Record hosted clean/seeded, fork, and private-repository smoke results separately when an authorized fixture repository and scanner prerequisites are available; otherwise leave those results explicitly unverified.

Use `skills/verify-and-evals/scripts/redgreen.py` for commit-bound proof until the root wrapper exists. Inspect the expected assertion failures and selected tests rather than accepting collection errors, crashes, or unrelated failures as sufficient evidence. Generating a candidate commit, pushing, creating PRs, or provisioning hosted fixtures requires separate authorization. Local red-before/green-after output is provisional until proof can reference an authorized committed candidate or CI revision.

## Risks / Trade-offs

- **Local changes versus upgrades:** refusing conflicts interrupts automatic upgrades. Mitigation: list exact paths, retain the user's bytes, document manual reconciliation, and make repeated identical installs stable.
- **Partial filesystem failure:** per-file atomic replacement is not a multi-file transaction. Mitigation: preflight, compare-before-replace, publish completed state last, report partial results, and never claim success after failure.
- **Hostile filesystem races:** path checks alone are not a sandbox against another privileged process continually replacing directories. Mitigation: containment checks and controlled staging; do not claim protection against a compromised host.
- **Larger Critical boundary:** protecting scripts, agent controls, and CI adapters can increase review volume. Mitigation: retain Lite for recognized prose, explain every escalation, and backtest the actual policy before rollout without weakening built-in controls.
- **Base-revision bootstrap:** the first hardening PR is still judged by the previous base checker. Mitigation: require independent human review and regression jobs, then test a follow-up fixture using the merged hardened base.
- **Incomplete provider evidence:** API permissions, ruleset visibility, licensing, or fork limitations can block a readiness verdict. Mitigation: explicit unverified/unsupported states and separate authorized operator follow-up; no automatic bypass or event elevation.
- **Workflow recognition limits:** a conservative supported profile can reject legitimate customization. Mitigation: report unsupported shape, preserve offline inspection, and require reviewed support rather than infer execution from arbitrary YAML.
- **Residual presence-only assurance:** meaningful-looking prose, external URLs, and test-path edits still do not prove approval or correctness. Mitigation: retain these limitations in output and guidance; defer stronger evidence semantics explicitly.

### Threat note

Untrusted inputs include candidate files and names, PR descriptions, ambient Python paths, pre-existing destination content/state, and incomplete provider responses. Protected assets include user-maintained files, the trusted checker/policy, read-only CI credentials, and the integrity of the merge decision. The implementation must not execute candidate code or destination tooling to inspect evidence, print matched secrets or file contents in errors, or silently escalate GitHub permissions. Workflow and checker changes still require external owner-review enforcement; base-copy isolation alone does not protect a PR-editable workflow definition.

## Migration Plan

1. Obtain explicit approval of these Critical-lane artifacts before implementation. Record two independent reviewer identities for the implementation, covering gate/security and installer/platform behavior; do not pre-fill approval claims.
2. Add focused regressions, observe the expected failures on the baseline, implement the smallest fixes, and run the complete relevant test matrix and mutation checks. Keep raw outputs and candidate/tooling identifiers in the implementation trace.
3. Validate fresh and legacy installations in disposable local targets, including a calibrated config that must not be overwritten. Compare the proposed default policy against a labeled risk corpus and inspect newly escalated paths.
4. Merge only through separately authorized repository operations after the required reviews. Verify a follow-up change against the hardened base because the hardening PR itself uses the previous gate version.
5. Pilot the installed foundation in an explicitly authorized repository. Monitor installation conflicts/failures, false lane escalations, malformed-input rejections, scanner setup failures, check completion, and readiness results. Do not broaden adoption while a required hosted scenario is unverified.
6. Activate branch protection, required checks, owner review, or hooks only under a separate explicit operator authorization using the published checklist. Re-run strict readiness after activation; installation success is not a substitute.

Rollback is also an authorized operation. Restore only managed files that still match the version being rolled back; never reset the worktree or overwrite later user edits. Preserve custom policy and the install-state record for diagnosis. A code rollback does not silently remove required checks or weaken hosted protection: if the old version cannot meet the current profile, report the incompatibility and require an operator decision. Do not promise a general uninstall/rollback command in this change.

## Open Questions

- Local implementation was authorized by the user's explicit apply request on 2026-11-05. Branch-protection mutation, commits/pushes/PRs, hook activation, and hosted fixture creation still require separate authorization.
- Before a hosted pilot, the operator must identify the target branch/repository, real owner identities, supported review-freshness policy, and any intentional bypasses. These are environment inputs, not permission to invent identities or change settings.
- Scanner licensing and fork/private-repository availability must be verified in that authorized environment. Until then, provider integration results remain unverified rather than blocking creation of these planning artifacts.
- No unresolved choice is required to write the local implementation: the manifest contract, helper layout, strict-readiness behavior, config compatibility, and deferred features are defined above. Any proposed expansion requires updating the proposal and affected specs before implementation.

## Implementation Record

- Authorization: explicit user request to apply `harden-sdlc-foundation`, 2026-11-05 at 10:28 UTC. This covers the planned local code/tests/documentation changes, not commits, pushes, PRs, hosted fixtures, hook activation, or GitHub-setting mutations.
- Baseline: `837794291b62d20fa28566b39552fc98befef52a`; the only pre-existing working-tree additions were this change's planning artifacts.
- Classification: the planned scripts, installer, hook, workflow, test, guidance, and change-artifact paths were classified before implementation with `python3 -B scripts/lane.py --paths ...`; result: `Critical: matched Critical rule scripts/lane.py (built-in) (scripts/lane.py +9 more)`.
- The threat note, staged rollout, ownership-preserving rollback, and separate human-review/operational approval boundaries above continue to apply. No human review or hosted readiness result is implied by this record.
- Baseline validation: `PYTHONDONTWRITEBYTECODE=1 TMPDIR=/var/folders/0q/2f3g6rrs1qq0nfc__7vt50640000gp/T/kilo python3 -m unittest discover -s tests -v` passed all 428 tests in 204.547 seconds before implementation changes. Fixture repositories were temporary; the project's Git history and settings were not changed.
- RED, task 2.1: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_lane.py -k ShippedPolicy` ran 5 tests with 34 expected assertion failures before classifier/config implementation changes. Failures exposed permissive execution-boundary classification, nested security paths, executable/unknown documentation, and Lite lockfiles; recognized prose already passed.
- RED, task 2.2: `python3 -m unittest discover -s tests -p test_lane.py -k change_facts` (bytecode disabled, approved fixture TMPDIR) ran 6 tests with 6 expected assertion failures: missing raw-path/mode/status records, Lite executable/symlink documentation, and success on missing metadata. Existing rename and NUL-delimited path tests remain in the suite.
- GREEN, tasks 2.1-2.4: `python3 -m unittest discover -s tests -p test_lane.py -v` (bytecode disabled, approved fixture TMPDIR) passed all 50 tests in 2.389 seconds after the policy and Git change-fact implementation. Legacy path-list entry points, local malformed-path escalation, config format 1, rename visibility, and recognized prose behavior remain covered.
- RED, task 3.1: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_evidence_check.py -k FenceSafety` ran 4 tests with 7 expected assertion failures before parser changes. Cases include shorter/mismatched/unterminated fences and invalid closing text, including literal HTML comments inside code fences.
- GREEN, task 3.2: all 72 evidence tests passed in 22.167 seconds after the fence scanner change, including existing PR-template and valid-evidence cases.
- RED, task 3.3: `python3 -m unittest discover -s tests -p test_evidence_check.py -k RevisionEvidence` (bytecode disabled, approved fixture TMPDIR) ran 10 tests with 9 expected assertion failures. Literal-path lookup already passed; missing metadata, unsafe exemptions, Git metadata, symlink/untracked/wrong-revision references, and working-tree substitution failed before implementation.
- GREEN, task 3.4: all 82 evidence tests passed in 26.225 seconds after tracked-blob lookup and complete change-metadata enforcement. The separate template suite exposed two old non-Git fixtures that must become committed evidence fixtures, plus a delegated root-wrapper import integration issue; neither is counted as passing verification yet.
- RED, task 4.1: `python3 -m unittest discover -s tests -p test_ci_security.py -k TrustedExecution` (bytecode disabled, approved fixture TMPDIR) ran 8 tests with 6 expected assertion failures. Both actual entry points exited 0 when adjacent or ambient modules exited early; the two existing base-policy-preservation cases already passed. No hosted workflow was created or run.
- GREEN, task 3.5: the 82 evidence tests and all 28 template tests pass after committed template fixtures and isolated lane loading; canonical helper import delegation also preserves the shared secret-pattern contract.
- RED, task 4.3: `python3 -m unittest discover -s tests -p test_ci_security.py -k WorkflowContract` ran 4 tests with 3 expected assertion failures before scanner/pin changes: mutable checkout references, persisted scanner checkout credentials, and missing scanner token settings. Pinned Gitleaks source documentation confirms `GITHUB_TOKEN`, `GITLEAKS_ENABLE_COMMENTS=false`, and the organization-license prerequisite. GitHub's authoritative v6 ref resolved to commit `d23441a48e516b6c34aea4fa41551a30e30af803`; no action major version was upgraded.
- Current CI-focused verification: `test_ci_security.py` ran 14 tests, 12 passed and 2 user-site negative-control cases were skipped; `test_ci_adapters.py` passed 4 tests. Adjacent/ambient module rejection, base-policy preservation, scanner settings, immutable pins, and credential/permission contracts pass. Task 4.2 remains open until the user-site control is established; no hosted scanner result is claimed.
- Installer worker RED: 37 initial installer tests exposed 31 expected assertion failures/subtest failures and 12 platform skips; separate mtime/stale-doctor checks failed 3/3 as expected, and actual Git hook interpreter checks failed 2/2 before implementation. Further state-race and root-import failures were reproduced before their fixes.
- Installer worker final focused results: `test_install.py` ran 52 tests (34 passed, 1 known CRLF-checkout failure, 17 native-platform skips); `test_hook.py` passed 29; `test_check_*.py` passed 102; `test_redgreen.py` passed 28; the shared-pattern template test passed. Tasks 5.1, 5.2, 5.3, and 5.5 are complete. POSIX launchers and the 62-file payload are implemented, but tasks 5.4, 5.6, 5.7, and 7.1 remain open for the documented platform gaps.
- Doctor worker RED: three workflow-safety tests failed on suffix identity matching, skipped-gate verification, and missing explicit GET/host behavior; 25 strict-profile tests produced 83 expected assertion/subtest failures before implementation. Further provider-completeness tests found missing pagination/queue checks and unsupported value handling. These are regression evidence, not proof that strict readiness is complete.
- Doctor worker final suite: `python3 -m unittest discover -s tests -p test_doctor.py -v` passed 99 tests in 116.963 seconds. Task 6.1 is complete; tasks 6.2-6.4 remain partial. This green suite does not cover the later manual root-only CODEOWNERS anchoring failure, and GET-only classic merge-queue visibility is still unresolved.

### Pause and resumed authorization

Implementation was paused after the user dismissed the scoped-adjustment question on 2026-11-05. Neither proposed adjustment below is approved, and no proposed POST query or attributes file was implemented. The original constraints and unchecked task requirements remain in force.

The preceding paragraph records the earlier pause, not the current authorization. The user subsequently selected **Approve both (Recommended)** in the resume question on 2026-11-05 and explicitly requested continuation. The two adjustments above are now authorized, and their corresponding design, specifications, and tasks have been updated. Commits, pushes, PR creation, hosted-setting mutations, and hook activation remain excluded. Historical findings below are retained as evidence of why the adjustment was necessary, not current prohibitions.

- Merge-queue inspection: the read-only GET GraphQL probe returned schema introspection rather than the requested repository query. Classic REST protection does not establish absence of a merge queue, so the specified classic strict profile cannot honestly be completed with GET-only inspection. A fixed read-only GraphQL query via POST was proposed, not authorized. Do not treat mocked complete-profile responses as provider verification.
- Windows checkout: `POSIXInstallation.test_installed_git_hook_survives_crlf_checkout_policy` reproduces an actual push failure after `core.autocrlf=true` rematerializes installed hooks: `fatal: cannot exec 'hooks/pre-push': No such file or directory`. Persistent LF attributes, corresponding manifest/classifier coverage, and a checkout-roundtrip regression were proposed, not authorized. The failing test remains visible.
- Additional doctor review found that stripping a leading slash from CODEOWNERS patterns can incorrectly treat root-only ownership as covering nested/future control files. This in-scope defect remains open while implementation is paused; readiness must not be relied on as complete.
- Native PowerShell/Windows execution, the two user-site injection controls, ShellCheck (not installed), commit-bound red/green proof, hosted smoke tests, and two independent human reviews remain unverified or outstanding. No project commits, pushes, PRs, hook activation, or hosted-setting mutations occurred.
- Pause inventory includes a modified tracked `scripts/__pycache__/doctor.cpython-314.pyc`, likely regenerated by an isolated interpreter probe that ignored the bytecode environment flag. It has not been reverted without confirmed provenance; it is not an intended implementation artifact.

### Resumed verification

- The approved attributes extension first failed the permissive-policy regression for root `.gitattributes`; the built-in Critical boundary was then expanded to cover that basename at every depth.
- The two previously skipped user-site controls used the wrong path scheme for macOS framework Python. The test now queries the interpreter's actual user-site path without executing site initialization. All 14 CI-security tests pass with zero skips, including a real user-site startup injection negative control and rejection through both isolated runners. Task 4.2 is complete.
- The approved LF extension now installs 63 explicit files. Actual installed-hook checkout/dispatch under `core.autocrlf=true`, custom-attributes conflicts, and narrow LF-rule tests pass. Native PowerShell/Windows remains unverified: 17 PowerShell cases and one junction case are skipped on this host; tasks 5.4 and 7.1 stay open for that verification.
- Strict-readiness regression work includes a real successful public read-only GraphQL POST query, fixed-query/variable-only transport tests, root-anchor and case-variant ownership tests, and conservative rejection of unsupported directory-only recursive owner patterns. The direct takeover reproduced two remaining ownership assertion failures before fixing them. The integrated run passed all 110 doctor tests; this does not attest the target repository's live protection settings.
- A Windows CI contract test failed before adding the Python 3.8/3.13 native job. The job now executes `PowerShellInstallation` and `FilesystemSafety` through `pwsh`, including actual Git dispatch and junction behavior; it has not been executed on a hosted Windows runner in this session.
- Integrated validation initially ran 567 tests in 389.271 seconds: 548 passed, 18 platform skips, and one documentation-reference failure. That failure was a prose phrase interpreted as a nonexistent `scripts/config` path; after correcting it, all 28 template/reference tests passed.
- `python3 scripts/lane_backtest.py --limit 50` evaluated all 12 first-parent commits: 11 Critical, 1 Standard, 0 Lite, no unclassified/skipped commits. The increase from the earlier 8 Critical/3 Standard/1 Lite reflects protection of the broader tooling and instruction boundary. Shipped-policy fixtures still keep recognized prose Lite and normal code Standard while escalating known security paths; a tooling repository's historical ratio is not an accuracy score or a reason to weaken the floor.
- Mutation maintenance first reproduced a stale target, then a baseline-only regression identified 13 stale anchors. They were updated to equivalent fault intent; the raw-path-validation removal is now explicitly non-equivalent because safe-path rejection and Git lookup errors have different observable outcomes. Baseline-only anchor checks are excluded from behavioral observer modules, so they cannot manufacture mutation kills.
- The first updated mutation run passed its unmodified baseline but exposed an undetected absolute-path-guard removal at mutant 8. That known-failing run was stopped; a dedicated absolute-prose-path test now kills mutant 8 without changing the correct guard implementation. A failing-first harness test then established fail-fast observer execution while keeping the baseline complete. The final complete battery is being rerun; earlier partial mutation output is not claimed as a passing battery.
- `openspec validate --all --strict --no-interactive` passed the change and all seven existing specs. `git diff --check` passed. ShellCheck is unavailable, and its installation/bytecode-cleanup question was dismissed; neither action is authorized by a generic continuation request.

### Critical review package

- Intent and acceptance: `proposal.md` and the four delta specs under this change's `specs/` directory. This implementation is Critical, not eligible for a lower-lane shortcut.
- Threat and rollout: the threat note, risks, staged rollout, and ownership-preserving rollback plan above remain the governing plan. No live protection, hook, deployment, or bypass setting was changed.
- Trace and decisions: retained the standard-library runtime and config format 1; replaced unsafe copying with explicit ownership and failure contracts; kept trusted-base execution but isolated imports; tightened structural evidence rather than claiming authenticated approval or semantic correctness. Rejected overwriting custom files, accepting unknown readiness as success, and elevating PR privileges.
- Tools and attribution: OpenSpec CLI, Python unittest, Git fixture repositories, read-only GitHub inspection, shell fixtures, and the mutation runner; AI-assisted-by: Kilo. Early scoped internal workers contributed installer/doctor changes; after the user's no-delegation instruction all subsequent work was performed directly.
- Review notes: direct inspection and regressions found and corrected fence/comment interactions, missing Git facts, tracked-blob substitution, root-wrapper import compatibility, CRLF rematerialization, directory-only ownership overclaims, and the absolute-path mutation gap. Two independent human reviews have **not** been received; no reviewer identity or approval is fabricated.
- Outstanding evidence: native Windows/PowerShell execution, ShellCheck, the final mutation result, commit-bound red/green proof, and authorized hosted scanner/target-protection results. The regenerated tracked doctor bytecode is confirmed to come from the earlier isolated probe but remains an unintended diff until explicitly authorized cleanup. The working tree is uncommitted; do not label it ready to merge or archive while these gates remain open.
