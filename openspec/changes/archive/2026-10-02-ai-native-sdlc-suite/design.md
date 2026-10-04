# Design

## Context

See proposal.md Why for motivation. Current state: greenfield repo with empty `openspec/specs/` and no prior decisions; only `prompt.md` constrains the approach. Constraints carried from the brief: three risk-proportional lanes chosen by deterministic script; one human gate at highest judgment; advisory-to-CI enforcement ladder with honest labels; artifacts as byproducts; SKILL.md under ~250 lines with detail in `references/` and templates in `assets/`; stdlib-only Python or POSIX shell with no network and no vendored binaries; open Agent Skills layout plus AGENTS.md snippet; imperative tone explaining why. Explore-phase decisions: `ai-sdlc` is both thin router and owner of init/doctor/onboarding via lazy loading; `decision-trace` assembles from spec plus review into the PR with lane-proportional size.

## Goals / Non-Goals

**Goals:**
- Deterministic lane selection and evidence gating that works the same locally and in CI except for fail-open versus fail-closed behavior.
- Footprint discipline: always-loaded context stays to names plus descriptions; per-skill SKILL.md stays small with measured token report.
- Proof harness that can report with-skill versus baseline deltas, trigger precision/recall, ceremony cost, context-gap lift, and six-month reconstruction without retuning evals to flatter results.
- Phased delivery: router plus `spec-first` end to end first, then remaining skills adjusted from learnings.

**Non-Goals:**
- Replacing spec-kit, Superpowers, or OpenSpec; adapters layer on them.
- Regulated-compliance coverage, automatic quality judgment in CI, or branch-protection administration (docs state what an admin can bypass).
- Retrofitting history for brownfield repos.

## Decisions

**D1: Lane rules live in versioned config, evaluated by `lane.py` on paths plus change-type signals.**
Rationale: deterministic and auditable; model never decides ceremony. Config lists Critical globs (auth, payments, migrations, infra, security paths) plus change-type predicates; first match wins; ambiguous or malformed input escalates to Standard or Critical, never Lite. Alternative considered: model-classified risk with script audit — rejected because non-deterministic and untestable for mutation coverage.

**D2: `ai-sdlc` SKILL.md stays a hot-path router; init/doctor/onboarding are cold paths in `references/` plus scripts.**
Rationale: preserves thin-router footprint while honoring ownership. SKILL.md holds lane table, routing table, and one-line init/doctor triggers; full flags, config schema, and brownfield rules load only on invocation. Alternative: separate `ai-sdlc-init` skill — rejected to keep skill count sharp and routing single-entry.

**D3: Enforcement is advisory skill, fail-open local hook with visible warning, fail-closed CI check on evidence existence.**
Rationale: matches honesty requirement; local work never blocks, merges block only when the check is marked required. `evidence_check.py` asserts presence of spec link, trace block, test changes, and review notes per lane, and its messages name the missing artifact and rule. Alternative: fail-closed everywhere — rejected for taxing Lite changes and review capacity.

**D4: Trace composes from spec plus review plus session metadata via template, never blank-page authoring.**
Rationale: satisfies byproduct constraint and Lite overhead target under five minutes. Lite trace is three fields; Standard adds alternatives and risk; Critical adds threat and rollout links with redaction guidance for PII/secrets. Alternative: append-only `decisions/` log — deferred as optional convention, not required, to avoid merge handling in phase one.

**D5: Specs are combined for Lite/Standard, split intent plus spec for Critical; review checks against intent with AI failure-mode checklist and explain-back.**
Rationale: one gate where judgment is highest (spec for Standard, plan for Critical); review capacity is the bottleneck so no blanket sign-offs. Alternative: uniform heavyweight spec for all lanes — rejected for ceremony creep.

**D6: Eval harness pre-registers pass criteria before runs; task evals pair with/without, trigger evals pair should/near-miss, plus ceremony, context-gap, reconstruction, and footprint reports.**
Rationale: makes better measurable and prevents flattery. Negative deltas publish with design corrections. Alternative: single aggregate quality score — rejected because it hides tradeoffs across pass rate, tokens, and time.

**D7: Open Agent Skills layout with `AGENTS.md` snippet; adapters are thin shims with dated comparison table.**
Rationale: composable and portable across Claude Code, Claude.ai, and compatible agents without depending on one runtime. Each adapter documents where the incumbent is better. Alternative: native rewrite per harness — rejected as scope explosion.

## Risks / Trade-offs

- [Eval flattery] Pre-registered criteria drift under pressure → Mitigation: criteria committed before runs; any change restarts the affected eval pair and is logged.
- [Doctor false confidence] Cannot verify required-check status without network → Mitigation: doctor reports verified versus unverified explicitly; LIMITATIONS.md states CI only blocks when marked required.
- [Gate checks existence not quality] Green gate misread as good change → Mitigation: LIMITATIONS.md read-first plus gate messages stating the limit; quality proven only by task and reconstruction evals.
- [Trace PII leakage] Session transcripts carry secrets and ticket text → Mitigation: redaction rules in template plus tests with secret fixtures; reconstruction eval uses scrubbed fixtures.
- [Footprint versus pushy triggers] Strong trigger phrases bloat descriptions → Mitigation: iterate descriptions against trigger evals under token budget; report total always-loaded tokens.
- [Adapter thinness] Shim becomes rewrite per incumbent layout change → Mitigation: versioned COMPATIBILITY policy, pinned adapter tests, dated comparison table admitting where incumbents win.
- [Mutation burden] Gate-logic mutation testing with stdlib-only is slow → Mitigation: scope mutation to lane plus evidence logic; report kills versus survivors honestly.

## Migration Plan

1. Land router plus `spec-first` with `lane.py`, `evidence_check.py`, `doctor.py`, CI templates, and eval harness skeleton; run its full proof slice and adjust conventions.
2. Add remaining skills, scripts, and tests in lane order; run full proof suite from the brief.
3. Finish README, LIMITATIONS.md, claims ledger, SBOM, STRIDE note, CHANGELOG, COMPATIBILITY, and adapters; publish results summary stating wins, ties, and losses.
4. Rollback: each phase is additive docs plus scripts; removal is deleting the added directories and CI workflow with no data migration. Brownfield repos keep prior history untouched.

## Open Questions

- Exact Critical glob defaults for `lane.py` config pending first-repo calibration (deferrable: config is versioned and evals cover override behavior).
- Automated judge model choice and sampling rate for spot-checks pending first eval cost data (deferrable: criteria shape is fixed, judge instance is swappable).
- Adapter depth for GSD-style harnesses beyond the three named incumbents (deferrable: phase one ships three adapters; more follow only with measured demand).
