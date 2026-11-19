## Why

The authorized WS0 proof against committed candidate `d6260c1f1fe34e6642de63cd9411cf0dc3b3bb01` returned `NOT_GREEN`: doctor crashes while displaying a hook path when a Windows worktree and its shared Git directory are on different volumes. A diagnostic-formatting failure must not prevent truthful local inspection or be hidden by weakening the proof tests.

## What Changes

- Make hook-path display tolerate the absence of a relative path between Windows volumes, while retaining normal relative display where it is valid.
- Preserve Git's resolved hook target for all file, permission, marker, and activation checks. Keep existing warning, verified, and unverified outcomes; do not configure or execute hooks to avoid the failure.
- Add focused regressions for cross-volume reporting, same-volume behavior, spaces in paths, and unchanged hook-status decisions. Exercise a real linked worktree across approved volumes when available, with a stated capability limit otherwise.
- Preserve the failed WS0 receipt. A later authorized committed fix must pass a new proof run before WS0's pending proof task can be closed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This restores the existing [portable-verification contract](../harden-sdlc-foundation/specs/toolchain-portability/spec.md) and [source/installed doctor consistency](../fix-self-consistency/specs/ci-security/spec.md). The change explicitly declares `skip_specs: true` rather than inventing a new requirement for an implementation defect.

## Impact

- Future implementation is limited to `scripts/doctor.py` and focused tests in `tests/test_doctor.py`, plus this change's records.
- The doctor path is a Critical boundary. Failing-first evidence, preservation of status semantics, and explicit review/rollback notes are required even though the repair is small.
- Public CLI forms, Python 3.8 support, scanner policy, evidence checks, hook dispatch, and repository settings remain unchanged. There is no new dependency or path-layout requirement for users.
- WS0 stays at 14/15, with its `NOT_GREEN` attempt recorded. WS1 planning is postponed by the user's decision; this proposal does not authorize implementation, commits, publishing, or changes to another workstream.
