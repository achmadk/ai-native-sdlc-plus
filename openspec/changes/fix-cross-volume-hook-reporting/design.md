## Context

See [proposal.md](proposal.md) for motivation. This design is included because the repair sits in a Critical hook-inspection path and must distinguish diagnostic formatting from security and activation decisions.

The [recorded WS0 attempt](../fix-self-consistency/redgreen-proof.json) used baseline `0ee9a1b426778aa4bd2cf45092bf37eb852d52a7` and committed candidate `d6260c1f1fe34e6642de63cd9411cf0dc3b3bb01`, with two repetitions per phase. Temporary worktrees lived on `C:` while the shared Git hook directory lived on `D:`. Both candidate runs raised `ValueError` in `check_hook` when `os.path.relpath(target, root)` tried to create an impossible relative path.

`git rev-parse --git-path hooks/pre-push` is already the authority for the hook target. The crash occurs while formatting `shown`, before testing whether that target exists. Existing tests cover missing, owned, foreign, and non-executable hooks but do not cover this cross-volume display case.

The recorded run returned `NOT_GREEN`, not successful proof. Its temporary worktrees were cleaned up. This planning step does not edit doctor, alter the old committed candidate, or close WS0 task 4.3.

## Goals / Non-Goals

**Goals:** retain truthful hook diagnostics across valid Git worktree layouts; preserve the target and all status decisions; obtain a specific regression failure and native verification without hiding platform limitations.

**Non-Goals:** configuring hooks, moving the repository, forcing same-volume temporary directories as a product requirement, changing scanner/evidence policy, weakening tests, broad exception suppression, or starting WS1. No implementation or new commit is authorized by planning.

## Decisions

### 1. Separate display from access

Keep relative display when `os.path.relpath` can represent the Git-resolved target. When that formatting operation raises `ValueError` because no relative representation exists, display the resolved absolute target instead.

Scope recovery to this formatting operation. Do not catch all exceptions around `check_hook`, invent a relative path, rewrite the access target, or change `core.hooksPath`. File existence, executable permission, marker recognition, and Git lookup continue to use the same target as before.

Alternatives rejected: forcing temporary worktrees onto the source drive hides the defect; treating all formatting errors as successful hook verification changes security meaning; changing hook settings is outside a diagnostic repair.

### 2. Preserve outcomes and read-only behavior

The following outcomes remain unchanged after display recovery:

| Condition | Outcome |
|---|---|
| Git cannot establish the target or repository state | Unverified diagnostic |
| Hook target is absent | Warning, not traceback or verified activation |
| Target is non-executable where executable permissions apply | Warning |
| An unrelated hook occupies the target | Warning, not recognition as the toolkit hook |
| Executable toolkit marker is present | Existing advisory verified result |

Keep the no-hook-template case and same-volume formatting behavior intact. Spaces in valid paths must not alter target selection. Neither inspection nor its tests may activate user hooks or change the source repository's settings.

### 3. Test the failure mechanism and its real layout

Add portable tests that exercise a `ValueError` from the display operation while checking target preservation and the outcome table. Keep the mocked exception visibly distinct from native cross-volume execution; unrelated errors must not be swallowed by an overly broad catch.

Add native Windows path cases and a real linked-worktree regression when two approved, writable volumes are available. Use isolated test-owned repositories and temporary directories; do not reconfigure or move the user's repository. If that layout cannot be provisioned, report a specific capability skip while retaining portable coverage. On the current host, the failed canonical run already demonstrates that the cross-volume layout is real and relevant.

The test must fail on the current code for the path-reporting defect, not because a required tool or directory is missing. Verify structured CLI output remains available instead of an unhandled traceback.

### 4. Keep proof claims causally specific

`d6260c1` is immutable and contains the bug. Changing the working copy cannot make proof against that same commit green. A new committed candidate requires separate authorization.

There are two distinct verification claims: the Windows cross-volume reporting repair, and the earlier WS0 scanner consistency repair. The old WS0 baseline also contains the path bug, so a combined proof can retain a baseline error even after the candidate is fixed. Do not call that unrelated error valid scanner red evidence.

