# Current actual-loader footprint

- Tested skill revision: `e692000a16984e824c759dc7bd09a5c150eb990b`
- Provider/model: `Agent Router` / `agentrouterr/gpt-5.6-sol`
- Probe evidence SHA-256: `7110972ae5f710da46545bbad6a68512d934b0c51048c017afd99fa8bea192d6`
- Probe execution: 15 attempts, 417,216 input tokens, 853 output/reasoning tokens, USD 0 reported cost
- Validation status: **VERIFIED**

## Three-part footprint

| Measure | Exact bytes | Observed tokens |
|---|---:|---:|
| Description catalog | 2,629 | 1,039 |
| Ten skill bodies | 38,239 | 10,929 |
| Maximum per-lane product context | n/a | 5,179 |

## Lane checkpoints

| Lane | Loaded product skills | Loaded body tokens | Catalog + loaded tokens | Unexpected | Repeated |
|---|---|---:|---:|---:|---:|
| Lite | `ai-sdlc` | 1,552 | 2,591 | 0 | 0 |
| Standard | `ai-sdlc`, `spec-first` | 2,810 | 3,849 | 0 | 0 |
| Critical | `ai-sdlc`, `spec-first`, `verify-and-evals` | 4,140 | 5,179 | 0 | 0 |

## Accounting Boundary

- Catalog tokens are the exact initial-input delta between matched empty-skill prompts with and without the ten product descriptions.
- Body tokens are the observed incremental model input after each Kilo `skill` tool result, including its loader wrapper and tool-call transcript.
- Lane totals report product catalog plus product skill loads. They do not claim the host agent's unrelated base system context.
- `evals/loader-record.json` binds every body value to its committed source hash; `evals/loader-probes.json` records raw-event hashes, step token fields, tool names, truncation state, and the matched catalog control.
