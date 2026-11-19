# Measured Ceremony Benchmark & Dogfood Report (WS4)

> [!NOTE]
> Measured on 2026-11-10 from committed registration `ws4-ceremony-v1-2026-11-10` ([`evals/ceremony-cases.json`](ceremony-cases.json)).
> This report replaces the estimated template times in [`evals/ceremony-benchmark.md`](ceremony-benchmark.md) with foreground-measured timings, explicit approval distinctions, and finite token budgets.

## 1. Preregistration & Method

- **Registration ID:** `ws4-ceremony-v1-2026-11-10`
- **Pass Criteria:** [`evals/pass-criteria.md`](pass-criteria.md)
- **Repetitions:** 3 foreground iterations per case
- **Checkpoints:** `[start]` -> `[preflight]` -> `[checks]` -> `[complete]`
- **Counting Rules:**
  - **Human Approvals:** Strictly recorded named human review sign-offs (e.g. `Approved-by:`). Tool/terminal consents and synthetic fixture metadata are never counted as human approvals.
  - **Tool Consents:** Tracked separately as CLI execution confirmations.
  - **Elapsed Time:** Monotonic wall-clock seconds across checkpoints. Human wait time is not estimated.
  - **Token Budgets:** Finite budgets frozen before benchmark execution: Lite: 8,000; Standard: 16,000; Critical: 24,000 tokens. Without verified loader provenance, token measurements remain `unavailable / unverified` (never substituted with `chars/4` or zero).

## 2. Measured Observations

| Fixture / Case | Lane | Required Approvals | Observed Approvals | Tool Consents | Step Timings (s) | Target Met? | Token Budget | Observed Tokens |
|---|---|---|---|---|---|---|---|---|
| `lite-fixture` | Lite | 0 | 0 | 1 | start: 0.000<br>preflight: 0.005<br>checks: 0.016<br>complete: 0.021 | **PASS** (< 300s, 0 approvals) | 8,000 | unavailable (unverified) |
| `standard-fixture` | Standard | 1 | 0 (stopped) | 1 | start: 0.000<br>preflight: 0.005<br>checks: 0.016 | **BLOCKED** (awaiting spec approval) | 16,000 | unavailable (unverified) |
| `critical-fixture` | Critical | 2 | 0 (stopped) | 1 | start: 0.000<br>preflight: 0.005<br>checks: 0.016 | **BLOCKED** (awaiting 2-person review) | 24,000 | unavailable (unverified) |
| `flat-review-queue` | Baseline | 1 | 1 | 0 | queue wait: unobserved | Baseline | N/A | N/A |

### Key Findings
1. **Lite Fast Path:** Completed in 0.021s foreground execution with 0 human pre-approvals, satisfying the `< 5 min` and `0 pre-approvals` target.
2. **Blocked Cases:** Standard and Critical workflows correctly halted at the check boundary awaiting human authorization; end-to-end human review duration was not fabricated.
3. **Loader Accounting:** In the absence of an authorized instrumented LLM loader session, loaded token counts remain explicitly `unavailable / unverified`.

## 3. Dogfood History (First-Parent Git History Analysis)

Replay of `scripts/lane_backtest.py` across 24 first-parent commits on `HEAD` (`b608deae0a28`):

- **Commits Analyzed:** 24 first-parent commits
- **Retroactive Lane Breakdown:**
  - **Critical:** 20 (83.3%) — matched built-in security, scripts, workflows, or agent control paths
  - **Standard:** 4 (16.7%) — feature, bugfix, or uncategorized repo paths
  - **Lite:** 0 (0.0%)
  - **Unclassified / Skipped:** 0
- **Limitations:**
  - **Path-only Git evaluation:** Reflects retrospective classification against current rules, not historical enforcement at commit time.
  - **Commits vs. PRs:** First-parent commits represent repository commit history, not squashed or merged PR records.
  - **Hosted PR / CI data:** GitHub Actions workflow reruns and failure rates cannot be inferred from commit text and are explicitly `unavailable / unverified`.

## 4. Historical Supersession Note

This report supersedes [`evals/ceremony-benchmark.md`](ceremony-benchmark.md). The earlier 2026-10-02 document recorded estimated authoring times (~2 min, ~15 min, ~45 min). Those numbers are retained as dated historical artifacts and are not reused as current measured performance.

