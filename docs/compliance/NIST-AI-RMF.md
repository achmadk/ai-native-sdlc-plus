# NIST AI Risk Management Framework (AI RMF 1.0) Mapping

How the AI-native SDLC Plus suite maps to the US National Institute of Standards and Technology (NIST) AI RMF core functions.

## The Four Core Functions

```
GOVERN ──► MAP ──► MEASURE ──► MANAGE
   ▲                               │
   └──────── (Feedback Loop) ──────┘
```

---

### 1. GOVERN (Cultivating Risk Management Culture & Governance)
*Processes, policies, and organizational structures for AI oversight.*

| NIST AI RMF Category | SDLC Suite Implementation |
|---|---|
| **GOVERN 1.1–1.3:** Organizational roles, responsibilities, and accountability | `skills/autonomy-policy/`: Tiers 1–3 define what an agent may do alone vs. what requires human sign-off; human remains accountable for PR merges. |
| **GOVERN 1.4:** Policies on risk thresholds | `scripts/lane-config.yaml`: Clear, code-enforced boundaries between Lite, Standard, and Critical paths. |
| **GOVERN 2.1–2.3:** AI system inventory and lifecycle readiness | `skills/ai-readiness-and-metrics/`: 4-dimension readiness scoring (Context, Trace, Gate, Autonomy) with pre-registered review dates. |
| **GOVERN 3.1:** Feedback and continuous improvement | Loop runbooks in `skills/ship-and-observe/`: Every incident, security finding, or test flake feeds back into an updated spec and regression test. |

---

### 2. MAP (Context, Scope & Boundary Setting)
*Identifying potential impacts, intended purpose, and constraints.*

| NIST AI RMF Category | SDLC Suite Implementation |
|---|---|
| **MAP 1.1–1.5:** Intended context, purpose, and system capabilities | `skills/spec-first/assets/intent-template.md`: Explicit intent statements before any code is generated. |
| **MAP 2.1–2.3:** System constraints and boundaries | `skills/spec-first/`: Formal out-of-scope constraints and assumptions recorded in specs. |
| **MAP 3.1–3.4:** Data and knowledge provenance | `skills/context-pack/scripts/check_brief.py`: Sourced context briefs with freshness validation and git-backed `governs:` checks. |

---

### 3. MEASURE (Analysis, Testing, and Evaluation - TEVV)
*Objective verification that AI actions match specifications.*

| NIST AI RMF Category | SDLC Suite Implementation |
|---|---|
| **MEASURE 1.1–1.3:** Metrics and evaluation approaches | `skills/verify-and-evals/assets/eval-plan-template.md`: Pre-registered eval criteria and metrics. |
| **MEASURE 2.1–2.4:** Testing and validation for trustworthiness | `skills/verify-and-evals/scripts/redgreen.py`: Automated proof that tests fail without the change and pass with it. |
| **MEASURE 2.7:** Detection of unintended behavior | `skills/review-by-intent/assets/review-checklist.md`: AI-specific failure checklist (invented APIs, weakened asserts, swallowed exceptions). |
| **MEASURE 3.1–3.3:** Ongoing monitoring and metric drift | `skills/ai-readiness-and-metrics/references/metrics.md`: Velocity paired with quality counter-metrics; Goodhart warnings. |

---

### 4. MANAGE (Risk Response and Recovery)
*Allocation of resources to address risks and handle production deviations.*

| NIST AI RMF Category | SDLC Suite Implementation |
|---|---|
| **MANAGE 1.1–1.3:** Prioritization and mitigation of identified risks | `skills/spec-first/assets/threat-note-template.md`: Threat notes for Critical changes. |
| **MANAGE 2.1–2.4:** Controls during release and deployment | `skills/ship-and-observe/assets/rollout-plan-template.md`: Staged rollout, telemetry signals, abort criteria, and rollback steps. |
| **MANAGE 3.1–3.2:** Incident response and un-planned loops | `skills/ship-and-observe/references/loop-runbooks.md`: Standardized runbooks for 5 unplanned loops. |
| **MANAGE 4.1–4.3:** Traceability and post-incident learning | `skills/decision-trace/assets/trace-block.md`: Auditable decision trails on every pull request. |
