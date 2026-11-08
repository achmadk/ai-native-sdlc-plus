## Context

See [proposal.md](proposal.md) for motivation and scope, and the two delta specs for behavior contracts. This design is required because the change introduces a trusted data resource and a contributor-checkout migration at the enforcement boundary.

Baseline: `0ee9a1b426778aa4bd2cf45092bf37eb852d52a7`. The read-only audit ran doctor on the real repository and observed one failure: `scanner-invokes-gate`. The workflow selects Gitleaks v3, but `scripts/doctor.py` compares it with one older constant. Existing tests invoke doctor on the source checkout but assert only script drift; their passing result does not establish zero overall failures. Fresh-install and Skills CLI acceptance have not been executed during planning.

The Git index contains 235 files and the 42 cleanup entries below. `.gitignore` already covers bytecode, `.omo/`, and `opencode_session.txt`; ignoring them did not remove previously tracked entries. The four generated OpenSpec skill-directory families need scoped ignore coverage.

`ci-security` is not yet a durable main spec: `harden-sdlc-foundation` proposes the broader capability. This change adds distinct requirement names in the same path, without replacing that delta or closing its pending tasks. The cleanup overlaps older pending bytecode work; reconcile status separately rather than performing duplicate removals or archiving another change.

## Goals / Non-Goals

**Goals:** keep the approved scanner set explicit and inspectable; make the installed inspector self-contained; detect drift against shipped files; remove only reviewed tracking entries while preserving local files and product discovery.

**Non-Goals:** arbitrary-SHA acceptance, automatic upstream approval, new hosted access, stronger semantic evidence judging, a new CLI, skill bootstrap redesign, description/evaluation tuning, global tool registration, or repository-history cleanup. No implementation is authorized by this planning request.

## Decisions

### 1. Keep a trusted scanner registry beside the inspector

Add `scripts/scanner-profiles.json` to the inspector distribution. Use a small version-1 schema containing the fixed scanner owner/repository and reviewed release/SHA entries. Validate exact field/type expectations, full lowercase 40-character SHAs, unique entries, and duplicate JSON keys; malformed or unsupported data is an actionable inspector failure, never a permissive fallback.

Resolve the file from the running inspector's own script location, not `--root`, current working directory, environment variables, or a user-supplied profile path. Validate it when inspection runs, rather than raising an unhandled error at module import. Keep current CLI forms and structured failure reporting.

Initial proposed entries, confirmed by upstream `git ls-remote` on 2026-11-08:

| Release | Commit | Reason |
|---|---|---|
| v2.3.8 | `f586c14365d4643c6aa59d472ae6e984bf47bb34` | Preserve the already supported structural profile |
| v3.0.0 | `e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e` | Match the currently shipped immutable workflow after contract review |

