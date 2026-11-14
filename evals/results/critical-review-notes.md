# Critical review packet: real-evals

## Intent and criterion verification

| Criterion | Status | Evidence |
|---|---|---|
| Frozen 30/30 selection registration and distractor catalog | met | `evals/selection-cases.json`, `evals/catalogs/`, registration commit `569eec7` |
| Capped live recording and deterministic offline replay | met | `scripts/model_eval.py`, `tests/test_model_eval.py`, provider/replay mutations |
| Ten concise descriptions with no fixture stuffing | met | `skills/*/SKILL.md`, Windows/WSL SkillHygiene tests |
| Current paired task evaluation | met, negative result retained | `evals/results/task-eval-current.md`, transcript commit `9054870` |
| Final held-out selection comparison | met, no aggregate improvement | `evals/results/selection-heldout-current.md` |
| Actual loader footprint | met | `evals/loader-record.json`, `evals/loader-probes.json`, `evals/results/footprint-current.md` |
| Revision-bound aggregate verification | met | `evals/results/latest.json` for `8341fe4`, 804 tests and 241/241 mutants |
| Current-claim drift detection | met | marked README/LIMITATIONS/PATCH-NOTES claims and `tests/test_verify_all.py` |

## Threat note verification

| Threat or failure mode | Control and evidence | Status |
|---|---|---|
| Provider command injection | JSON argv, `shell=False`, minimal environment, shell-execution mutant | verified locally |
| Credential or response-secret persistence | explicit environment allowlist, raw response scanning, secret-persistence test/mutant | verified locally |
| Spend or request overrun | preregistered caps, pre-call maximum request cost, persistent held-out/loader attempt ledgers | verified locally; two held-out transient failures recorded |
| Benchmark tuning or held-out leakage | registration commit precedes calls, development-only tuning, frozen candidate before one-time held-out run | verified by Git ancestry and transcripts |
| Transcript substitution or partial replay | request/catalog/registration/source hashes, repeat completeness, atomic writes | verified by tests and mutations |
| External skill prompt injection | pinned bounded descriptions treated as catalog data; no external skill is installed | verified by registration contracts |
| Fabricated token or verification claims | actual Kilo loader deltas, exact-byte fallback, atomic receipt, marked claim validation | verified by loader records, receipt tests, and mutations |
| Hosted enforcement mistaken for local evidence | doctor retains three WARN and two unverified results; reports deny hosted proof | unresolved operational limitation, not represented as pass |

## Rollout plan verification

1. Registration and baseline catalogs were committed before provider calls (`569eec7`).
2. Provider/replay infrastructure and the development baseline were committed before the candidate experiment (`e692000`).
3. Development results informed only the ten description edits; no skill body or membership changed.
4. The held-out comparison ran once after candidate freeze. No description changed afterward.
5. Actual loader probes and reports were added without entering the install/wheel payload.
6. Clean-revision verification passed on `8341fe4`: 804 Windows tests, 241/241 non-equivalent mutants, doctor 0 FAIL, verified footprint. WSL independently passed 804 tests.
7. Current claims reference that receipt; ShellCheck and hosted enforcement remain explicitly unavailable/unverified.

Monitoring signals: model-eval replay/hash failures, claim-marker drift, unit or mutation regressions, doctor FAIL/WARN/unverified counts, unexpected/repeated loader paths, and provider cap failures.

Rollback: restore the previous ten frontmatter descriptions while retaining registrations, raw-result transcripts, negative reports, and the lexical-overlap history. Remove live provider configuration to stop further calls. Repository-only eval scripts and reports can be reverted without a runtime data migration; do not delete evidence already used for decisions.

## Independent human review notes

### Reviewer 1

- Reviewer: Achmad Kurnianto
- Intent/spec verdict: OK
- Threat/rollout verdict: OK
- Findings and recommendation: No findings requiring changes; approve.

### Reviewer 2

- Reviewer: Achmad Kurniawan
- Intent/spec verdict: OK
- Threat/rollout verdict: OK
- Findings and recommendation: No findings requiring changes; approve.

Both distinct named human reviews are complete and recommend approval.
