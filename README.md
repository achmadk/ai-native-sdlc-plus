# AI-native SDLC skills (plus)

Risk-proportional Agent Skills for AI-native delivery: explicit intent before code, governed loops, traceable work — without adding review burden.

Claims convention: [report-stated] = perception-survey respondents report (never measured outcomes); [measured here] = numbers from evals/ in this repo; [extrapolated] = judgment, flagged as such.

## 60-second demo

```
$ python3 scripts/lane.py --paths docs/guide.md
Lite: matched Lite rule docs/**
$ python3 scripts/evidence_check.py --lane Standard --present spec_link test_changes
WARNING: missing evidence for Standard: trace_block, review_notes (local, not blocking)
```

## Install

```sh
npx skills add achmadk/ai-native-sdlc-plus
```

That discovers all 10 skills (`ai-sdlc`, `spec-first`, `context-pack`, `review-by-intent`, `decision-trace`, `verify-and-evals`, `ship-and-observe`, `learning-mode`, `autonomy-policy`, `ai-readiness-and-metrics`) and links them into your agent. Useful variants:

```sh
npx skills add achmadk/ai-native-sdlc-plus --skill ai-sdlc --skill spec-first  # router + spec slice only
npx skills add achmadk/ai-native-sdlc-plus --all                                # every skill, every agent
npx skills add achmadk/ai-native-sdlc-plus -g                                   # global, all projects
npx skills list                                                                # verify / check for updates with npx skills check
```

Manual fallback (no Node.js): copy any `skills/<name>/` directory containing SKILL.md into your agent's skills directory. For the deterministic scripts (lane classifier, evidence gate, doctor), run `sh install.sh` in your repo instead.

## 10-minute first win

1. `sh install.sh` (copies config, templates, CI workflow; 2 min).
2. `python3 scripts/doctor.py --root .` (verify install; 1 min).
3. Classify your next change: `python3 scripts/lane.py --paths <files>` (1 min).
4. Write intent with `skills/spec-first/assets/intent-template.md` (Lite: 5 min).
5. Open the PR with the trace block from `skills/decision-trace/assets/trace-block.md`; CI checks evidence with `--ci`.

## Suite map (skills to SDLC stages)

Plan: ai-sdlc, spec-first, context-pack. Build: decision-trace, learning-mode. Verify: verify-and-evals. Review: review-by-intent, decision-trace, autonomy-policy. Ship/observe: ship-and-observe. Govern/measure: autonomy-policy, ai-readiness-and-metrics.

## Adoption order (experimental -> pilot -> org-wide)

Individual first (router + spec-first + trace), then pilot (evidence gate required in CI, context-pack), then org-wide (policy tiers, readiness metrics). Regulated use: unsupported today (see LIMITATIONS.md).

## How this compares (2026-10-02, factual)

| Area | This suite [measured here] | timwukp/ai-native-sdlc | spec-kit |
|---|---|---|---|
| Lanes scale ceremony with risk | Yes: Lite/Standard/Critical + lane.py | Not found on front page | Not found; SDD + bug-fix + assessment extensions |
| Right-of-code (rollout/observe/incident loops) | ship-and-observe + intent-closing loop | CI gate + privacy scanner | Bug-fix extension adjacent |
| Context packs | Yes, with staleness | Unverified | Unverified |
| Trace as byproduct | Yes, lane-sized PR blocks | Intent chain (heavier, stronger provenance) — they are better here today | Unverified |
| Leader policy + metrics | Yes | Unverified | Unverified |
| Proof battery | Task + trigger + ceremony + context-gap + reconstruction + footprint, negatives published | verify.py model (excellent precedent) + 36/80 control rubric — they are better on worked-example history | Maturity at scale (140k stars, integrations) — they are better here today |

Survey context: 94% use AI, 36% agentic, 6% deeply integrated; 74% faster codegen yet ~78-79% manual PR process; trust ~25-32% zero / ~60% guarded / ~1% full autonomy [all report-stated].
