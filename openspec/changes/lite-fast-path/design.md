## Context

See [proposal.md](proposal.md). This change consumes the command/runtime contract in [WS3's design](../one-front-door/design.md); that proposal is not evidence that WS3 is implemented. The existing `spec-first` contract already exempts Lite from additional pre-build approval, while retaining tests and trace at merge. Its intent template places Intent and Plan in a Lite PR, so the new draft includes those plus Trace rather than adding another authored spec.

`evidence_check.py` already computes the lane, reads a body, detects evidence, applies the narrow non-executable exemption, and exposes JSON. Local warning-mode exit zero does not mean every requirement passed. `openspec/config.yaml` currently has the schema plus commented examples. `evals/ceremony-benchmark.md` mixes limited timing with estimates, `evals/footprint.md` uses `chars/4`, and `lane_backtest.py` is explicitly path-based.

The user chose actual agent/loader evidence for tokens, not declared payload size. A selected harness/run must supply input provenance and token accounting; absent evidence remains unverified. This does not authorize a live run, tooling install, model override, or spend. Cross-cutting orchestration, active instruction configuration, and measurement design make this design necessary; it is not skipped.

## Goals / Non-Goals

- Reduce duplicate authoring for eligible Lite changes while reusing the existing classifier/checker and preserving all actual obligations.
- Keep the command deterministic from explicit inputs, read-only by default, and separate from measurement/report generation.
- Measure only what the registered run actually observes, separating payload layers, human/tool interactions, and hosted unknowns.
- Do not add stronger WS5 test-execution/authorship attestation, tune WS6 trigger descriptions, implement WS2 adapters, or change hosted settings here.
- Treat finite lane budgets, harness identity, and case boundaries as required preregistration inputs, not values inferred from a successful-looking run.

## Decisions

### 1. A bounded Lite command over the WS3 interface

Proposed invocation:

```text
sdlc lite --base REF [--head HEAD] [--repo-root PATH] [--config FILE]
          [--intent TEXT] [--redgreen RECEIPT] [--output FILE] [--json]
```

Require an explicit base; default head to HEAD and repository to the current working directory. Resolve both revisions to immutable identities before gathering facts. This first contract checks committed changes, not a guessed working-tree/untracked diff or inferred remote default branch. Report a missing base, empty range, or failed Git inspection honestly. There is no `--lane` or `--present` shortcut.

```text
explicit revisions --> real strict classifier --> Lite? --> factual draft --> real checker
                                                 |                              |
                                                 no                             v
                                                 v                         result/missing
                                          normal workflow

authorized run/loader records ---------------------------> measurement report
                                                            (never an exemption)
```

Implement the composer as a small command module, provisionally `scripts/lite.py`, registered in WS3 and its owned payload/command adapters. Invoke the selected runtime's existing lane and `check evidence` interfaces with fixed argument vectors, immutable revisions, and consistent configuration. No helper lookup from inspected data and no shell interpolation. Native helper failure or inconsistent structured output is not a passing Lite result.

Use fail-closed evidence checking locally, without claiming a hosted run. Send the draft as stdin and disable optional file-summary side effects for this composition call. Preserve direct helpers' existing local/CI behavior; the Lite command must not treat the helper's local warning exit as success. Keep underlying policy in the checker, not in duplicated lists inside the composer.

Exit 0 means the eligible local workflow's required checks passed; 1 means missing/conflicting evidence or non-Lite eligibility; 2 is usage; 3 is inspection/tooling failure. For non-Lite input, report the actual lane and normal workflow rather than publishing a ready Lite draft. Missing required content remains actionable even when a preview is available.

### 2. Draft facts, not undocumented decisions

Use `--intent` or usable author-recorded commit text for Intent. Include a short factual Plan for the checks being performed. Trace can reference resolved revisions, diffstat/change metadata, existing assistance trailers, and supplied receipt facts. Escape untrusted Markdown/control text and do not inflate filenames/statistics into an invented business rationale.

Do not generate `Approved-by` or human-review attestations from free-form trailers. Missing rationale, attribution, alternatives, and accepted-risk judgments are explicitly not recorded; the draft is not a reconstructed human review. This retains the existing lane-proportional trace and merge-review obligations rather than claiming the drafting command completes every review requirement.

A supplied red/green receipt is bounded input, with schema and revision consistency checked. A valid matching receipt can be summarized as reported evidence, with its hash/source; it is not authenticated execution or a substitute for changed-test evidence. Do not echo arbitrary command tails or secrets. Explicitly bad or mismatched input is an error/conflict, not silently ignored to obtain a pass.

Default output is a PR-body draft plus clear diagnostics, or one documented JSON result. It does not mutate the repository, create a PR, or commit. `--output` is explicit consent to a safe new output: reject unsafe paths, links, and differing existing content; identical output can be retained. Generated evidence is user content, not an extra owned-runtime record.

### 3. Real project context without a new policy engine

Fill this repository's OpenSpec context/rules with stable facts: Python/Git runtime, canonical scripts/skills, trusted tooling versus inspected data, TDD/evidence conventions, and actual WS3 commands. Preserve the selected schema and unrelated configuration. Avoid volatile test counts, invented approvals, copied private context, or supposed automatic hooks.

Verify that the selected OpenSpec CLI returns the context and relevant artifact rules. These are planning instructions only; runtime classification still uses its existing policy. Protect active OpenSpec config/schema control paths against permissive Lite/non-executable rules as needed. Do not install a custom schema or activate WS2's adapters as part of this change.

### 4. Preregister the experiment before observing results

Use explicit ceremony fixtures and a registration tied to `evals/pass-criteria.md`, with case data such as `evals/ceremony-cases.json`. Freeze the case set, implementation/policy references, lane and comparison flows, measurement checkpoint, repetitions, counting rules, tool/harness versions, permissions, finite token budgets, and handling of failures/unavailable data. The registration must be committed before benchmark execution through separately authorized Git work.

The existing Lite criterion stays under five minutes and zero workflow pre-approvals; do not relax it after a miss. Finite Lite/Standard/Critical token budgets and their scope are required registration parameters selected before any run, never derived from observed loads. Missing values block measurement acceptance. This is configurable experimental input, not a hidden unlimited default.

Keep functional red/green tests distinct from performance/ceremony runs. Unit tests can establish behavior; they do not establish a timing/token claim. Do not change criteria, case labels, permissions, or comparison setup after looking at measurements without reporting the old result and starting a separately reviewed registration.

### 5. Observe time, approvals, and loaded context separately

Provide a small foreground runner/report path, provisionally `scripts/ceremony_benchmark.py`, over the registered Lite/Standard/Critical fixtures and comparison flow. Record executed steps, monotonic elapsed time, results, retries, and explicit interruptions. Begin/end at the registered workflow checkpoint; identify fixture preparation, coding time, bootstrap, human wait, and hosted queues as included or excluded rather than folding estimates into elapsed time.

Report required workflow approval counts separately from actual observed approvals and tool/skill consent prompts. Synthetic fixture metadata is not human approval. Preserve native permission prompts and stricter project rules; do not select a permissive mode after a slow result. A blocked Standard/Critical case records its actual progress and unresolved human input, not a fabricated completed review duration. Local fixture results do not prove production merge latency.

Actual token measurement uses an authorized, identified agent/loader run and retained input/load records plus tokenizer/provider accounting. Capture what was delivered at the declared checkpoint, not just which files the router intended to select. Record source hashes, truncation/reloads/caching distinctions when applicable, and the accounting method. Separate always-visible names/descriptions, router body, selected skill bodies, repeated/unexpected content, and other context.

Do not sum token estimates and call them an observed input count. Provider totals alone cannot attribute a skill body; path lists alone cannot establish actual tokenization. Unobservable private/system context stays separately unverified, not copied into public evidence. No `chars/4` or assembled-payload fallback satisfies the user-selected actual-loader metric. Missing or incomplete loader/accounting evidence leaves that metric pending.

The runner can consume a bounded normalized record from the selected instrumented harness, but validating such a record is not proof the run occurred. Acceptance requires the actual authorized execution and retained source/run identity. Selecting a harness/model/tokenizer and numeric budgets is explicit preregistration input; live calls or new dependencies require separate permission and are not part of the default offline gate/runtime.

### 6. Dogfood the history without inventing missing dimensions

Freeze the repository/range and policy reference for the history report. Reuse `lane_backtest.py` where useful, labeling its path-only/current-policy nature. A full-metadata classification, if reported, must actually use the existing change metadata reader. With no independent expected labels, false-positive/negative rates are unavailable, not the script's default zeros presented as measurements.

Actual PR sizes and workflow rerun/failure counts require identified PR/provider records, obtained through separately authorized read-only collection or retained real records. Commit counts/diffstats are labeled as commits, not silently promoted to PRs. Commit messages about CI fixes do not prove a workflow failed or reran. Record source/run identifiers, units, aggregation, and missing data explicitly.

Write new observations to `evals/ceremony-measured.md` with the paired cases, limits, and dogfood section. Update current documentation to those results only when collected. Preserve old ceremony/footprint tables and their negative/estimated values as dated history; add a supersession/limitation pointer rather than rewriting past data or repeating old shape-level passes as current measured success.

## Risks / Trade-offs

- Drafting could manufacture evidence from insufficient text. Mitigation: explicit input/source references, unknown fields, bounded receipts, no approval synthesis, and real checker results.
- A fast path could downgrade executable changes. Mitigation: immutable ranges, strict native classification, non-Lite refusal, and adversarial mode/rename/control-file tests.
- New context guidance could be mistaken for enforcement. Mitigation: test actual instruction exposure, retain separate runtime gates, and protect active control files.
- Benchmark collection could game the result. Mitigation: committed registration, fixed budgets/permissions/boundaries, paired inputs, retained failures, and no post-run relabeling.
- Loader/provider data may be incomplete or private. Mitigation: actual observed controlled-input accounting, redacted/provenance-only records where needed, and unverified metrics instead of fabricated totals.
- Git history cannot establish every PR or hosted event. Mitigation: explicit source types and unavailable fields; no inferred reruns or historic enforcement claims.
- Stronger execution/authorship guarantees are outside this increment. Keep WS5's scope separate and state what the current structural checks still cannot prove.

## Migration Plan

1. Verify completed WS3 behavior and obtain named approval for this Critical implementation. Re-read the existing criteria and preserve WS2's paused artifacts; planning completion alone does not satisfy a prerequisite.
2. Add failing-first Lite eligibility/drafting/checker tests, then the registered command and installed payload. Keep default output non-mutating and require explicit safe file output.
3. Activate factual context/rules in this repository and verify their actual CLI exposure, instruction safety, and control-path protection. Do not change global settings or customer schemas.
4. Prepare and obtain approval for concrete measurement inputs, including an instrumentable actual loader and finite budgets. Commit registration only when authorized; obtain separate consent before running agents/providers or adding tooling.
5. Execute registered fixtures and actual loader/history collection, retain all results, and publish only measured/qualified values. Missing required observations leave acceptance incomplete, even if functional tests pass.
6. For rollback, retain an external trusted runtime, use the current version's safe owned uninstall, then initialize the selected pre-WS4 distribution with the recorded profiles and use direct native checks. Do not ask an older updater to delete unknown Lite paths. Stop on modified-file conflicts; preserve canonical policy, generated user evidence, and measurement history, and revert guidance only as a reviewed change without lowering gate requirements.
7. Record canonical committed red/green proof, two independent reviewer notes, and measurement/rollback limitations before handoff. No implementation, approval attestation, measurements, commits, or live evaluations occur in this planning request.
