# SOC 2 Type II AI Delivery Controls Mapping

How the AI-native SDLC Plus suite satisfies AICPA Trust Services Criteria (TSC) for Change Management, Security, and Processing Integrity in AI-assisted engineering.

## Summary for Auditors

When engineers use AI coding assistants and autonomous agents, traditional SOC 2 change management controls often suffer from "rubber-stamp" reviews and missing audit trails. This suite restores auditor-verifiable controls directly in the git and CI workflow.

---

## Trust Services Criteria Mapping

| TSC Criteria | SOC 2 Requirement | SDLC Suite Control | Audit Evidence (Point to this) |
|---|---|---|---|
| **CC6.1** | Logical access and least privilege | `skills/autonomy-policy/`: Tiers define agent permissions; agents cannot merge code or alter branch protection | Action catalog (`action-catalog.md`), CI token permissions `contents: read` |
| **CC6.6** | Boundaries, encryption, and credential protection | Automated secret scanners in `check_brief.py`, `check_spec.py`, and `redgreen.py`; zero secrets in traces | CI step logs; clean regex scans across all brief and spec submissions |
| **CC6.8** | Preventing unauthorized code or data exfiltration | Sourced context packs (`skills/context-pack/`) with freshness windows and banned prompt injection phrases | `check_brief.py` validation report in CI |
| **CC7.1** | Vulnerability detection and configuration monitoring | Automated CI gate (`scripts/evidence_check.py --ci`) and `scripts/doctor.py` repository health audits | CI run status (`evidence` job) and `python3 scripts/doctor.py` output |
| **CC7.2** | Monitoring anomalies and security incidents | `skills/ship-and-observe/`: Loop runbooks for findings, flaky builds, and security incidents | Incident intent records and post-incident PRs with regression tests |
| **CC8.1 (CM-1)** | Authorization of changes prior to implementation | `skills/spec-first/`: Spec approval before build on Standard and Critical changes | Signed spec amendment or approval trailer in PR description |
| **CC8.1 (CM-2)** | Pre-implementation testing and verification | `skills/verify-and-evals/`: Red-to-green proof (`scripts/redgreen.py`) and required test diffs | CI check verifying `test_changes` in the PR diff |
| **CC8.1 (CM-3)** | Peer review and segregation of duties | `skills/review-by-intent/`: Reviewer checklists; 2 human reviewers required on Critical changes; bot cannot approve | GitHub branch protection rule requiring peer approval; PR review notes |
| **CC8.1 (CM-4)** | Emergency changes and rollback capability | `skills/ship-and-observe/`: Required `## Rollout plan` with explicit rollback commands and abort signals | PR body `## Rollout plan` on Critical changes |
| **CC8.1 (CM-5)** | Complete traceability of change reasoning | `skills/decision-trace/`: Mandatory `## Trace` block logging agent, model, prompts, and rejected alternatives | Permanent PR description and commit history |
