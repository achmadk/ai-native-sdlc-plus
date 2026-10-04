# Proposal

## Why

Teams report AI code generation is faster yet PR review, testing, and ship processes have not changed, so throughput gains queue at review. Survey respondents also report missing context (acceptance criteria and prior decisions agents never read) and unreconstructible reasoning after months. This change builds a small, risk-proportional, evidence-backed Agent Skills suite that makes intent explicit before code, governs planned and unplanned loops, and makes agent work traceable — without adding review burden.

## What Changes

- Adds `ai-sdlc` router skill with deterministic lane selection (`lane.py` + config), plus `init`, `doctor`, and brownfield onboarding.
- Adds IC skills: `spec-first`, `context-pack`, `review-by-intent`, `decision-trace`, `verify-and-evals`, `ship-and-observe`, and optional `learning-mode`.
- Adds leader skills: `autonomy-policy` and `ai-readiness-and-metrics` with policy template and phased rollout guidance.
- Adds deterministic tooling: `lane.py`, `evidence_check.py` (CI fail-closed / local warn), `doctor.py`, hook templates, GitHub Actions + generic CI templates. Stdlib-only Python or POSIX shell, no network, no vendored binaries.
- Adds proof harness: task evals (with/without per skill), trigger evals (should/should-not), ceremony benchmark, context-gap test, reconstruction test, footprint report, with pre-registered pass criteria.
- Adds distribution: README with 10-minute quickstart and 60-second demo, suite diagram, adoption order, one-command install, adapters for spec-kit / Superpowers / OpenSpec, MIT license, CHANGELOG, COMPATIBILITY policy, CONTRIBUTING checklist, LIMITATIONS.md, and claims ledger.
- Builds router + one IC skill (`spec-first`) end to end first, runs its evals, then adjusts the rest before building the remainder.

## Capabilities

### New Capabilities

- `lane-router`: classify a change into Lite / Standard / Critical via deterministic script and route to the next skill; own init/doctor/onboarding; enforce evidence ladder.
- `spec-first`: turn vague requests into intent, acceptance criteria, constraints, and test expectations (one file for Lite/Standard, split for Critical).
- `context-pack`: assemble prior decisions, incidents, security rules, standards, and ticket criteria into a compact reusable brief with source links and staleness date.
- `review-trace`: review against intent and risk with AI failure-mode checklist and explain-back check; auto-draft decision records and prompt/agent trace blocks as a PR byproduct.
- `verify-evals`: test-first verification, evaluation criteria, validation loops, LLM-as-judge with caveats, incident-to-permanent-eval conversion.
- `ship-observe`: rollout checks for AI-generated changes, agent-visibility practices, runbooks for unplanned loops; incidents write a new intent closing the loop.
- `governance`: trust tiers, escalation and review rules per lane with policy template and rollout plan; org readiness scoring and dividend-reinvestment metrics with Goodhart warnings; junior learning-mode pairing.

### Modified Capabilities

- None. No existing specs exist (`openspec list --specs` returns empty); this is greenfield.

## Impact

- Greenfield addition under repo root: `skills/`, `scripts/`, `evals/`, `assets/`, `references/`, CI templates, docs (`README`, `LIMITATIONS.md`, `CHANGELOG`, `COMPATIBILITY`, `CONTRIBUTING`). No existing code, APIs, or dependencies to migrate.
- No breaking changes. Consumers opt in via install; adapters layer on spec-kit / Superpowers / OpenSpec without replacing them.
- Risk: eval and proof harness is the largest effort; mitigated by building router + `spec-first` first and adjusting before scaling.
