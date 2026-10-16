# EU Cyber Resilience Act (CRA) Compliance Guide (Regulation EU 2024/2847)

How the AI-native SDLC Plus suite satisfies European Union Cyber Resilience Act obligations for products with digital elements (PDEs).

## Core Timelines

- **Article 14 Mandatory Reporting:** In effect since **11 September 2026** (applies retroactively to active products).
  - 24-hour early warning to the ENISA Single Reporting Platform (SRP) and national CSIRTs.
  - 72-hour detailed incident notification.
  - 14-day final mitigation report (post-patch availability).
- **Full Application & Essential Requirements (Annex I):** **11 December 2027**.
  - Secure-by-default configurations.
  - Vulnerability handling process for product lifetime (minimum 5 years).
  - Machine-readable Software Bill of Materials (SBOM).

---

## SDLC Mapping for CRA Requirements

### 1. Mandatory Incident & Vulnerability Reporting (Article 14)
When an actively exploited vulnerability or severe security incident affects an AI-generated or AI-modified component:
- Follow `skills/ship-and-observe/references/loop-runbooks.md` ("Security finding loop" & "Incident loop").
- Produce an incident intent using `skills/ship-and-observe/assets/incident-intent-template.md`.
- File the early warning within 24 hours of confirmation.
- Trace the vulnerability's introduction back to commit trailers (`AI-Agent:`, `AI-Model:`) via `skills/decision-trace/`.

### 2. Secure-by-Design Lifecycle (Article 10 & Annex I Part I)
- **Pre-code Threat Modeling:** Every Critical change must produce a `## Threat note` (`skills/spec-first/assets/threat-note-template.md`).
- **Secret & Credential Scrutiny:** All briefs (`check_brief.py`), specs (`check_spec.py`), and test outputs (`redgreen.py`) run identical secret-detection regexes.
- **Fail-Closed Verification:** Automated gate (`evidence_check.py --ci`) blocks unverified merging.

### 3. Vulnerability Handling & Patching (Annex I Part II)
- Every security fix routes through `skills/verify-and-evals/scripts/redgreen.py`: proving the fix failed before the patch and succeeds after, preventing regression.
- Every remediation PR carries attributable rollback criteria in `## Rollout plan`.

### 4. Supply Chain & SBOM Transparency
- Every library or subcomponent added must be recorded in the change's context brief (`skills/context-pack/`).
- Toolkit itself maintains a clean, zero-external-dependency SBOM at `docs/SBOM.md`.
