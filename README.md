# AI-native SDLC skills (plus)

AI-native SDLC combines Agent Skills with a standard-library Python gate for risk-proportional delivery. It classifies Git changes as Lite, Standard, or Critical, checks the evidence owed by that lane, and supports non-destructive toolkit installation. Use it alongside your coding agent and planning process; installing instructions or passing a structural check is not proof of semantic quality, human approval, runtime containment, or hosted merge enforcement. See [the limits](LIMITATIONS.md).

Claims convention: `[report-stated]` means a cited publisher or survey reports it, not an independently reproduced outcome; `[measured here]` means a scoped local observation with recorded inputs and environment; `[extrapolated]` means a fit judgment. Historical evaluation records do not attest a newer revision or a comparative benchmark.

Already using OpenSpec or Spec Kit? Keep that planning process while evaluating this repository's gate and skills. The gate and spec checker accept OpenSpec change folders and Spec Kit feature folders in-place as lane-appropriate specification evidence—see [the interoperability guide](docs/INTEROPERABILITY.md). Use `scripts/sdlc.py` (or the local wheel's `sdlc` entry point) as the unified front door for `init`, `lane`, `check spec|brief|evidence`, `doctor`, `explain`, `status`, `update`, `uninstall`, and `lite`. Start with the [sourced comparison](docs/COMPARISON.md), [current compatibility notes](docs/COMPATIBILITY.md), and [interoperability guide](docs/INTEROPERABILITY.md).

---

## Sixty-Second Gate Demo