The v3 [pinned action metadata](https://github.com/gitleaks/gitleaks-action/blob/e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e/action.yml) uses Node 24. Its [migration documentation](https://github.com/gitleaks/gitleaks-action/blob/e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e/README.md) reports unchanged inputs, outputs, and behavior. That is upstream-reported compatibility, not a hosted scan result or independent approval. Record the implementation-time provenance/contract review before adding the entries.

Continue to enforce existing workflow shape, full-history checkout, credential, permission, event, comments-disabled, and license-expression checks. Do not add unrelated newer v2 pins simply because they exist. Recognition of the retained v2 entry is not a promise that an obsolete hosted runtime remains usable.

Rejected alternatives: accepting every full SHA would erase the approved-version boundary; deriving approval from the inspected workflow would allow self-attestation; fetching upstream approvals during inspection would change the offline trust model. Excluding the action from Dependabot would hide update pressure rather than coordinate reviewed policy updates, so Dependabot remains unchanged.

### 2. Ship the data as an owned runtime resource

Add the data file to `scripts/install-manifest.json`, with the same non-executable mode and ownership/conflict treatment as other data resources. Existing installer logic remains authoritative; update expected payload assertions rather than introducing another copier or state format.

An updated installed doctor must work after its source checkout is removed or renamed. Missing or corrupt data in its own bundle is a failure. Do not add a requirement that an externally inspected repository contain this registry, and do not add it to hosted lane/checker byte comparisons: the evidence workflow does not execute this doctor-only data file. A target's own registry is ignored by an external inspector.

### 3. Separate integration truth from protocol fixtures

Add two regression paths: aggregate zero-failure inspection of the real source checkout; and subprocess execution of the installed doctor with the original fixture source unavailable. Assert overall failures and scanner recognition, not only script drift. Warnings and unverified external controls remain visible.

Keep existing bounded-workflow fixtures independent of the production registry. Add focused tests for the new v3 entry, retained v2 entry, unlisted full SHA, wrong repository, mutable/short ref, invalid or missing trusted data, and target-owned registry poisoning. Do not make all fixtures read the subject's allow-list, which could cause a weakened policy to validate itself.

Write source/installed regression tests before implementation and capture the current scanner mismatch as the expected failure. Avoid module-level reads of the future data file that would turn baseline verification into a collection error. Confirm installed data is included in ownership hashes, idempotent reruns, and local-conflict protection.

### 4. Use an exact tracking-removal inventory

Implementation removes these entries from the index only, preserving local contents. Re-enumerate and compare before mutation; do not expand a broad glob into new deletion scope. Snapshot candidate working-file contents and unrelated status, and require them to be preserved afterward. No history rewrite or automatic deletion of local directories is included.

Bytecode entries (11):

```text
scripts/__pycache__/doctor.cpython-314.pyc
scripts/__pycache__/doctor_online.cpython-312.pyc
scripts/__pycache__/evidence_check.cpython-314.pyc
scripts/__pycache__/lane.cpython-314.pyc
scripts/__pycache__/lane_backtest.cpython-312.pyc
scripts/__pycache__/trace_lint.cpython-312.pyc
scripts/__pycache__/trigger_eval.cpython-314.pyc
scripts/tests/__pycache__/test_suite.cpython-314.pyc
tests/__pycache__/test_extras_doctor_online.cpython-312.pyc
tests/__pycache__/test_extras_lane_backtest.cpython-312.pyc
tests/__pycache__/test_extras_trace_lint.cpython-312.pyc
```

Local state/session entries (7):

```text
.omo/run-continuation/ses_f04b98cb4ffeCx6nKvsqbe5RAi.json
.omo/run-continuation/ses_f04b98e9affe3zc8GKlTyqVtL6.json
.omo/run-continuation/ses_f04b99125ffeybOnwgIMpnJGeR.json
.omo/run-continuation/ses_f04b9950effePhHMbiIfp6WbdV.json
.omo/run-continuation/ses_f04b99840ffef2XISBl5Lc1jnS.json
.omo/run-continuation/ses_f08328a4dffeu5qacoLW91cpUp.json
opencode_session.txt
```

Generated instructions (24) are exactly `SKILL.md` in each combination of these four roots and six directories, not all content beneath the tool roots:

| Roots | Directories |
|---|---|
| `.agents/skills/`, `.claude/skills/`, `.kilocode/skills/`, `.opencode/skills/` | `openspec-apply-change`, `openspec-archive-change`, `openspec-explore`, `openspec-propose`, `openspec-sync-specs`, `openspec-update-change` |

Preserve root `AGENTS.md`, all `skills/` product sources, `adapters/`, authored `.claude/` commands/configuration, `.cursorrules`, Copilot instructions, and `openspec/` specifications/history. Do not read or republish session-file contents merely to perform index hygiene. Any suspected historical secret exposure is a separate investigation, not solved by untracking.

### 5. Guard the source index and document regeneration

Add narrow generated-OpenSpec ignore rules while retaining the existing runtime/session exclusions. Add `tests/test_repository_hygiene.py` checks against Git-index paths, including recurrence despite ignore rules and preservation of product names. This is a source-checkout baseline guard, not a behavioral mutation observer; a copied mutant tree without its own Git index must not produce a false mutation kill.

Document the contributor change in `docs/COMPATIBILITY.md`: the project root/specs are already initialized; contributors explicitly choose their tools for local generation and use `openspec update` to refresh selected instructions. CLI help confirms `openspec init --tools <selection>` and `openspec update [path]`; no `--force` or automatic all-tool registration is planned. Keep generated compatibility directories local/ignored. New hand-authored Kilo agents and commands use `.kilo/`, not legacy project-config paths.

### 6. Verify discovery on clean candidate content

The Skills CLI [command reference](https://github.com/vercel-labs/skills/blob/main/docs/commands.md#skills-add) supports local-directory sources and `--list` without installing skills. Verify the candidate's tracked distribution, not an arbitrary working directory that still contains the preserved local generated copies, and not the unchanged remote default branch.

Use an owned clean export/clone of the candidate with a recorded tree/content identity, then run the supported listing operation and compare names with the ten-skill spec. Record CLI version, source, command, and output. This check does not prove Skills-only runtime bootstrap, which belongs to WS3. An unavailable CLI/Node environment or required package download needs separate authorization and remains a verification blocker; do not install tools or claim a count from inspection alone.

Do not label an export of unchanged HEAD as the repaired candidate. If verification precedes a commit, record the explicit source-file inventory and content hashes for the clean snapshot, including intended additions and excluding the reviewed removals and ignored local files. Such a snapshot is not canonical committed red/green evidence.

## Risks / Trade-offs

- Approval data becomes a runtime dependency -> ship it with the inspector, validate it explicitly, and exercise missing/corrupt installed-bundle cases.
- A target attempts to approve its own code -> resolve only inspector-owned data and test a poisoned target registry.
- Supporting v3 is mistaken for observed scanning -> keep bounded recognition, authentication/licensing, runtime support, and actual hosted results separate.
- Future dependency bumps drift again -> retain Dependabot and let source/installed consistency tests require a coordinated reviewed registry update.
- Cleanup hides source loss or breaks contributor setup -> exact inventory, index-only removal, local-content preservation, narrow ignores, and explicit regeneration documentation.
- New metadata/test files change counts -> report the actual post-change inventory and explanations; do not game a file-count target or reuse older figures.
- Registry or discovery validation is mocked into success -> retain real subprocess integration and independent negative cases, and record unavailable tooling as incomplete.

### Threat Note

The registry is approval policy, not untrusted repository configuration. Its location and contents are part of the trusted inspector distribution. An inspected repo, ambient path, or current working directory cannot expand it. Unknown or unreadable policy must not be hidden by a green health summary. Existing read-only credentials, disabled comments, immutable pins, advisory hooks, and fail-closed CI remain mandatory. Source cleanup changes tracking only and does not purge history or certify that old session files contained no secrets.

## Verification and Migration Plan

1. After explicit apply authorization, record current revision, lane, inventory, tool versions, and the specific doctor failure; refresh scope if the baseline differs. Reconfirm v2.3.8/v3.0.0 provenance before changing the trusted set.
2. Add failing source/installed aggregate-health tests and an index-hygiene regression before implementation. Record scanner mismatch and tracked-artifact failures separately from import/setup failures.
3. Implement registry validation and manifest inclusion; run positive/negative policy tests, source doctor, installed doctor with source unavailable, and ownership/conflict tests. Preserve all unrelated diagnostics.
4. Apply only approved index removals; verify local-content preservation, ignored recurrence, clean candidate discovery, and the complete Git inventory. Do not stage unrelated changes or create a commit implicitly.
5. Run full unit tests, mutation verification, ShellCheck, and available platform integration checks in the main foreground. Record exact counts/skips/versions and compare to the baseline; do not use the prior 604-test report as this change's result.
6. Run strict OpenSpec validation, final scope/diff checks, and the applicable local evidence check. Canonical `scripts/redgreen.py` proof requires an explicitly authorized committed candidate; do not substitute uncommitted observations or unrelated failures.

Roll out only after review. Validate the owned package on clean and conflicting targets before broader adoption; actual hosted CI requires its own authorized run. Keep the scanner workflow pinned to the current v3 SHA and leave credentials/protection settings unchanged.

Rollback treats doctor, its registry, and the manifest as one compatible bundle. Revert an incorrect registry entry together with the affected behavior under review; never fall back to accepting arbitrary pins. Restore tracking only for specifically reviewed files if contributor tooling breaks, without overwriting preserved local copies or rewriting history. Do not downgrade to an obsolete scanner runtime merely to obtain a green local check.

## Approval and Handoff

Planning completion is not permission to implement or to mutate the Git index. The apply request and required command-level approvals must cover the named cleanup; any expanded inventory, dependency provisioning, commit, push, agent registration, or hosted action needs separate authorization.

Approved-by: Achmad Kurnianto, 2026-11-08. Explicit approval covers WS0 implementation and the listed 42 index-only removals while retaining local files. Commits, pushes, tool installation, and hosted/settings changes are excluded. This is scope authorization, not either independent reviewer's approval.

Two independent reviews remain pending: trusted-policy provenance and poisoning resistance; and source/installed integration, cleanup preservation, discovery evidence, and rollback behavior. Record actual identities and findings only when supplied. Later workstreams and other active changes remain untouched.

## Implementation Evidence

- Task 1.1: baseline remains `0ee9a1b426778aa4bd2cf45092bf37eb852d52a7`; initial changes were only this planning directory. The current Git inventory matches all 42 reviewed entries. The complete intended runtime/test/documentation/cleanup scope classifies Critical.
- Native `python -B scripts/doctor.py --root . --json` reproduced exactly one failure, `scanner-invokes-gate`, with 30 verified results, three warnings, one informational result, and two unverified hosted controls. This was a source inspection, not a fresh-install or hosted result.
- Implementation-time `git ls-remote` reconfirmed v2.3.8 at `f586c14365d4643c6aa59d472ae6e984bf47bb34` and v3.0.0 at `e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e`. No workflow, repository setting, or upstream reference was changed.
- Task 1.2 RED: the new source-CLI and installed-CLI health regressions ran two tests in 7.858s and both failed their exit-zero assertion specifically on `scanner-invokes-gate`. The installed test removed its owned fixture source before invoking the installed doctor. There were no import or collection errors; runtime code was unchanged.
- Task 1.3 RED: nine independent scanner-registry tests ran in 5.740s with 29 expected assertion failures across subcases and no errors. They exposed missing validation, the compiled v2 fallback, and v3 rejection; existing invalid-reference/target-poisoning checks remained meaningful. No test loaded an expected allow-list from production data.
- Task 1.4 RED: six hygiene tests ran in 0.769s with five expected assertion failures: four missing generated-skill ignore patterns and the 42 excluded tracked entries. Product-name preservation, forced-addition detection, and exclusion from mutation observers passed. Output exposed paths only, not session-file contents.
- Task 2.1 GREEN: all nine registry tests plus the real source-health regression passed (10 tests, 13.967s). The pinned v3 action metadata/docs were reread: Node 24 and reported unchanged inputs/outputs; no hosted scan or independent approval is inferred. The loader is local, bounded, strict, and independent of target/cwd/environment; existing workflow credential/shape conditions remain unchanged.
- Task 2.2: two new installation assertions first failed because the registry was absent from the payload (2 tests, 2.205s). After adding the single owned 0644 manifest entry, 10 focused POSIX/PowerShell installation cases passed in 26.016s, covering exact payload/state, no-op reruns, owned updates, local/unowned conflicts, source-unavailable execution, and missing installed data without traceback. Installer state format and copy logic were unchanged.
- Task 2.3: the real source doctor now returns `failed: false`, zero failures, 31 verified results, four warnings (including uncommitted tooling), one informational result, and two unverified hosted controls. Installed/source regressions pass; the external-inspector test verifies that the inspected target need not supply a registry. No warnings or external requirements were suppressed.
- Task 3.1: four hygiene-rule tests passed in 0.850s after adding only the four root-scoped generated-OpenSpec ignore patterns. Tests check actual Git ignore behavior for excluded and authored paths, forced-index detection, and exclusion from mutation observers. Compatibility documentation now explains the registry bundle and explicit local regeneration; no init/update or registration ran.
- Task 3.2: approved index-only removal completed for exactly 42 entries. Before/after path fingerprint was `d91d8e9c4a9a3cc1a50a924649f71059e0b363ea`; the fingerprint of their raw local-file blob hashes remained `c1ec519ef6bc82714f07b1f9377afa4e283ad7d1`. All 42 local files remain readable and byte-identical. The index contains only those 42 staged removals; implementation changes were not staged and no commit/history rewrite occurred.
- Task 3.3: all six hygiene tests passed in 1.082s. The complete index was reviewed: 193 entries remain, versus 235 initially, with all ten product skills and authored adapters/specs preserved. New runtime/test/planning additions remain untracked and are not included in that index count; no final release count is inferred. Existing cached Skills CLI 1.7.0 was found using `npx --no-install --offline skills --version`, without a package installation.
- Task 4.1: an owned local verification clone received the actual tracked delta plus the eight explicit runtime/test/planning additions. Its 201-entry candidate tree is `24147494009d5c6b77d15d338b3f34e5194e0e3a`, not an unchanged-HEAD export or a commit. Existing Skills CLI 1.7.0 / Node v26.13.0 ran `npx --no-install --offline skills add <clean-candidate> --list` with telemetry disabled and reported exactly the ten specified product names, no generated OpenSpec additions. Listing left the snapshot unchanged and installed no skills. Subsequent evidence-only edits are outside that recorded snapshot; it is not canonical committed proof.
- Task 4.2 Windows: `python -B -m unittest discover -s tests -v`, Python 3.15.2, completed 624 tests in 737.149s with zero failures/errors and 16 unrelated filesystem/POSIX-capability skips. New registry, source/installed doctor, ownership, and index-hygiene tests all executed. Bytecode writing was disabled and fixtures used approved temporary storage.
- Task 4.2 POSIX: `python3 -B tests/mutate.py` in WSL Ubuntu/Python 3.14.4 completed a clean 624-test baseline in 155.667s, zero failures/errors, 26 skips (unavailable PowerShell/ShellCheck and Windows-only branches). The runner reported 176/176 non-equivalent mutants killed and only the two documented equivalents (#70, #166). Expected failures in injected mutants are not baseline failures.
- Native ShellCheck 0.9.0 ran `shellcheck install.sh hooks/pre-push hooks/pre-push.sh` successfully. No tool installation or hosted CI/scanner execution occurred. After verification, all 42 preserved-file hashes still matched, and Git-normalized content for all eight changed implementation/test/documentation files matched the recorded clean discovery tree.
- Task 4.3 remains pending: no source-repository commit was authorized or created, and the clean snapshot's tree identity is not a committed candidate or canonical red/green proof.

### Critical Handoff

- Intent: [proposal.md](proposal.md). Requirements: [CI security](specs/ci-security/spec.md) and [repository hygiene](specs/repository-hygiene/spec.md). The Threat Note and rollback constraints above remain applicable.
- Implementation trace: Kilo used Git, Python unittest, the existing Node/Skills CLI cache, ShellCheck, WSL, and scoped file patches in the main foreground. No subagent/background work, dependency installation, agent registration, hosted execution, or source-repository commit occurred.
- Policy review track: independent reviewer identity and decision are pending. Evidence available for review includes upstream ref mapping, bounded inspector-owned parsing, unchanged workflow/credential checks, retained legacy structure, malformed-data failures, and target/cwd/environment poisoning resistance.
- Integration/hygiene review track: independent reviewer identity and decision are pending. Evidence includes source and installed doctor success, source-unavailable and local-conflict tests, exact staged removal inventory with preserved local hashes, the clean 201-file snapshot, and ten-name Skills listing. The existing mutation battery is not a claim of exhaustive new-registry mutation coverage.
- Human scope approval by Achmad Kurnianto is recorded above; it is not either independent review. Hosted scanning, branch protection, regulatory readiness, and canonical committed proof remain unverified. Later workstreams and the other active changes were not modified.
- Task 4.5: strict OpenSpec validation, staged and unstaged whitespace checks, and the local Critical evidence-section check passed; the latter reports attestation, not independent verification. Final scope inspection confirmed no changes to workflows, product skills/adapters, installers/hooks, durable specs, or other active changes. Git emitted only its configured LF-to-CRLF notices for edited text.
- Handoff: 14/15 tasks complete. Task 4.3 alone remains pending for an authorized committed candidate. HEAD is still `0ee9a1b426778aa4bd2cf45092bf37eb852d52a7`; only the 42 approved index removals are staged, and new implementation/test/planning content remains unstaged or untracked. Local copies are preserved; no source-repository commit, push, registration, hosted/settings change, or archive occurred.
