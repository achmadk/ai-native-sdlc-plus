# Final held-out skill selection comparison

- Tested revision: `e692000a16984e824c759dc7bd09a5c150eb990b`
- Registration: `real-evals-selection-v1` at `569eec7a51e8b8f7ee78c26601560dfd15d3b866`
- Provider/model: `Agent Router` / `agentrouterr/gpt-5.6-sol`
- Cases/repetitions: 20 held-out cases, two catalogs, 3 repeats
- Recorded at: `2026-11-13T14:27:20.425302Z`; cost status: `verified`
- Comparison verdict: **FAIL**

## Catalog outcomes

| Catalog | Exact-label records | Precision | Recall | Input tokens | Output/reasoning tokens | Cost (USD) | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| Baseline | 54/60 | 100% | 100% | 547281 | 17220 | 0 | FAIL |
| Candidate | 54/60 | 100% | 100% | 521541 | 16816 | 0 | FAIL |

Candidate minus baseline exact-label records: **+0**.

## Per-case comparison

| Case | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| sel-ai-sdlc-s-h | 3/3 | 3/3 | +0 |
| sel-ai-sdlc-n-h | 3/3 | 3/3 | +0 |
| sel-spec-first-s-h | 0/3 | 0/3 | +0 |
| sel-spec-first-n-h | 3/3 | 3/3 | +0 |
| sel-context-pack-s-h | 3/3 | 3/3 | +0 |
| sel-context-pack-n-h | 3/3 | 2/3 | -1 |
| sel-learning-mode-s-h | 1/3 | 3/3 | +2 |
| sel-learning-mode-n-h | 3/3 | 3/3 | +0 |
| sel-verify-and-evals-s-h | 3/3 | 3/3 | +0 |
| sel-verify-and-evals-n-h | 3/3 | 3/3 | +0 |
| sel-review-by-intent-s-h | 3/3 | 2/3 | -1 |
| sel-review-by-intent-n-h | 3/3 | 3/3 | +0 |
| sel-decision-trace-s-h | 3/3 | 3/3 | +0 |
| sel-decision-trace-n-h | 3/3 | 3/3 | +0 |
| sel-autonomy-policy-s-h | 2/3 | 3/3 | +1 |
| sel-autonomy-policy-n-h | 3/3 | 3/3 | +0 |
| sel-ship-and-observe-s-h | 3/3 | 2/3 | -1 |
| sel-ship-and-observe-n-h | 3/3 | 3/3 | +0 |
| sel-ai-readiness-and-metrics-s-h | 3/3 | 3/3 | +0 |
| sel-ai-readiness-and-metrics-n-h | 3/3 | 3/3 | +0 |

## Preserved misses and confusions

| Catalog | Case | Repeat | Selected | Missing | Forbidden | Unexpected |
|---|---|---:|---|---|---|---|
| candidate | sel-spec-first-s-h | 1 | ai-sdlc, spec-first, superpowers/brainstorming | none | none | ai-sdlc, superpowers/brainstorming |
| baseline | sel-spec-first-s-h | 1 | ai-sdlc, autonomy-policy, context-pack, spec-first | none | none | ai-sdlc, autonomy-policy, context-pack |
| baseline | sel-spec-first-s-h | 2 | ai-sdlc, autonomy-policy, spec-first | none | none | ai-sdlc, autonomy-policy |
| candidate | sel-spec-first-s-h | 2 | ai-sdlc, spec-first | none | none | ai-sdlc |
| candidate | sel-spec-first-s-h | 3 | ai-sdlc, spec-first | none | none | ai-sdlc |
| baseline | sel-spec-first-s-h | 3 | ai-sdlc, spec-first | none | none | ai-sdlc |
| candidate | sel-context-pack-n-h | 2 | openspec/openspec-explore, superpowers/brainstorming | none | none | superpowers/brainstorming |
| baseline | sel-learning-mode-s-h | 2 | learning-mode, verify-and-evals | none | none | verify-and-evals |
| baseline | sel-learning-mode-s-h | 3 | learning-mode, verify-and-evals | none | none | verify-and-evals |
| candidate | sel-review-by-intent-s-h | 1 | ai-sdlc, review-by-intent | none | none | ai-sdlc |
| baseline | sel-autonomy-policy-s-h | 3 | autonomy-policy, superpowers/brainstorming | none | none | superpowers/brainstorming |
| candidate | sel-ship-and-observe-s-h | 2 | ship-and-observe, superpowers/systematic-debugging, verify-and-evals | none | none | superpowers/systematic-debugging, verify-and-evals |

## Evidence boundary

Catalog selection is not live loader discovery, automatic skill invocation, loaded-context measurement, task quality, or human approval. The held-out results were inspected only after descriptions were frozen, and no description edit follows this report.