This is a local replay of the missing-evidence failure mode seen on [PR #4](https://github.com/achmadk/ai-native-sdlc-plus/pull/4), not a new hosted PR or an exact replay of its event payload. It uses the recorded base/head below and a simplified empty PR body. Test files changed, but Critical evidence is still required.

Prerequisites: run from an existing full-history toolkit checkout containing both revisions, with supported Python and Git installed. Cloning, installation, authentication, and hosted execution are outside the timing boundary. A missing ref or tool is a setup failure, not a successful demonstration of blocking.

POSIX shell:

```sh
printf '' | PYTHONDONTWRITEBYTECODE=1 GITHUB_STEP_SUMMARY='' python3 -B scripts/evidence_check.py --ci \
  --config scripts/lane-config.yaml --repo-root . \
  --base=e5e8ff20fb732064f9ad38271199b3357b398099 \
  --head=0ee9a1b426778aa4bd2cf45092bf37eb852d52a7 --pr-body-file -
```

PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:GITHUB_STEP_SUMMARY = ''
'' | python -B scripts/evidence_check.py --ci `
  --config scripts/lane-config.yaml --repo-root . `
  --base=e5e8ff20fb732064f9ad38271199b3357b398099 `
  --head=0ee9a1b426778aa4bd2cf45092bf37eb852d52a7 --pr-body-file -
```

Expected exit code: **1**, with this missing-evidence result, not an ignored failure:

```text
ok       test_changes   16 test path(s) changed
FAIL: missing evidence for Critical: intent_link, spec_link, threat_note, trace_block, review_notes, rollout_plan
```

`[measured here]` Two prepared-checkout runs on 2026-11-09 took approximately **0.30 seconds** and **0.681 seconds** on Windows with Python 3.15.2 and Git 2.45.1.windows.1, using checker revision `06c2ab56d1f790f17203c586108c53112be563cd` and the inputs above. These are reference observations, not a cold-start, onboarding, hosted-PR, or competitor-performance claim. The command does not edit files or GitHub; actual CI runs trusted-base tooling against a fresh event payload. Do not use `--present` or a lane downgrade to make incomplete Critical evidence pass.

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

Run the installer from a toolkit checkout, supplying the target repository. Source paths are relative to the installer, not your working directory.

```bash
sh /path/to/ai-native-sdlc-plus/install.sh /path/to/repo
```

```powershell
& "C:\path\to\ai-native-sdlc-plus\install.ps1" -Root "C:\path\to\repo"
```

The shared standard-library installer copies the explicit payload in `scripts/install-manifest.json`: core and optional tools, canonical helper entry points, skill resources, CI templates and their runner, both GitHub enforcement workflows, hooks, and narrow LF attributes. It does not register skills, activate hooks, change GitHub settings, or install dependencies. Python 3.8+ and Git are prerequisites for the toolkit; PowerShell can use a working `python` when `python3` is unavailable.

Ownership is recorded in `.sdlc-install.json`. Identical reruns preserve file/state bytes and modification times. An unchanged managed file can be upgraded; a differing unowned or locally modified file causes a reported conflict before payload writes. This includes existing lane configs, templates, workflows, and `.gitattributes`. Reconcile conflicts explicitly and rerun; do not delete ownership state to force an overwrite. A later I/O failure reports a partial result and returns nonzero rather than claiming success.

From the installed repository (via the unified `sdlc` front door or direct helpers):

```bash
python3 scripts/sdlc.py init --root . [--agents claude,cursor,copilot,codex,gemini,opencode,kilo]
python3 scripts/sdlc.py status --root .        # read-only ownership, policy, and drift status
python3 scripts/sdlc.py doctor --root .        # grouped offline installation health (raw counts retained)
python3 scripts/sdlc.py explain codeowners --root .
python3 scripts/sdlc.py lane --paths <files>
python3 scripts/sdlc.py check spec --help
python3 scripts/sdlc.py check brief --help
python3 scripts/sdlc.py check evidence --help
python3 scripts/redgreen.py --help
```

Copying files is not merge enforcement. After separately authorized setup, inspect the supported GitHub protection profile:

```bash
python3 scripts/doctor.py --root . --check-branch-protection --require-enforcement
```

This requires authenticated `gh` access to protection, ownership, and bypass settings. It uses read-only REST requests plus a fixed read-only GraphQL POST query for merge-queue state; no mutations are issued. Missing, inaccessible, or unsupported prerequisites fail strict readiness. Follow the [activation checklist](skills/ai-sdlc/references/init.md), not a generic doctor exit code.

---

## 10-Minute First Win

1. Run the source-relative installer against your target and resolve any reported conflicts (2 min for a clean target).
2. Verify local health with `python3 scripts/doctor.py --root .`; hosted enforcement remains unverified without the explicit remote check (1 min).
3. Classify your next change: `python3 scripts/lane.py --paths <files>` (1 min).
4. Draft intent using `skills/spec-first/assets/intent-template.md` (Lite: 5 min).
5. After authorized bootstrap and required-check setup, open a PR with the trace template. CI uses base-revision tooling and explicit `--base`/`--head` revisions. Local spec/intent links must be nonempty regular tracked blobs at the evaluated head, not untracked files or Git metadata.

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

Instruction adapters are provided for popular AI coding assistants. Installation and instruction availability are not proof of agent behavior or runtime permission enforcement; agent registration remains separate.

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

- **GitHub Actions:** `.github/workflows/sdlc-gate.yml` (trusted base tooling and isolated Python execution)
- **GitLab CI:** [`adapters/ci/gitlab-ci.yml`](adapters/ci/gitlab-ci.yml)
- **Azure DevOps:** [`adapters/ci/azure-pipelines.yml`](adapters/ci/azure-pipelines.yml)
- **Bitbucket Pipelines:** [`adapters/ci/bitbucket-pipelines.yml`](adapters/ci/bitbucket-pipelines.yml)
- **Generic CI (CircleCI, Jenkins, Buildkite):** [`skills/ai-sdlc/assets/ci-generic.sh`](skills/ai-sdlc/assets/ci-generic.sh)

---

## Optional Tools

Standalone, standard-library helpers that sit next to the core gate and never run automatically (details in [`docs/optional-tools.md`](docs/optional-tools.md)):

- `scripts/trace_lint.py`: heuristic checks that PR evidence is more than empty paperwork (unedited templates, empty fields, broken links, missing test files).
- `scripts/lane_backtest.py`: replays `lane.py` over your recent history to calibrate lane rules.
- `scripts/doctor_online.py`: narrower legacy opt-in check that a named context is required. Use core doctor's `--require-enforcement` profile for the broader protection checks.

---

## Supply Chain & Security Hardening

- **Zero Third-Party Runtime Dependencies:** 100% Python standard library (`sys`, `os`, `re`, `subprocess`, `unittest`).
- **Pinned Workflow Actions:** All CI actions pinned to immutable 40-character commit SHAs.
- **Integrated Secret Scanning:** Multi-layer secret regex scanning in all brief/spec parsers plus [Gitleaks action](.github/workflows/gitleaks.yml) in CI.
- **Cross-Platform Pre-Push Hooks:** Advisory dispatch with supported interpreter discovery and managed LF rules that survive Git checkout. Windows Python 3.8/3.13 CI runs focused native installer/Git-dispatch tests and a separate full suite; a configured job or skipped test is not a passing execution result.
- **Reproducible Verification:** Run `python3 -m unittest discover -s tests -v`, `python3 tests/mutate.py`, and the ShellCheck command in `.github/workflows/ci.yml` against the revision being evaluated. Historical counts in `evals/` and `PATCH-NOTES.md` do not attest a newer revision. Trigger scores measure lexical matching, not actual agent skill selection.

Gitleaks receives the generated read-only `GITHUB_TOKEN` explicitly and has PR commenting disabled. Organization repositories additionally require `GITLEAKS_LICENSE`; fork-event secret availability can prevent scanning. Missing credentials, licensing, or API access must fail as setup errors, not be bypassed or reported as a clean scan. Hosted scanner verification is separate from local workflow-contract tests.

For self-tests in a Windows toolkit checkout, use `python -B -m unittest discover -s tests -v`. Shared fixtures select Git for Windows' shell, handle read-only Git objects, and report unavailable symlink, filename, permission, or terminal capabilities as explicit skips. Windows command doubles run through the existing Python interpreter without compiling temporary executables. Portable classification and Git-metadata checks still run. See [compatibility and test coverage](docs/COMPATIBILITY.md) for the configured matrix, locally exercised versions, and skip boundaries; local results do not attest unrun CI jobs or hosted scanner behavior.

---

## How This Compares

These are reviewed source descriptions and fit judgments, not a leaderboard or independent product tests. The [detailed comparison](docs/COMPARISON.md) covers the same tools plus Tessl, with prerequisites, unverified areas, and evidence limits. No source absence is treated as feature absence.

| Tool | Version / surface | Documented capabilities | Fit / limits | Evidence | Primary sources | Checked |
| --- | --- | --- | --- | --- | --- | --- |
| Spec Kit | 1.3.2 snapshot | Configurable SDD, bug-fix and assessment processes; extensions, presets, workflows and gates. | Evaluate for reusable process customization; it is not inherently fixed-depth. Comparative cost and agent outcomes are unverified here. | [report-stated] capabilities; [extrapolated] fit | [README](https://github.com/github/spec-kit/blob/v1.3.2/README.md) | 2026-11-09 |
| OpenSpec | 1.16.1 snapshot; stores beta | Requirement/scenario artifacts, change lifecycle, profiles/schemas, and separate planning stores. | Evaluate for evolving specifications; artifact completion is not approval or hosted enforcement. | [report-stated] capabilities; [extrapolated] fit | [README](https://github.com/Fission-AI/OpenSpec/blob/v1.16.1/README.md) | 2026-11-09 |
| Kiro | IDE 1.4.121; CLI 3.1.0; other surfaces rolling | IDE, CLI and hosted surfaces with specs, steering, hooks, permissions and ACP. | Evaluate for integrated agent execution; check the chosen surface and service terms rather than assuming IDE-only behavior. | [report-stated] capabilities; [extrapolated] fit | [Docs](https://kiro.dev/docs/) [Changelog](https://kiro.dev/changelog/) | 2026-11-09 |
| BMAD | 6.12.4 snapshot | Right-sized planning/build paths, durable context, specialist perspectives and optional modules. | Evaluate for shared product/engineering process; relative ceremony has not been measured here. | [report-stated] capabilities; [extrapolated] fit | [README](https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/README.md) | 2026-11-09 |
| Superpowers | 7.0.2 snapshot | Design, TDD, debugging and review skills with harness-specific plugins and documented behavior evaluations. | Evaluate for agent-integrated coding discipline; verify loader behavior and repository controls in the selected setup. | [report-stated] capabilities; [extrapolated] fit | [README](https://github.com/obra/superpowers/blob/v7.0.2/README.md) | 2026-11-09 |

For a fact-checked adoption decision, review the linked version/surface and its current terms, then test the workflow you need. A passing metadata lint validates this table's structure, not those product claims or a universal winner.
