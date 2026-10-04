# Tasks

## 1. Competitor Gap Analysis and Baseline Plan

- [x] 1.1 Read incumbent repos (ai-native-sdlc SKILL.md, templates, scripts, evals, limitations; spec-kit, Superpowers, OpenSpec) and write one-page gap analysis marking unverified items as unverified, verified by gap doc existing at `evals/gap-analysis.md` with dated sources
- [x] 1.2 Finalize skill list with purpose, audience, trigger, and one-line description each plus lane rules table and assumptions log, verified by `openspec/changes/ai-native-sdlc-suite/specs/` matching the list with zero orphan capabilities
- [x] 1.3 Pre-register pass criteria for task evals, trigger evals, ceremony benchmark, context-gap test, reconstruction test, and footprint report, verified by `evals/pass-criteria.md` committed before any eval run timestamp

## 2. Router Plus Spec-First Slice End to End

- [x] 2.1 Scaffold Agent Skills layout (`skills/ai-sdlc/SKILL.md` under 250 lines, `references/`, `assets/`, `AGENTS.md` snippet) with thin-router hot path and lazy init/doctor pointers, verified by line count check and footprint measurement script output
- [x] 2.2 Implement `skills/spec-first/SKILL.md` (combined file for Lite/Standard, split for Critical, testable criteria rules) with examples, verified by three sample specs rendering from vague prompts without copy-paste violations
- [x] 2.3 Implement `scripts/lane.py` from versioned config with first-match-wins and escalate-on-ambiguous behavior, verified by unit tests covering Lite, Standard, Critical, ambiguous, and malformed inputs passing
- [x] 2.4 Implement `scripts/evidence_check.py` (local warn fail-open, CI fail-closed on evidence existence) and `scripts/doctor.py` (verified versus unverified reporting), verified by local-warning and CI-blocking test scenarios passing
- [x] 2.5 Add `init` setup plus hook templates, GitHub Actions workflow, and generic shell CI variant, verified by fresh-repo install and `doctor.py` run succeeding on a fixture repo
- [x] 2.6 Mutation-test lane plus evidence gate logic and add path-traversal plus malformed-input tests, verified by mutation report with kills versus survivors published
- [x] 2.7 Run spec-first and router task evals (3 prompts each with and without skill) plus trigger evals (8 should plus 8 near-miss per skill) and record deltas in pass rate, tokens, and time, verified by `evals/results-router-spec-first.md` with negative deltas retained
- [x] 2.8 Review slice learnings and adjust conventions for remaining skills, verified by decision note in change recording what changed and why

## 3. Remaining IC Skills

- [x] 3.1 Build `context-pack` skill with source-link plus staleness-date brief template and lane-proportional depth, verified by context-gap test fixture resolving correctly with brief attached
- [x] 3.2 Build `review-by-intent` skill with AI failure-mode checklist and lane-mapped review notes, verified by intent-mismatch fixture producing a blocking verdict naming the violated criterion
- [x] 3.3 Build `decision-trace` template composing trace blocks from spec plus review plus session metadata with redaction rules and lane-proportional sizes, verified by reconstruction dry-run where a fresh agent explains the change from trace alone
- [x] 3.4 Build `verify-and-evals` skill with red-to-green requirement, judge-caveat documentation, and incident-to-eval conversion guide, verified by sample eval with failing-then-passing test evidence present
- [x] 3.5 Build `ship-and-observe` skill with lane-scaled rollout checks, agent-visibility record format, and unplanned-loop runbooks that open a new intent, verified by Critical fixture denying ship readiness without rollback plan
- [x] 3.6 Build optional `learning-mode` pairing guide with explain-back expansion, verified by junior-path walkthrough producing guided questions instead of a single statement

## 4. Leader Skills and Policy

- [x] 4.1 Build `autonomy-policy` skill with trust tiers, per-lane escalation rules, fill-in policy template, and phased rollout plan, verified by unattended-action fixture held for escalation with tier rule cited
- [x] 4.2 Build `ai-readiness-and-metrics` skill with readiness scoring, quality-weighted metric set, Goodhart warnings, and dividend-reinvestment guidance, verified by sample report recommending quality-first reinvestment with warnings present
- [x] 4.3 Document each skill's primary audience plus cross-audience notes and trigger phrases, verified by trigger-eval descriptions audit passing for all shipped skills

## 5. Tooling Hardening and Security

- [x] 5.1 Complete unit tests for every script with stdlib-only and no-network constraints enforced, verified by full test suite passing with network-disabled run
- [x] 5.2 Run static security scan, fix findings, pin versions, generate SBOM, and write short STRIDE threat model including trace PII and admin-bypass risks, verified by clean scan report plus `SBOM` and `THREAT-MODEL.md` present
- [x] 5.3 Add COMPATIBILITY and versioning policy plus hook and CI version pins, verified by version-check test passing against policy

## 6. Full Proof Suite

- [x] 6.1 Run all remaining task evals per skill (leader, IC, edge case each with and without) and publish deltas, verified by `evals/results-full.md` with pre-registered criteria applied and negatives retained
- [x] 6.2 Run full trigger-eval battery per skill and iterate descriptions until accuracy target met, verified by precision and recall table published per skill
- [x] 6.3 Run ceremony benchmark timing human approvals for Lite, Standard, and Critical versus flat approval chain, verified by benchmark table with counts and minutes published
- [x] 6.4 Run context-gap test and six-month reconstruction test across lanes, verified by both test reports stating pass or fail with evidence excerpts
- [x] 6.5 Publish footprint report (total always-loaded tokens and per-skill SKILL.md sizes), verified by measurement script output committed

## 7. Packaging and Adoption Docs

- [x] 7.1 Write README with 10-minute quickstart, 60-second demo transcript, suite-to-SDLC-stage diagram, adoption order, and factual dated comparison table admitting where incumbents win, verified by quickstart executed verbatim on a clean checkout
- [x] 7.2 Write LIMITATIONS.md read-first (gate meaning, admin bypass, non-coverage including regulated compliance, known gaps) plus adoption-position table and claims ledger tagging every non-trivial claim report-stated, measured-here, or extrapolated, verified by ledger audit with zero untagged claims
- [x] 7.3 Add one-command install, MIT license, CHANGELOG, CONTRIBUTING with skill-quality checklist, and thin adapters plus docs for spec-kit, Superpowers, and OpenSpec, verified by install plus adapter smoke tests passing

## 8. Integration Verification

- [x] 8.1 Run `openspec validate --strict` for the change and the full test plus scan suite together, verified by zero errors and reports linked from the results summary
- [x] 8.2 Publish results summary stating plainly where the suite wins, ties, and loses with links to all proof artifacts, verified by summary present at `evals/results-summary.md`
