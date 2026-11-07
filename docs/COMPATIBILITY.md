# COMPATIBILITY / versioning policy

Versioning applies to skills, scripts, templates, and adapters. Lane-config `version: 1` identifies the parser format, not a policy revision counter. Do not increment it for an ordinary rule edit. Review rule changes as Critical and identify the evaluated policy through its committed revision.

- Minor: new skill, new template field (optional), new adapter.
- Patch: wording, fixes, eval data.
- Major: lane semantics change, required-evidence change, dropped adapter.

The core runtime floor is Python 3.8 and uses only the standard library. Git is required for revision-aware checks; authenticated `gh` is needed only for explicit hosted inspection. Workflow actions use full immutable SHAs; comments identify their human-readable versions.

## Configured CI coverage

| Platform | Python | Suites |
|---|---|---|
| Linux | 3.8, 3.10, 3.12, 3.13 | Full suite, including the separate 3.8 compatibility job |
| macOS | 3.12 | Full suite |
| Windows | 3.8, 3.13 | Focused PowerShell installation, filesystem-safety, and actual Git-dispatch tests |
| Windows | 3.8, 3.13 | Separate full-suite job with verbose verdicts and skip reasons |

Both Windows jobs propagate the Python exit status. The full-suite job has a 45-minute timeout, allowing margin over a measured 29-minute local run. A configured job is not an execution result: these CI versions still require their own successful runs against the candidate revision.

Local verification for this change uses Windows with Python 3.15.2, Git 2.45.1.windows.1, and PowerShell 7.6.9, plus WSL Ubuntu with Python 3.14.4. Completed run counts and individual skip reasons are recorded in the [change's verification record](../openspec/changes/harden-sdlc-foundation/design.md). Local runs on these versions do not attest the configured Python 3.8/3.13 jobs or macOS.

Completed foreground runs on 2026-11-07:

| Check | Result |
|---|---|
| Native Windows full suite | 601 tests, zero failures/errors, 16 capability skips |
| WSL Ubuntu full suite | 601 tests, zero failures/errors, 24 Windows-only skips |
| POSIX mutation battery | 176/176 non-equivalent mutants killed; two documented equivalent survivors |

All 18 native PowerShell installer cases and the Git-dispatched Windows hook cases passed. Skips remain coverage limits, not passing executions of those platform-specific cases.

## Test capabilities

From a Windows toolkit checkout, run `python -B -m unittest discover -s tests -v`. This runs the lane, evidence, brief/spec, doctor, generic-CI, installer, hook, red/green, optional-tool, and template suites. The self-tests are not part of the installed payload.

- Shell fixtures discover Git for Windows' own shell before considering PATH. They avoid WSL launchers and preserve the fixture's PATH precedence; generic-CI fixtures bind `python3` to the interpreter running the tests.
- Symlink tests probe file or directory link creation. Missing privilege or filesystem support produces a named skip. Windows junction cases run natively without requiring symlink privilege.
- Tests that need POSIX executable permissions, pseudo-terminals, or fd-based directory removal probe those capabilities. Git-index executable/symlink metadata tests still run on Windows.
- NTFS cannot represent some control-character, wildcard, and colon filenames. Physical fixtures skip only after a filename probe; filesystem-free path/classification and raw Git-record tests retain the assertions, including literal pathspec and diagnostic-sanitization coverage.
- Native command doubles use the Windows .NET Framework C# compiler already on the host. A missing compiler or an Application Control denial produces an explicit capability skip, not a clean remote-check result. Tests do not install a compiler or change security policy. Missing-CLI, offline, and non-GitHub cases run without creating a command double.
- PowerShell absence skips only its invocation cases. Windows command-line and junction cases are explicitly Windows-only. POSIX results cannot stand in for those native branches.

Temporary fixtures remove read-only Git objects and unlink junctions without traversing their targets. Red/green cleanup checks use per-test scratch directories so concurrent mutation runs cannot create false cleanup failures.

Foundation behavior tightens deliberately: install conflicts return nonzero without overwriting local work; path-only inspection cannot grant a CI documentation exemption; local evidence must be tracked at the evaluated revision; nested security and control paths receive higher lanes. Existing config format 1 and helper invocation forms remain supported. Root helper entry points delegate to the existing skill-local implementations.

The installer preserves `.gitattributes` conflicts and maintains `.sdlc-install.json` ownership state. A pre-manifest installation has no implied ownership: identical files are retained, differing files require explicit reconciliation. Do not claim an automatic rollback or uninstall interface; neither is provided by this change.
