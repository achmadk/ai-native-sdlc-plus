# AI-native SDLC skills (plus)

> **Risk-proportional Agent Skills for AI-native delivery: explicit intent before code, governed loops, traceable work — with compliance mappings for the EU AI Act, Cyber Resilience Act (CRA), NIST AI RMF, and SOC 2 Type II.**

Claims convention: `[report-stated]` = perception-survey respondents report (never measured outcomes); `[measured here]` = numbers from `evals/`, or from the test suite and verification scripts in this repository, reproducible by running them; `[extrapolated]` = judgment, flagged as such.

---

## 60-Second Demo

```bash
# 1. Classify risk lane from changed files
$ python3 scripts/lane.py --paths docs/guide.md
Lite: matched Lite rule docs/**

# 2. Check owed evidence for the lane
$ python3 scripts/evidence_check.py --lane Standard --present spec_link test_changes
WARNING: missing evidence for Standard: trace_block, review_notes (local, not blocking)
```

---

## Install & Setup

### Fast Install via Agent Skills CLI
```bash
npx skills add achmadk/ai-native-sdlc-plus
```
This discovers all 10 skills (`ai-sdlc`, `spec-first`, `context-pack`, `review-by-intent`, `decision-trace`, `verify-and-evals`, `ship-and-observe`, `learning-mode`, `autonomy-policy`, `ai-readiness-and-metrics`) and links them into your agent. It installs the skills; the gate scripts, config, CI workflow and hooks come from the next section.

```bash
npx skills add achmadk/ai-native-sdlc-plus --all  # every skill, every agent
npx skills add achmadk/ai-native-sdlc-plus -g     # global, all projects
```

### Deterministic Scripts & CI Gate (No Node.js required)
- **Linux / macOS:**
  ```bash
  sh install.sh
  ```
- **Windows (PowerShell):**
  ```powershell
  .\install.ps1
  ```
- **Verify installation health:**
  ```bash
  python3 scripts/doctor.py --root .
  ```

---

## 10-Minute First Win

1. Run `sh install.sh` (or `.\install.ps1` on Windows) to copy gate scripts, config, CI workflow, and hooks (2 min).
2. Verify with `python3 scripts/doctor.py --root .` (1 min).
3. Classify your next change: `python3 scripts/lane.py --paths <files>` (1 min).
4. Draft intent using `skills/spec-first/assets/intent-template.md` (Lite: 5 min).
5. Open PR with trace block from `skills/decision-trace/assets/trace-block.md`; CI verifies evidence with `evidence_check.py --ci`.

---

## The 10 Skills (Mapped to SDLC Stages)

| Stage | Skill | Audience | What it Delivers |
|---|---|---|---|
| **All** | [`ai-sdlc`](skills/ai-sdlc/SKILL.md) | Everyone | Lane router (Lite / Standard / Critical), evidence rules, doctor checks |
| **Planning** | [`spec-first`](skills/spec-first/SKILL.md) | ICs | Acceptance criteria (`AC1: ... \| pass: ...`), out-of-scope bounds, spec approvals |
| **Planning** | [`context-pack`](skills/context-pack/SKILL.md) | ICs | Sourced briefs of historical decisions, standards, and git-based freshness |
| **Build** | [`decision-trace`](skills/decision-trace/SKILL.md) | ICs | Reasoning trail as a PR by-product (prompts, models, rejected alternatives) |
| **Build** | [`learning-mode`](skills/learning-mode/SKILL.md) | Juniors / Mentors | Guided pairing, 4-level hint ladder, predict-then-run understanding |
| **Verify** | [`verify-and-evals`](skills/verify-and-evals/SKILL.md) | ICs | Deterministic red-to-green proof (`scripts/redgreen.py`), eval pre-registration |
| **Review** | [`review-by-intent`](skills/review-by-intent/SKILL.md) | Reviewers | Intent-vs-implementation audit, AI failure checklist (hallucinations, fake tests) |
| **Review** | [`autonomy-policy`](skills/autonomy-policy/SKILL.md) | Leaders / Sec | Trust tiers (1–3), action catalog, fail-closed escalation, demotion triggers |
| **Ship & Observe** | [`ship-and-observe`](skills/ship-and-observe/SKILL.md) | ICs / SRE | Rollout/rollback plans, attributable hunks, runbooks for 5 unplanned loops |
| **Govern & Measure**| [`ai-readiness-and-metrics`](skills/ai-readiness-and-metrics/SKILL.md) | Leaders | 0–3 readiness rubric, team-level metrics beyond velocity, Goodhart counter-metrics |

---

## Enterprise Compliance Packs (US & EU)

Pre-built mappings from gate evidence to the provisions below. They are supporting evidence, not legal advice, certification or a conformity assessment; see [LIMITATIONS.md](LIMITATIONS.md):

- **[EU AI Act (Regulation EU 2024/1689 & Omnibus 2026/1744)](docs/compliance/EU-AI-ACT.md):**
  - Article 4: AI Literacy (`learning-mode`)
  - Article 9: Risk Management (`threat-note-template.md` on Critical lane)
  - Article 10: Data & Context Governance (`context-pack`)
  - Article 11 & Annex IV: Technical Documentation (`spec-first`)
  - Article 12: Automated Lifecycle Logging (`decision-trace` git trailers)
  - Article 14: Human Oversight & Stop Controls (`autonomy-policy` tiers)
  - Article 15: Cybersecurity & Robustness (`verify-and-evals` red-to-green proof)
  - Article 50: Synthetic code transparency and author disclosure
