# EU AI Act Compliance Mapping (Regulation EU 2024/1689 & Omnibus EU 2026/1744)

How the AI-native SDLC Plus suite maps directly to compliance obligations under the European Union Artificial Intelligence Act.

## Overview & Timelines (as of late 2026)

- **Prohibited AI Practices (Article 5):** In force since 2 February 2025.
- **AI Literacy (Article 4):** In force since 2 February 2025 (`learning-mode` & `review-by-intent`).
- **General-Purpose AI (GPAI) Models (Chapter V):** Applicable since 2 August 2025.
- **Transparency Obligations (Article 50):** Applicable since 2 August 2026 (synthetic content marking & agent disclosure).
- **Standalone High-Risk AI Systems (Annex III):** 2 December 2027 (amended by Digital Omnibus Regulation EU 2026/1744).
- **Embedded Regulated Products (Annex I):** 2 August 2028.

---

## Article-by-Article Evidence Map

| Article | EU AI Act Requirement | SDLC Suite Artifact / Mechanism | Enforcement Layer |
|---|---|---|---|
| **Art. 4** | AI literacy of staff operating AI systems | `skills/learning-mode/`: Guided pairing, 4-level hint ladder, predict-then-run checks | Skill (educational guardrail) |
| **Art. 9** | Risk management system (identification & residual risk mitigation) | `skills/spec-first/assets/threat-note-template.md`: Threat notes required on Critical lane | CI Gate (`sdlc-gate.yml` verifies `## Threat note`) |
| **Art. 10** | Data governance & provenance | `skills/context-pack/assets/brief-template.md`: Sourced, dated context with git-based staleness | `check_brief.py` |
| **Art. 11 & Annex IV** | Technical documentation prior to placing on market | `skills/spec-first/`: Pre-code criteria (`AC1: ... \| pass: ...`), approved spec before build | `check_spec.py` |
| **Art. 12** | Automatic logging of events during lifecycle | `skills/decision-trace/assets/trace-block.md`: Agent, prompt, rejected options, git trailers (`AI-Agent:`) | CI Gate verifies `## Trace` |
| **Art. 14** | Human oversight (design for human stop / override) | `skills/autonomy-policy/`: Tiers 1-3, mandatory human approval, fail-closed escalation | Code review & CI branch protection |
| **Art. 15** | Accuracy, robustness, and cybersecurity | `skills/verify-and-evals/`: Red-to-green proof (`scripts/redgreen.py`), failing-first test verification | Deterministic tool run |
| **Art. 50** | Transparency & marking of AI-generated content / code | Commit trailers (`AI-Agent: <tool>`, `AI-Model: <id>`), `ship-and-observe` agent hunk markers | `evidence_check.py` + PR trace |

---

## Lane Routing for EU AI Act Risk Classes

1. **Unacceptable Risk (Article 5):** Banned. Not eligible for any SDLC lane.
2. **High-Risk (Annex III / Annex I):** Must route to **Critical** lane.
   - Requires: Intent statement, formal spec file, threat note, red-to-green test proof, trace block, 2 human reviewers, rollout & rollback plan.
3. **Limited Risk / Transparency Only (Article 50):** Routes to **Standard** lane.
   - Requires: Spec file, test changes, trace block with model disclosure, human review notes.
4. **Minimal / No Risk:** Routes to **Lite** or **Standard** based on codebase change paths in `scripts/lane-config.yaml`.
