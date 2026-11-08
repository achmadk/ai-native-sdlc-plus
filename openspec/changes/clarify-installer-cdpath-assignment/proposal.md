## Why

The CI ShellCheck command reports SC1007 for the intentional empty `CDPATH` assignment in `install.sh`, so lint fails even though the shell expression is valid. Making that empty value explicit must preserve source-relative installation and prevent an inherited `CDPATH` from influencing source lookup.

## What Changes

- Quote the empty value in the existing command-local `CDPATH` assignment on the source-resolution line. Keep `cd`, argument quoting, physical-path resolution, and failure propagation unchanged.
- Add focused coverage in `tests/test_install.py`: an actual ShellCheck regression when the tool is available, and a source-resolution case with nonempty `CDPATH`, a relative launcher path, and a shadow directory. Preserve existing installer assertions and shared fixture utilities.
- Keep `shellcheck install.sh hooks/pre-push hooks/pre-push.sh` as the acceptance command. Missing ShellCheck must be reported as unavailable, not treated as a clean lint result or hidden behind a warning suppression.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The [existing toolkit-installation contract](../harden-sdlc-foundation/specs/toolkit-installation/spec.md) already requires source-relative lookup, explicit failures, and non-destructive installation. This change preserves those requirements and declares `skip_specs: true` rather than creating a duplicate delta.

## Impact

- Future implementation is limited to `install.sh` and focused regressions in `tests/test_install.py`; this proposal does not authorize implementation.
- `install.sh` is a built-in Critical boundary. The repair needs the existing specification reference, failing-first lint evidence, threat/rollback notes, and accurate reviewer status despite its small source diff.
- There is no new runtime dependency, API, installer option, or payload format. ShellCheck is already used by CI; local test coverage may detect its availability but must not install it automatically.
- Hooks, PowerShell installation, the shared Python installer, workflows, lint severity, Git settings, hosted controls, and other changes remain outside the implementation scope.
