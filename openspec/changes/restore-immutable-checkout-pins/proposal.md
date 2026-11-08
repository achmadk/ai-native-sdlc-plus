## Why

The evidence workflow uses `actions/checkout@v7.0.1` for both its trusted-base and candidate-head checkouts, causing `test_all_enforcement_actions_have_full_immutable_pins` to fail. Release tags can move, so the workflow must restore the existing immutable-action contract rather than relax the test.

## What Changes

- Pin both checkout steps in `.github/workflows/sdlc-gate.yml` to the upstream-verified v7.0.1 commit `3d3c42e5aac5ba805825da76410c181273ba90b1`, already used by `.github/workflows/gitleaks.yml`.
- Replace the obsolete pinning TODO comments with the human-readable version comment. Preserve checkout refs and paths, full candidate history, disabled credential persistence, read-only permissions, PR events, timeout, job identity, and isolated fail-closed execution.
- Improve action-specific failure diagnostics in the existing workflow contract test so both invalid references are visible. Keep its full-SHA assertion and scanner coverage intact.
- Collect failing-first and green verification evidence for the Critical implementation change, with review and rollback notes. Planning does not authorize implementation, commits, pushes, or hosted configuration changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is an implementation repair, not a change to requirements. `.openspec.yaml` explicitly sets `skip_specs: true`; no delta spec will be created.

The governing requirement is [Immutable enforcement actions](../harden-sdlc-foundation/specs/ci-security/spec.md) in the existing `harden-sdlc-foundation` change. Reusing that unchanged contract avoids duplicating its not-yet-archived `ci-security` capability or altering the other change's artifacts and task status.

## Impact

- Future implementation is confined to `.github/workflows/sdlc-gate.yml` and the relevant diagnostics in `tests/test_ci_security.py`.
- The workflow path classifies Critical. The small patch still requires the repository's intent, specification reference, threat note, failing-first verification, trace, two-reviewer notes, and rollout/rollback evidence.
- The intended checkout release remains v7.0.1. This is not a version upgrade, a new dependency, an API change, or a modification to scanner behavior.
- No changes are planned to `gitleaks.yml`, other CI workflows, Dependabot configuration, production Python, installer/hook behavior, credentials, repository protection settings, or unrelated pending work.
