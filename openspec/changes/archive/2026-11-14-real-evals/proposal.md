# Proposal

## Why

The current trigger benchmark measures a keyword matcher against prompts and `Not for:` lists tuned together, while task-eval results are hand-recorded and current verification numbers can drift independently of the revision they describe. WS6 needs preregistered, replayable evidence of real model selection and task behavior, plus a single revision-bound verification receipt that keeps current claims honest.

## What Changes

- Replace the current trigger score as the primary selection claim with a preregistered model selection corpus containing at least 30 should-trigger and 30 near-miss cases across all ten product skills, split into development and held-out sets before execution.
- Evaluate the product skills alongside pinned, attributed OpenSpec and Superpowers skill-description distractors, using at least three repeats per case and exact expected/allowed/forbidden selection labels rather than a second model's unsupported judgment.
- Add a standard-library provider-command boundary for explicitly authorized live recording, with request and cost caps, redacted revision-bound transcripts, and deterministic offline replay for CI. Network access and provider credentials remain outside the default gate.
- Capture a baseline against the registered skill catalog, rewrite all ten descriptions to concise real-language what/when text without fixture-specific stuffing, and compare the candidate catalog on development and held-out cases. Merge or split skills only if separately approved evidence identifies a persistent confusion pair.
- Preserve the old trigger experiment as a dated `lexical overlap` baseline; do not rewrite its historical corpus or results as model-selection evidence.
- Re-run with-skill versus baseline task evaluations on the current revision with registered assertions, token/time accounting, negative-result retention, automated-judge caveats, and sampled human spot-check records where a judge is used.
- Add `scripts/verify_all.py` to run the unit suite, mutation checks, doctor-on-self, and footprint measurement through fixed trusted entry points, then write an atomic structured receipt under `evals/results/` with the tested revision, environment, commands, outcomes, counts, and limitations.
- Add explicit current-claim markers in `README.md`, `LIMITATIONS.md`, and `PATCH-NOTES.md`; tests fail when marked values disagree with the verification receipt. Historical measurements remain dated history rather than being silently updated.
- Non-goals: no hosted service, provider SDK, runtime network dependency, composite quality score, per-person metric, automatic publication, fabricated approval, live-call execution during planning, or changes to unrelated open workstreams.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `verify-evals`: Replace lexical-only trigger confidence with preregistered, repeated model-selection and task-evaluation evidence that can be replayed offline and retains negative results.
- `governance`: Bind current measured claims to a structured revision-specific verification receipt and reject marked claims that have become stale.

## Impact

- Expected planning targets include selection/task corpus and transcript fixtures under `evals/`, the ten canonical skill descriptions, `scripts/trigger_eval.py`, new trusted evaluation and verification orchestration scripts, focused tests and mutation observers, and marked current-result sections in `README.md`, `LIMITATIONS.md`, and `PATCH-NOTES.md`.
- Runtime remains Python 3.8+ and standard-library-only. External model access is optional, explicitly authorized, capped, and performed only through a configured command; CI consumes committed replay records without network or secrets.
- The implementation is Critical because it changes `scripts/**` and `skills/*/SKILL.md`. Apply must classify the final path set, obtain fresh named implementation approval, and preserve trusted-runtime isolation.
- `one-front-door` and `lite-fast-path` retain their pending committed-proof tasks. This change consumes their implemented interfaces and measurement vocabulary but does not mark, waive, or absorb those tasks.
