# Security policy

## Supported versions

There are no tagged releases yet. Only the latest commit on `main` receives
security fixes.

## Reporting a vulnerability

Please do not open a public issue for security problems.

1. Preferred: use GitHub private vulnerability reporting
   (repository **Security** tab, then **Report a vulnerability**).
2. If that is unavailable, contact the maintainer through the profile at
   <https://github.com/achmadk>.

You can expect an acknowledgement within 7 days. Fix timelines depend on
severity and are communicated in the advisory thread.

## In scope

- The deterministic scripts in `scripts/` and the installers
  (`install.sh`, `install.ps1`).
- Hooks in `hooks/` and CI workflows or adapters (`.github/workflows/`,
  `adapters/ci/`).
- Typical risks for this kind of tooling: command injection through PR
  titles, bodies, branch names or file paths; path traversal; checking out
  and executing untrusted PR code with privileged tokens; secret leakage in
  logs.

## Out of scope

- Behaviour already documented in `LIMITATIONS.md` (for example, an admin
  being able to bypass required checks, or the narrow privacy pattern scan).
- Vulnerabilities in third-party agents or CI platforms themselves.