- **[EU Cyber Resilience Act (CRA / Regulation EU 2024/2847)](docs/compliance/CRA.md):**
  - Article 14 Mandatory Reporting: 24h early warning, 72h notification, final report within 14 days of a corrective or mitigating measure being available, via ENISA Single Reporting Platform (SRP)
  - Essential cybersecurity requirements, secure-by-design lifecycle, and machine-readable SBOM
- **[NIST AI Risk Management Framework 1.0 (AI RMF)](docs/compliance/NIST-AI-RMF.md):**
  - Comprehensive alignment across all four NIST AI RMF core functions: **GOVERN**, **MAP**, **MEASURE**, and **MANAGE**
- **[SOC 2 Type II AI Delivery Controls](docs/compliance/SOC2-TYPE2.md):**
  - Criteria CC6 (Access & Boundaries), CC7 (Incident Monitoring), CC8 (Change Authorization, Testing, Peer Review, Rollback)

---

## Universal Agent Compatibility

Verified, turnkey configurations for popular AI coding assistants:

| Agent / Tool | Config File | Integration Method |
|---|---|---|
| **Claude Code** | `.claude/CLAUDE.md`, `.claude/commands/` | Native CLI integration |
| **Cursor IDE** | `.cursorrules`, `.cursor/rules/sdlc.mdc` | Multi-rule MDC context |
| **GitHub Copilot** | `.github/copilot-instructions.md` | Workspace instructions |
| **OpenAI Codex / Aider / Devin** | `AGENTS.md` | Standard markdown agent prompt |
| **Google Gemini CLI / Antigravity** | `GEMINI.md` | Instruction ruleset |

---

## Multi-CI Platform Support

Enforce lane evidence across any CI platform with base-branch tooling verification:

- **GitHub Actions:** `.github/workflows/sdlc-gate.yml` (trusted tooling checkout, unforgeable merge-base)
- **GitLab CI:** [`adapters/ci/gitlab-ci.yml`](adapters/ci/gitlab-ci.yml)
- **Azure DevOps:** [`adapters/ci/azure-pipelines.yml`](adapters/ci/azure-pipelines.yml)
- **Bitbucket Pipelines:** [`adapters/ci/bitbucket-pipelines.yml`](adapters/ci/bitbucket-pipelines.yml)
- **Generic CI (CircleCI, Jenkins, Buildkite):** [`skills/ai-sdlc/assets/ci-generic.sh`](skills/ai-sdlc/assets/ci-generic.sh)

---

## Optional Tools

Standalone, standard-library helpers that sit next to the core gate and never run automatically (details in [`docs/optional-tools.md`](docs/optional-tools.md)):

- `scripts/trace_lint.py`: heuristic checks that PR evidence is more than empty paperwork (unedited templates, empty fields, broken links, missing test files).
- `scripts/lane_backtest.py`: replays `lane.py` over your recent history to calibrate lane rules.
- `scripts/doctor_online.py`: opt-in check, via the `gh` CLI, that the gate is a required check.

---

## Supply Chain & Security Hardening

- **Zero Third-Party Runtime Dependencies:** 100% Python standard library (`sys`, `os`, `re`, `subprocess`, `unittest`).
- **Pinned Workflow Actions:** All CI actions pinned to immutable 40-character commit SHAs.
- **Integrated Secret Scanning:** Multi-layer secret regex scanning in all brief/spec parsers plus [Gitleaks action](.github/workflows/gitleaks.yml) in CI.
- **Cross-Platform Pre-Push Hooks:** Non-blocking advisory hooks for POSIX (`hooks/pre-push.sh`) and Windows PowerShell (`hooks/pre-push.ps1`).
- **Comprehensive Verification:** 380 unit and integration tests passing; 155-mutant verification battery with 100% of non-equivalent mutants killed; ShellCheck clean (0 warnings); 10/10 skills passing trigger evals (0.97 precision, 0.96 recall). `[measured here]`

---

## How This Compares (Factual)

| Area | This suite | timwukp/ai-native-sdlc | spec-kit |
|---|---|---|---|
| **Lanes scale ceremony with risk** | Yes: Lite/Standard/Critical (`lane.py`) | Not found on front page | Not found; fixed extension depth |
| **Enterprise compliance packs** | Mappings in `docs/compliance/`: EU AI Act, CRA, NIST AI RMF, SOC 2 | None documented | None documented |
| **Right-of-code loops** | `ship-and-observe` + 5 loop runbooks | CI gate + privacy scanner | Bug-fix extension adjacent |
| **Context packs & freshness** | Yes: git-tracked `governs:` staleness | Unverified | Unverified |
| **Decision trace as by-product** | Yes: lane-sized PR trace blocks | Intent chain (heavier) | Unverified |
| **Multi-Agent / Multi-CI** | Claude, Cursor, Copilot, Codex, Gemini + 5 CI systems | Single platform focus | GitHub Actions primarily |
| **Proof battery** | 380 tests + 155 mutation check + trigger precision 0.97 | verify.py model + 36/80 rubric | Maturity at scale (140k stars) |

This suite's column describes what is in this repository; its numbers are `[measured here]`. The other two columns summarize those projects' public READMEs: "Not found" means not found there, not that it is absent, and "Unverified" means not checked. Re-check them before relying on them.

Survey context: 94% use AI, 36% agentic, 6% deeply integrated; 74% faster codegen yet ~78-79% manual PR process; trust ~25-32% zero / ~60% guarded / ~1% full autonomy `[all report-stated]`.
