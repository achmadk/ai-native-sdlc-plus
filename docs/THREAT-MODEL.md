# Threat model (short STRIDE)

Scope: lane classifier, evidence gate, doctor, trace blocks, install.

- Spoofing: fake lane label in PR body. Mitigation: CI recomputes lane from paths, ignores self-declared labels.
- Tampering: edited lane-config to downgrade Critical. Mitigation: config versioned and reviewed; evidence check cites rule version.
- Repudiation: unclear who approved. Mitigation: review notes name approver and base commit.
- Information disclosure: secrets in trace/session excerpts. Mitigation: redaction rules, secret fixtures in tests, never print matched values in scanners.
- Denial of service: none material (scripts run in ms, no network).
- Elevation: admin edits branch protection to bypass gate. Mitigation: documented plainly; gate is not unbypassable by owners.

Out of scope: regulated compliance, specialist secret scanning (use Gitleaks alongside), runtime sandboxing.
