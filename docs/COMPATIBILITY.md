# COMPATIBILITY / versioning policy

Versioning applies to skills, scripts, templates, and adapters. Lane-config `version: 1` identifies the parser format, not a policy revision counter. Do not increment it for an ordinary rule edit. Review rule changes as Critical and identify the evaluated policy through its committed revision.

- Minor: new skill, new template field (optional), new adapter.
- Patch: wording, fixes, eval data.
- Major: lane semantics change, required-evidence change, dropped adapter.

The core runtime floor is Python 3.8 and uses only the standard library. Git is required for revision-aware checks; authenticated `gh` is needed only for explicit hosted inspection. Workflow actions use full immutable SHAs; comments identify their human-readable versions.

The CI matrix includes Linux Python 3.8/3.10/3.12/3.13 and macOS Python 3.12. A separate Windows Python 3.8/3.13 job executes the PowerShell installer, filesystem safety, and actual Git-dispatch contracts. A configured job is not a claim that it passed on an unpushed revision; inspect the relevant run before claiming platform verification.

Foundation behavior tightens deliberately: install conflicts return nonzero without overwriting local work; path-only inspection cannot grant a CI documentation exemption; local evidence must be tracked at the evaluated revision; nested security and control paths receive higher lanes. Existing config format 1 and helper invocation forms remain supported. Root helper entry points delegate to the existing skill-local implementations.

The installer preserves `.gitattributes` conflicts and maintains `.sdlc-install.json` ownership state. A pre-manifest installation has no implied ownership: identical files are retained, differing files require explicit reconciliation. Do not claim an automatic rollback or uninstall interface; neither is provided by this change.
