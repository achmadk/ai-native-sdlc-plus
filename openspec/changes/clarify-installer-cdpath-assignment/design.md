## Context

See [proposal.md](proposal.md) for the motivation. This design is included because a misleading fix to the lint warning could weaken source selection in a Critical installer entry point, and because the required lint tool was unavailable locally during planning.

Observed at clean baseline `a00d6f58a62c30944bcee61bac9e8840ff991d03`:

- `install.sh` computes its source directory inside command substitution, using an empty `CDPATH` assignment before `cd`, quoted `dirname` input, and `pwd -P`.
- The script uses POSIX `sh`, validates Python 3.8 or newer, delegates filesystem changes to `scripts/install.py`, and propagates failure. Those choices are unchanged.
- `.github/workflows/ci.yml` already runs `shellcheck install.sh hooks/pre-push hooks/pre-push.sh`. The user supplied an SC1007 failure at the source-resolution line.
- `tests/test_install.py` already owns isolated source/target fixtures, uses shared shell discovery, and checks installation from an unrelated directory with spaces in paths. Its normal launcher invocation uses an absolute source path; no explicit `CDPATH` case was found.
- ShellCheck was unavailable in the local WSL environment during exploration. No local lint success or failure reproduction is claimed. The [SC1007 guidance](https://www.shellcheck.net/wiki/SC1007) confirms that an intentionally empty assignment should be quoted explicitly.

The [existing installation requirement](../harden-sdlc-foundation/specs/toolkit-installation/spec.md) governs source-relative lookup and explicit failure handling. Requirements do not change, so specifications are explicitly skipped rather than duplicated.

## Goals / Non-Goals

**Goals:**

- Make the empty assignment unambiguous to ShellCheck while preserving its shell behavior.
- Protect source lookup against nonempty caller `CDPATH` values and make actual lint coverage distinguishable from missing-tool skips.

**Non-Goals:**

- No general shell refactor, warning suppression, severity reduction, or change to the CI command.
- No modification to hooks, PowerShell, the shared Python installer, runtime requirements, ownership rules, or managed LF behavior.
- No automatic tool installation, repository-setting change, commit, push, or hosted execution. Planning itself does not authorize implementation.

## Decisions

### 1. Quote only the empty assignment value

Use an explicitly quoted empty value, `CDPATH=''`, immediately before the existing `cd` command. Retain the separating space, command-substitution scope, operand quoting, `pwd -P`, and `|| exit 1`.

The old spelling already empties `CDPATH`; this is a lint/intent clarification, not a change to the resolved directory. Removing the assignment could allow inherited search paths or `cd` output to affect `SOURCE`. Removing the separating space would instead assign the word `cd` and change command parsing. Global environment changes, a different path-resolution utility, and disabling SC1007 are unnecessary alternatives and are excluded.

### 2. Test lint with the real lint tool

Add a small standalone unittest in `tests/test_install.py` that runs the existing three-file ShellCheck command and asserts successful completion, retaining diagnostics on failure. Detect the tool before execution; an unavailable tool must produce an explicit skip reason rather than a fabricated successful process result.

That optional unittest does not replace or weaken the mandatory CI ShellCheck step. Before the launcher edit, the new lint test must be demonstrated to fail on SC1007 using an available, authorized ShellCheck installation. A skipped test, a missing executable, or a Python collection error is not the intended red result. After the edit, the same lint test and the exact CI command must pass without new suppressions.

Record the actual ShellCheck version and host. If no authorized execution environment is available, stop that verification path and ask separately about access or installation; do not silently waive the lint requirement. The supplied CI diagnostic remains reported evidence until a matching run is captured.

### 3. Keep the behavioral preservation test independent of ShellCheck

Add a POSIX-launcher case using the existing temporary installation fixture, so it can run whenever the supported shell is available even if ShellCheck is absent.

- Invoke the real copied launcher by a relative path from the fixture's parent directory, retaining spaces in source and target names. Its directory operand must not start with `/`, `./`, or `../`, since those would avoid the relevant `CDPATH` search behavior.
- Set a relative `CDPATH` entry such as `shadow`, with a matching shadow source-directory name under that entry. A relative entry avoids Windows drive-letter separators in Git-shell fixtures.
- Include a fixture-only control demonstrating that ordinary directory lookup can select the shadow under this environment. This prevents a false-positive test whose paths never exercise `CDPATH`.
- Assert successful installation from the real distribution, the expected payload/state, and no execution of a sentinel shadow installer. Do not relax the existing non-destructive assertions or bypass the production launcher with a mocked result.

The behavioral test is expected to pass on the original valid expression and on the clarified expression. Record it as preservation coverage, not as the failing-first proof for SC1007.

## Risks / Trade-offs

- A quick fix could stop clearing `CDPATH` -> restrict the source diff to the empty-value spelling and exercise a shadow-directory case.
- A fixture could use an absolute or dot-prefixed directory and never trigger `CDPATH` -> use a bare relative source directory and verify the shadow control.
- Unit tests could pass while lint was skipped -> require a separate, successful execution of the exact ShellCheck command before closing lint verification.
- A local tool or hosted runner may be unavailable -> record the limitation and wait for explicit authorization instead of installing tools or changing CI automatically.
- Additional lint findings could exceed this repair -> stop and surface the added scope instead of suppressing warnings or expanding the patch silently.

### Threat Note

The source directory determines which Python installer is executed. Caller-controlled directory-search configuration must not redirect it to another distribution or contaminate the captured path. The change must retain command-local empty `CDPATH`, quoted paths, the command-substitution boundary, and failure propagation. The test sentinel is isolated fixture data, not a reason to execute arbitrary repository code during verification.

## Verification Plan

1. Reconfirm the Critical lane and record the actual baseline and lint-tool availability before implementation.
2. Add the two focused regressions before editing `install.sh`. Capture the real SC1007 failure where ShellCheck is available and the passing source-resolution preservation case.
3. Make only the empty-assignment clarification. Run `shellcheck install.sh hooks/pre-push hooks/pre-push.sh` unchanged and require exit zero with no SC1007 suppression.
4. Run the focused regressions, the existing installer test module, and `python -m unittest discover -s tests -v` on available supported hosts. Record counts, skips, and exact outcomes; a clean syntax parse or unit result does not substitute for ShellCheck.
5. Use `scripts/redgreen.py` for canonical revision-bound lint-test proof only after an explicitly authorized committed candidate and the required tool are available. Keep this proof pending when either prerequisite is absent; a skipped lint test is never valid proof.
6. Inspect the final diff and validate this change. Link the existing installation specification, preserve the declared spec skip, and record only evidence actually obtained.

## Migration Plan

No data or configuration migration is required. After explicit apply authorization, verify the lint and installation behavior before presenting the patch for review. The shell file remains under existing LF management, and installed-file hashes continue to be handled by the shared installer without a manifest-format change.

If behavior regresses, hold rollout and investigate the isolated launcher change. An authorized rollback to the original expression must explicitly mark SC1007 as unresolved; do not claim success by removing `CDPATH` isolation, suppressing the warning, or bypassing CI.

Two independent review tracks remain pending: source-resolution semantics and scope preservation; and verification quality, real ShellCheck red/green evidence, capability-skip reporting, and rollback handling. Record reviewer identities and approval only when supplied. No hosted result or human approval is implied by completed planning artifacts.

## Implementation Record

- Apply was explicitly requested on 2026-11-08. The unfixed revision is `a00d6f58a62c30944bcee61bac9e8840ff991d03`; initial status contained only this change's untracked planning directory. The installer expression still matched the reported SC1007 input.
- Task 1.1: `python -B scripts/lane.py --paths install.sh tests/test_install.py` confirmed Critical. The evidence/tracking paths were separately classified before editing.
- Unlike the planning-time WSL environment, native Windows now has an existing `C:\ProgramData\chocolatey\bin\shellcheck.exe`. Running `shellcheck --version` succeeded and reported 0.9.0. Shared discovery selected `C:\Program Files\Git\usr\bin\sh.exe`. No tool installation or host-setting change was performed by this apply.
- Task 1.2 RED: `python -B -m unittest tests.test_install.ShellLint -v` ran one test in 0.134s and failed its exit-zero assertion with ShellCheck's SC1007 diagnostic on `install.sh:6`. The launcher was unchanged. This was a real lint assertion failure, not collection failure, executable lookup failure, or a skipped check.
- Task 1.3 preservation baseline: the new `POSIXInstallation.test_relative_launcher_ignores_inherited_cdpath` passed against the unchanged launcher in 1.120s. Its unisolated control selected the shadow directory under `CDPATH=shadow`; the real relative launcher installed the expected files/state from the true source, did not execute the shadow sentinel, and preserved the shadow and target Git metadata. This passing test is not the SC1007 red proof.
- Task 2.1 GREEN: the launcher diff changes only `CDPATH=` to `CDPATH=''`. The exact command `shellcheck install.sh hooks/pre-push hooks/pre-push.sh` returned zero with no diagnostics under ShellCheck 0.9.0. The lint and source-resolution regressions then both passed in 3.347s. No warning suppression, argument change, interpreter change, or hook/workflow edit was introduced.
- Task 2.2 Windows verification, Python 3.15.2: `python -m unittest discover -s tests -p test_install.py -v` ran 58 tests in 128.437s with zero failures/errors and three filesystem-capability skips. The full `python -m unittest discover -s tests -v` run completed 604 tests in 478.211s, zero failures/errors, 16 platform-capability skips. ShellCheck actually executed and passed in both runs. Verification ran in the main foreground with bytecode writing disabled and owned temporary fixtures.
- Windows full-suite skips were file-symlink capability (4), directory-symlink capability (2), POSIX executable-permission checks (2), unsupported literal filenames (6), unavailable POSIX pseudo-terminal (1), and fd-based removal (1). None was a lint skip; all native PowerShell installation cases, installed helper checks, and Git-dispatched hook cases passed.
- Task 2.2 POSIX verification, WSL Ubuntu with Python 3.14.4: the installer module ran 58 tests in 51.224s with zero failures/errors and 20 skips (18 unavailable PowerShell cases, one Windows junction case, and unavailable ShellCheck). The full suite ran 604 tests in 98.440s with zero failures/errors and 25 skips: those 20 plus two Windows command-line cases, two Windows junction-support cases, and one Windows command-fixture case. The CDPATH shadow-control regression passed on POSIX. Commands used the same unittest arguments through `python3`, with `PYTHONDONTWRITEBYTECODE=1`.
- The POSIX ShellCheck skip is not claimed as lint success. The actual lint result is the completed native ShellCheck 0.9.0 execution recorded above. No tool installation was needed, and no hosted CI result is claimed.
- Task 3.1 remains pending: this fix is uncommitted, and no repository commit was authorized or created. The observed local SC1007 red and subsequent green results are not presented as canonical revision-bound proof.

### Critical Handoff Evidence

- Intent and specification: [proposal.md](proposal.md) describes the lint-only source clarification; the unchanged [toolkit-installation contract](../harden-sdlc-foundation/specs/toolkit-installation/spec.md) supplies the source-relative and non-destructive behavior requirements. The Threat Note and Migration Plan above remain applicable.
- Source-resolution review track: independent human reviewer and approval are pending. Available observations are the one-line empty-value spelling change, unchanged command scope/quoting/failure propagation, and a real shadow-directory control that verifies the installer selects the true distribution without executing the sentinel.
- Verification review track: independent human reviewer and approval are pending. Available observations are the real ShellCheck 0.9.0 SC1007 failure before the edit, successful identical lint execution afterward, passing preservation coverage on both hosts, and the recorded full-suite results and skip limits.
- Trace and attribution: Kilo performed the implementation and verification directly in the main foreground using Git, OpenSpec, Python unittest, existing native ShellCheck, and WSL. Alternatives rejected were removing `CDPATH` isolation, changing parsing to `CDPATH=cd`, suppressing SC1007, or treating a missing linter as a successful result. No runtime dependency was installed, no hosted execution was performed, and no human approval was fabricated.
- Task 3.3: strict OpenSpec validation and `git diff --check` passed. Git reported only its configured LF-to-CRLF notice for the Python test file, not whitespace errors. The local Critical evidence check accepted the collected sections as attested, not independently verified. Final changes are limited to `install.sh`, `tests/test_install.py`, and this change's artifacts; the specification skip remains declared.
- Handoff status: 7/8 tasks complete. Only task 3.1 remains pending for an explicitly authorized committed candidate and canonical lint-test proof. HEAD remains `a00d6f58a62c30944bcee61bac9e8840ff991d03`; no source-repository commit, push, workflow edit, settings change, or archive was performed.
