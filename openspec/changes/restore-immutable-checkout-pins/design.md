## Context

See [proposal.md](proposal.md) for the motivation and scope. This design is included because action references select executable code at the CI enforcement boundary; provenance, failure propagation, and rollback need explicit treatment even for a small patch.

Observed at baseline `d5a6322495f1c7e6661df2b4484b424f1a29ba09`:

- `.github/workflows/sdlc-gate.yml` has two `actions/checkout@v7.0.1` references, at the trusted-base and candidate-head steps.
- `.github/workflows/gitleaks.yml` already uses `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` with a v7.0.1 comment.
- The workflow contract test requires every evidence/scanner action reference to match `^[^@]+@[0-9a-f]{40}$`. Its current per-workflow subtest stops at the first bad reference, so one reported failure masks the second checkout occurrence.
- On 2026-11-08, `git ls-remote https://github.com/actions/checkout.git "refs/tags/v7.0.1" "refs/tags/v7.0.1^{}"` returned `3d3c42e5aac5ba805825da76410c181273ba90b1` for the release tag. Upstream resolution confirms the candidate pin, not a human approval or a hosted execution result.
- Exploration reproduced the focused test failure without modifying the workflow. The supplied CI report ran 602 tests with one failure and seven skips; it is a reported baseline, not a green result for this change.

The [existing CI-security contract](../harden-sdlc-foundation/specs/ci-security/spec.md) already specifies immutable actions, non-persisted credentials, isolated trusted-base execution, and fail-closed behavior. No requirements change, so this change declares `skip_specs: true` instead of duplicating the other active change's delta.

## Goals / Non-Goals

**Goals:**

- Replace both mutable references with the verified commit for the already-selected release.
- Make every offending action visible in test diagnostics without changing the set of references the test accepts.
- Produce a narrowly reviewable Critical fix with a specific failing-first result and a verified green result.

**Non-Goals:**

- No checkout-version upgrade or downgrade, scanner change, matrix standardization, dependency installation, or production Python change.
- No test suppression, weaker pin validation, new runtime exceptions, or changes to branch-protection policy.
- No implementation during planning. Later apply authorization does not by itself authorize commits, pushes, hosted pilots, or repository-setting changes.

## Decisions

### 1. Preserve v7.0.1 and pin its verified commit

Use `3d3c42e5aac5ba805825da76410c181273ba90b1` for both evidence checkout actions and retain `v7.0.1` only as a human-readable comment. The obsolete TODO text is removed when the pins are implemented.

Reconfirm upstream provenance before editing. If the tag resolves differently, stop for review rather than silently selecting a different commit. A 40-character string alone is not evidence that it belongs to the intended upstream release.

Alternatives rejected: retaining the mutable tag, shortening the SHA, downgrading to the older v4 pin still present in some unrelated CI jobs, or changing the assertion to accept release tags. None is needed to repair the stated regression.

### 2. Preserve the checkout and execution boundary

The workflow diff is limited to the two action references and their version comments. Review these invariants explicitly:

| Area | Unchanged behavior |
|---|---|
| Trusted tooling | Checkout `github.event.pull_request.base.sha` into `trusted` |
| Candidate | Checkout `github.event.pull_request.head.sha` into `change`, with `fetch-depth: 0` |
| Credentials | `persist-credentials: false` for both checkouts; `contents: read` permission |
| Evidence execution | Isolated `python3 -I` invocation from trusted tooling, trusted configuration, explicit base/head and event payload |
| Scheduling | Existing pull-request event types, concurrency, five-minute timeout, and `evidence` job identity |
| Failure behavior | No new conditions, ignored failures, success fallbacks, or privileged events |

There is no reason to edit the already-pinned scanner or other workflows. Their differing checkout versions are outside this repair.

### 3. Improve reporting, not the security policy

In `test_all_enforcement_actions_have_full_immutable_pins`, retain the existing full-SHA regex, nonempty-action assertion, and coverage of both enforcement workflows. Add action-granular subtest identification so the workflow and action occurrence are visible and one failure does not prevent checking later references.

This supplies a meaningful test change without hard-coding a permanent release allow-list or introducing a new acceptance rule. Run the improved test against the unchanged workflow first; both tag-based checkout occurrences must be reported as assertion failures. A collection error or missing dependency is not the intended red result.

