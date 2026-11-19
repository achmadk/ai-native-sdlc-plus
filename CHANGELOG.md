# CHANGELOG

## 0.3.0 (Unreleased)

- Use shared `scripts/version.py` product identity for doctor, installed CLI, wheel filename, METADATA, and dist-info. Runtime installation ownership remains version 1.
- Provide the standard-library installer, unified CLI, non-destructive lifecycle operations, and local offline wheel from the explicit runtime allowlist.
- Generate seven native agent profiles from shared descriptors, canonical policy, skill sources, and command operations. Repository compatibility adapters are separately hash-approved; both Cursor formats retain the canonical safeguards.
- Emit evidence manifests, inspect configured approval evidence, and verify semantic JUnit red-green records through the committed gate and proofing helpers.
- Retain preregistered model-selection and paired-task recordings, offline replay, actual-loader token observations, and negative evaluation outcomes. These are scoped observations rather than broad quality claims.
- Native discovery and behavioral coverage for generated profiles require separate evidence from each declared client/version/surface; generated-file tests alone do not establish support.
- This candidate is not tagged or published. The exact release candidate, required native evidence, independent reviews, and tag authorization remain separate release gates.
- Earlier cumulative patch rounds remain in `PATCH-NOTES.md`; their exact release chronology is not established here, and no historical release dates or tags are backfilled.

## 0.1.1 (2026-10-02)

- Fix SKILL.md frontmatter: quote description strings so `npx skills add` YAML discovery parses all 10 skills (unquoted `Triggers: ...` broke parsing). Add SkillsLayoutTest regression test (17/17 green).

## 0.1.0 (2026-10-02)

- Initial suite: 10 skills, lane.py + evidence_check.py + doctor.py, hook and CI templates, eval battery with published negatives, README, LIMITATIONS.md, adapters, install.
