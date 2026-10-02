# COMPATIBILITY / versioning policy

Semver for skills, scripts, templates, and adapters. Lane-config `version` bumps on any rule change; evidence check prints the config version it evaluated.

- Minor: new skill, new template field (optional), new adapter.
- Patch: wording, fixes, eval data.
- Major: lane semantics change, required-evidence change, dropped adapter.

Pinned: CI workflow pins actions/checkout@v4 and setup-python@v5; Python floor 3.11+. Adapter smoke tests run on each minor.