### 4. Separate planning, execution evidence, and approval

The proposal records intent, while the existing CI-security spec supplies the unchanged requirement. This design carries the threat and rollback notes. Do not reinterpret the lack of a new delta as a lower-risk implementation lane.

Local test output, upstream tag resolution, hosted job results, and reviewer approvals are different evidence. Record each only after it exists. Preserve the other active change's artifacts and pending tasks; if that change is archived, follow its requirement into the main specification rather than recreating it here.

## Risks / Trade-offs

- A tag could move between investigation and implementation -> retain the proposed SHA as the reviewed target and stop on a changed upstream mapping.
- Only one checkout could be repaired -> report every action occurrence and verify both checkout references in the final diff.
- A valid-looking SHA could identify unintended code -> compare the exact upstream release mapping, not just the regex or a version comment.
- Pin editing could accidentally alter trust separation or credentials -> keep the diff to references/comments and verify the invariant table and existing workflow contracts.
- A green unit test cannot prove that GitHub fetched and executed the action -> distinguish local results from an actual authorized CI run.
- Action-level subtests change failure reporting -> preserve all assertions and use the full test suite to check for unrelated regressions.

### Threat Note

A movable action tag permits upstream code to change without a corresponding repository diff. The selected action runs with checkout access and the job's read-only repository token, so immutable provenance matters even without write permissions. The repair must not introduce broader credentials, persist the checkout token, execute candidate code as trusted tooling, or weaken failure propagation. Commit pinning controls which code is selected; it does not certify that code as harmless.

## Verification Plan

1. Re-run lane classification for the intended workflow/test paths. The implementation must remain Critical.
2. Before the workflow edit, update only action-level test diagnostics and run `python -B -m unittest discover -s tests -p test_ci_security.py -k test_all_enforcement_actions_have_full_immutable_pins -v`. Preserve the expected failures for both mutable checkout references.
3. After the repair, run the same focused command, then `python -B -m unittest discover -s tests -p test_ci_security.py -v` to cover adjacent trust-boundary contracts.
4. Run the reported CI command, `python -m unittest discover -s tests -v`, with bytecode writing disabled in the process environment. Record actual platform, count, skips, and outcome. Do not represent an unavailable platform or hosted job as passed.
5. Once an explicitly authorized committed candidate exists, use `scripts/redgreen.py` against the recorded baseline and candidate, selecting the focused pin contract. Its red output must be the expected invalid-pin assertion. If only uncommitted work exists, keep committed proof pending rather than creating commits or fabricating revision evidence.
6. Validate this change, inspect the final diff, and run the applicable local evidence check using only collected evidence. A local `--present` result is attestation, not independent verification.

## Migration Plan

No application or data migration is needed. After explicit apply authorization, prepare the local patch and passing tests, then present the evidence for review. A later authorized PR/CI run should show successful action resolution for both checkouts and unchanged execution of the `evidence` check; scanner behavior and required-check settings are not modified by this change.

Stop rollout if action resolution, checkout behavior, or evidence execution regresses. Do not revert to a release tag as the recovery path. Any rollback to a previous checkout release must use an independently reviewed immutable commit, update both references and comments consistently, and rerun the same contracts. No such rollback or hosted setting change is pre-authorized by this plan.

Two-reviewer handoff is pending:

- Supply-chain reviewer: verify upstream provenance, both pins, version preservation, and unchanged credential/trust boundaries.
- Verification reviewer: verify the specific red result, green contracts/full-suite result, absence of test weakening, rollback constraints, and the distinction between local and hosted evidence.

Record actual reviewer identities, findings, and decisions only when supplied. Planning completion is not either reviewer's approval.

## Implementation Record