After a fixed committed candidate is available, capture a targeted Windows proof of this reporting repair. Re-run the required WS0 source/installed scanner proof on an appropriate supported host/layout where the baseline's red output is the scanner assertion, with the separate native cross-volume result retained. Record the platform and why the proofs are separate; do not omit the required tests or present one layout as proof of all layouts. Preserve the original failed receipt and leave WS0 task 4.3 pending until its stated criteria are actually met.

## Risks / Trade-offs

- Absolute display is longer than relative display -> use it only when relative formatting is unavailable; do not change the target.
- Broad exception handling could hide real failures -> catch only the expected display error and test unrelated-error behavior.
- A missing hook could accidentally become verified -> assert warning/status semantics independently of formatting.
- A simulated error could be overstated as native coverage -> retain a real linked-worktree case and label capability gaps explicitly.
- A baseline path error could masquerade as scanner proof -> keep reporting and scanner proofs separate and inspect their actual red reasons.

### Threat Note

Doctor inspects activation; it does not grant or alter it. Git's resolved target, marker checks, credential boundaries, and hosted-readiness distinction remain authoritative. A readable absolute path is diagnostic data, not permission to execute or configure a hook. No change may turn a formatting fallback into a bypass or a blanket green result.

## Verification and Migration Plan

1. After explicit apply authorization, record the baseline and classify `scripts/doctor.py` and `tests/test_doctor.py` as Critical.
2. Add focused portable/native regressions before the production edit and capture the expected reporting failure.
3. Implement the narrow display fallback, then run hook-inspection tests, the real cross-volume CLI case where available, and the full suite on available supported hosts. Record exact outcomes and skips.
4. Validate the change and review the diff for unchanged hook selection, status semantics, public command forms, and settings.
5. Only after separate committed-candidate authorization, produce the targeted native proof and resume WS0 proof as described above. Do not create commits or change old proof results merely to complete a checkbox.

No data, configuration, or dependency migration is required. If the repair regresses hook detection or read-only behavior, stop rollout and revert only the reviewed diagnostic/test change after authorization; do not compensate by altering hook settings or suppressing tests.

Independent source/security and verification reviews remain pending. Planning readiness is not either approval, hosted execution evidence, or successful WS0 proof.

## Implementation Evidence

- Task 1.1: explicit apply authorization was received for the reporting fix. Baseline is `d6260c1f1fe34e6642de63cd9411cf0dc3b3bb01`; initial changes were the new planning directory and the previously recorded WS0 failed attempt. The intended source/test/record paths classify Critical.
- The workspace parent on `D:` and approved temporary parent on `C:` exist and provide the two fixture volumes. The native test will verify actual provisionability. No hook configuration or repository relocation was performed.
- The old WS0 receipt was inspected and remains `NOT_GREEN`; its raw Git blob fingerprint is `241d065709f83cf04bc369c4cf92077ac47f4635`. It will not be overwritten or counted as successful proof.
- Task 1.2 RED: five focused tests ran in 0.037s with six expected assertion failures (four outcome-table cases and two native drive-letter cases), no collection errors. Same-volume relative display, unknown Git targets, and propagation of unrelated formatter exceptions already passed. Production code remained unchanged.
- Task 1.3 RED: the real linked-worktree CLI test ran on the approved D:/C: layout and failed its exit-zero assertion with the exact cross-volume `ValueError` (one test, 0.919s). The fixture's configuration and status were preserved, its worktree/repository were cleaned up, and source worktree registration remained unchanged. This was native execution, not the portable mocked-error case.
- Task 2.1 GREEN: the only runtime change catches `ValueError` around display formatting and falls back to the resolved target. All 13 focused reporting/native-worktree/existing-hook tests passed in 6.569s, with one unrelated POSIX-permission skip. The real cross-volume CLI emitted JSON, retained a warning for the absent hook, and preserved fixture configuration. Access-target and status assertions passed, including unrelated-exception propagation.
- Task 2.2: the complete doctor module passed 127 tests in 209.685s with one unrelated executable-permission skip. Native cross-volume execution ran, not skipped. Runtime diff review confirmed only the display fallback; hook dispatch, workflows, scanner policy, lane/evidence rules, and source-repository settings were unchanged.
- Task 3.1 Windows: `python -B -m unittest discover -s tests -v`, Python 3.15.2, completed 630 tests in 748.877s with zero failures/errors and 16 unrelated capability skips. Both the real cross-volume linked-worktree test and the native drive-letter test executed successfully. The run was in the main foreground with bytecode writing disabled and approved temporary storage.
- Task 3.1 POSIX: the same unittest discovery through WSL Ubuntu `python3 -B`, Python 3.14.4, completed 630 tests in 176.159s with zero failures/errors and 28 skips. These include the two new Windows-only cases (`native Windows cross-volume worktree` and `Windows drive-letter path semantics`) plus the existing PowerShell/ShellCheck and Windows-specific capability limits. Portable formatting-error and status-preservation tests executed; this is not a claim of native Windows coverage from POSIX.
- Task 3.2 remains pending. The repair is uncommitted and no new committed candidate or publishing action has been authorized. Local failing-first and cross-volume observations are not canonical committed proof, and the earlier WS0 `NOT_GREEN` receipt and pending status remain unchanged.

