# SBOM (suite v0.1.0)

No third-party runtime dependencies. Scripts are stdlib-only Python; hooks and CI variants are POSIX shell / GitHub Actions pinned workflow files.

| Component | Version | Source |
|---|---|---|
| scripts/lane.py | 0.1.0 | this repo, stdlib only |
| scripts/evidence_check.py | 0.1.0 | this repo, stdlib only |
| scripts/doctor.py | 0.1.0 | this repo, stdlib only |
| hooks/pre-push.sh | 0.1.0 | this repo, POSIX shell |
| .github/workflows/sdlc-gate.yml | 0.1.0 | pins actions/checkout@v4, setup-python@v5 |

Python floor: 3.11+. Network calls: none in scripts.