- Apply was explicitly requested on 2026-11-08. The unfixed baseline is `d5a6322495f1c7e6661df2b4484b424f1a29ba09`; initial status contained only this change's untracked planning directory.
- Task 1.1: the specified workflow/test path classification returned Critical. The design/task tracking paths were also classified before editing. Upstream `git ls-remote` reconfirmed v7.0.1 at `3d3c42e5aac5ba805825da76410c181273ba90b1`; both gate references are still mutable tags, so the observed scope matches the plan.
- The declared specification skip remains in place. The existing CI-security requirement was reread; no requirement, other active change, hosted setting, or repository configuration is being changed.
- Task 1.2 RED: after adding occurrence/action subtest labels, the specified focused command ran one test in 0.006s and reported two assertion failures: occurrences 1 and 2 both referenced `actions/checkout@v7.0.1` in `sdlc-gate.yml`. There were no collection or environment errors. The workflow had not yet been edited, and the original regex, nonempty-action assertion, and scanner coverage were retained.
- Task 2.1 GREEN: both references now use `3d3c42e5aac5ba805825da76410c181273ba90b1` with v7.0.1 comments. The same focused command passed one test in 0.001s. The workflow diff contains exactly the two reference/comment replacements; no checkout parameter or enforcement setting changed.
- Task 2.2: all 16 tests in `test_ci_security.py` passed in 10.589s, with no skips or errors. The invariant table is unchanged: trusted base and candidate head refs/paths, full candidate history, read-only non-persisted credentials, events, concurrency, timeout, job identity, and isolated fail-closed command remain as before. A targeted `git diff --exit-code` confirmed the scanner, other workflows, production scripts, installers, and hooks are unchanged. No repository-setting mutation was performed.
- Task 3.1: `python -m unittest discover -s tests -v` completed in the main foreground on Windows with Python 3.15.2, `PYTHONDONTWRITEBYTECODE=1`, and an approved temporary fixture directory. Result: 602 tests in 2149.010s, zero failures/errors, `OK (skipped=16)`. This is local execution evidence, not a hosted CI result.
- Full-suite skips: file-symlink capability (4), directory-symlink capability (2), POSIX executable-permission checks (2), unavailable POSIX pseudo-terminal (1), fd-based removal (1), and unsupported literal filenames (6: `source\\n.py` twice, plus `[literal]*.md`, `::error::x.md`, ` literal[1]*.md`, and `:(exclude)tests`). None concerns checkout pin validation; all CI security contracts executed successfully.
- Task 3.2 remains pending. The workflow fix is uncommitted, and no commit was requested or created. Failing-first local observations above are not presented as canonical committed red/green proof. Hosted action resolution, other interpreter/platform CI jobs, and human approvals are also unverified in this apply run.

### Critical Handoff Evidence

- Intent: [proposal.md](proposal.md), preserving v7.0.1 while restoring immutable action selection.
- Specification: the unchanged [CI-security requirement](../harden-sdlc-foundation/specs/ci-security/spec.md), particularly immutable enforcement actions and trusted-base execution.
- Threat and rollback: the Threat Note and Migration Plan above remain applicable. No recovery path authorizes a mutable action reference or weakened enforcement.
- Test evidence: action-granular red assertions for both original tags, the passing focused contract, 16 passing adjacent security tests, and the complete 602-test local result are recorded above.
- Supply-chain review track: independent human reviewer and decision are pending. Available observations are the matching upstream SHA, unchanged release, both pinned occurrences, and unchanged checkout/credential boundaries.
- Verification review track: independent human reviewer and decision are pending. Available observations are the specific assertion-based red, unchanged acceptance regex, passing local verification, explicit platform skips, and outstanding committed/hosted evidence.
- Trace: Kilo used the OpenSpec CLI, Git provenance/diff inspection, Python unittest, and targeted patches. No subagents, background verification, new runtime dependencies, or hosted actions were used in this apply. The rejected alternatives remain tag acceptance, abbreviated or unverified pins, unrelated version changes, and security-test suppression.
- Attribution: assisted by Kilo. These implementation notes are not either independent reviewer's approval; no reviewer identity or approval date has been invented.
- Task 3.4: strict OpenSpec validation and `git diff --check` passed. Git emitted only its configured LF-to-CRLF notices, not whitespace errors. The local Critical `--present` check accepted the collected intent/spec/threat/test/trace/review/rollout sections as attested, not independently verified. Final status contains only the two intended implementation files and this change's artifacts; the specification skip remains declared.
- Handoff status: 7/8 tasks complete. Only task 3.2 remains pending for an explicitly authorized committed candidate and canonical red/green proof. The local CI test regression is fixed; no source-repository commit, push, hosted run, protection update, or archive was performed.