### Critical Handoff

- Intent and requirements: [proposal.md](proposal.md), the unchanged [toolchain-portability contract](../harden-sdlc-foundation/specs/toolchain-portability/spec.md), and [WS0 doctor consistency](../fix-self-consistency/specs/ci-security/spec.md). The threat and rollback constraints above remain in force.
- Source/security review track: independent reviewer and approval are pending. Evidence shows a display-only `ValueError` fallback, the same Git-resolved access target, unchanged permission/marker checks, truthful missing-hook warnings, and propagation of unrelated exceptions.
- Verification review track: independent reviewer and approval are pending. Evidence includes the specific assertion-based red results, native D:/C: linked-worktree execution, full Windows/POSIX suites, explicit skip limits, and fixture cleanup/configuration preservation. The old baseline's unrelated path error cannot stand in for scanner-failure proof.
- Trace and attribution: Kilo performed this repair directly using Git, scoped patches, Python unittest, OpenSpec, and WSL in the main foreground. No subagents, background execution, dependency installation, source-repository hook activation, hosted action, or fabricated approval was used.
- Task 3.3: strict OpenSpec validation and `git diff --check` passed, with only existing Git LF-to-CRLF notices. The local Critical evidence-section check passed as attestation, not independent verification. Hook/workflow/scanner/evidence surfaces outside the two implementation files are unchanged, and test-owned worktrees were cleaned up.
- Final status is 7/8 tasks complete; only task 3.2 remains pending for a newly authorized committed candidate and valid canonical proof. HEAD remains `d6260c1f1fe34e6642de63cd9411cf0dc3b3bb01`. The old WS0 receipt fingerprint remains `241d065709f83cf04bc369c4cf92077ac47f4635`; pre-existing WS0 evidence edits were preserved, not replaced. No source-repository commit, push, settings change, archive, or WS1 work occurred.

### Committed Verification Completion

- The user resumed remaining work after committing the repair as `06c2ab56d1f790f17203c586108c53112be563cd`. [Native canonical proof](redgreen-proof-06c2ab5-windows.json) reports `PASS` against baseline `d6260c1f1fe34e6642de63cd9411cf0dc3b3bb01`, with two repetitions. Each base run has the six expected reporting assertions and no test errors; each candidate run passes five tests with no skips. This covers the reporting contract and native drive-letter behavior, not a claim that the canonical temporary trees themselves span volumes.
- The same committed candidate separately passed `python -B -m unittest tests.test_doctor.CrossVolumeHookChecks -v` on the real D:/C: fixture (one test, 1.456s, no skips). This retains actual linked-worktree evidence instead of relying only on the portable exception test.
- Task 3.2 is complete and the change is 8/8. The authorized WS0 scanner proof is resumed separately on POSIX to avoid the unrelated baseline Windows error. The original WS0 `NOT_GREEN` receipt remains byte-identical (`241d065709f83cf04bc369c4cf92077ac47f4635`). No implementation, commit, publication, archive, or host setting was changed during this verification.
