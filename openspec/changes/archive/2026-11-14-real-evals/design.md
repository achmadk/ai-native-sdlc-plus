# Design

## Context

See [proposal.md](proposal.md) and the `verify-evals` and `governance` deltas. The current trigger harness embeds 80 positive and 80 near-miss prompts in Python, reads each full skill body, and tests only whether two query words occur in the preassigned skill. Four descriptions contain fixture-specific `Not for:` lists, and the matcher explicitly parses those lists. Its report is manually maintained, has no CI observer, and cannot expose cross-skill or external-skill confusion.

Task results are also manual. Six exact prompts survive for `ai-sdlc` and `spec-first`; the other 24 prompts, outputs, rubrics, model identities, repeats, and transcripts are absent. Existing ceremony registration provides a useful JSON-validation pattern, but it is not a provider or replay layer. There is no aggregate verification receipt, current-claim observer, provider boundary, or machine-readable actual-loader record covering all three lanes.

Evaluation tooling stays repository-only, outside the install/wheel payload. External distractors cannot live under `skills/`, whose source inventory must remain the ten product skills. Live provider access is an explicit exception to the normal offline script policy; default tests and CI remain network-free.

## Goals / Non-Goals

**Goals:**
- Freeze realistic selection and task cases before observing model results or rewriting descriptions.
- Record bounded live runs once, then reproduce scoring and reports offline from committed, provenance-checked inputs.
- Separate catalog selection, agent discovery, skill invocation, task quality, and loaded-context measurements so one cannot be claimed as another.
- Produce one machine-readable verification receipt that current documentation claims can reference exactly.

**Non-Goals:**
- No provider SDK, direct HTTP client, hosted service, networked CI, automatic credential discovery, or package publication.
- No cryptographic proof that a provider or human was honest; provider identity, usage, and cost remain reported evidence.
- No skill merge/split in this change unless measured confusion first causes a separately reviewed scope update.
- No rewriting dated historical results, closing other changes' pending proof tasks, or treating planning approval as code review.

## Decisions

### 1. Freeze registrations and catalogs before live execution

Add versioned machine-readable registrations under `evals/` for selection cases, task cases, criteria, catalog snapshots, and external-source provenance. Selection contains at least 30 should-trigger and 30 near-miss cases across all ten product skills, unique IDs, development/held-out splits, expected/allowed/forbidden selections, three or more repeats, finite request/token/cost limits, and pass criteria. Task evaluation contains three cases per skill (leader, IC, edge), condition-independent assertions, repetitions, and judge/human-review rules.

The baseline product catalog is a committed snapshot of the ten current frontmatter descriptions with source paths and hashes. External OpenSpec and Superpowers entries contain only bounded names/descriptions plus source URL, retrieval date, upstream revision, license/provenance, and content hash. They remain data under `evals/`, never discovered product skills or executable instructions.

The registration must be committed before any live run. Development cases can guide description edits. Held-out cases are evaluated only in the final paired run, where baseline and candidate catalogs are sent in randomized order. This is a procedural holdout backed by immutable inputs, not a claim of cryptographic blindness.

Rejected: keeping cases in Python or editing them after a miss. That repeats the current self-referential benchmark.

### 2. Score selection with labels, not another model

Create a selection evaluator that presents the full registered catalog and asks the provider under test for a bounded list of skill IDs. It validates IDs, scores expected/allowed/forbidden selections, emits per-case outcomes and confusion pairs, and aggregates precision/recall without a composite quality score.

No judge model is needed for selection because labels are preregistered. A model judge remains optional for free-form task output only. Deterministic assertions run first; any judge record includes model/rubric identity, randomized condition labels, calibration cases, known blind spots, and a sampled human spot-check result.

The existing `trigger_eval.py` and its report remain a dated historical experiment. Current prose renames its metric `lexical overlap`; it cannot satisfy model-selection acceptance.

Rejected: using free-form judge opinions for routing. Exact registered labels are cheaper, replayable, and easier to audit.

### 3. Use a shell-free provider command protocol

Live mode reads a JSON argv array from an explicit environment variable and launches it with `shell=False`. Requests and responses use versioned JSON Lines over standard streams. The child receives a minimal environment plus explicitly named credential variables; variable names, never values, are recorded. Tests use a local process double.

Each normalized record contains case/split/condition/repeat, provider/model, selected IDs or task response, request/catalog/registration/revision hashes, usage, self-reported cost, timestamp, and redaction status. Persistent writes scan bounded fields for configured credentials and existing secret patterns. Missing or malformed usage never becomes zero.

The runner checks the request cap before every call and refuses a next call that can exceed the monetary cap. A provider unable to report cost may produce request/token observations, but cannot satisfy a monetary-cap claim. Live mode requires separate user authorization; replay mode refuses to invoke a provider.

Rejected: direct provider HTTP integrations. They add credentials, dependencies, and provider policy to the product runtime.

### 4. Make replay the CI contract

Replay validates schema, unique record identity, case/catalog/request/revision hashes, repeat completeness, and transcript redaction before scoring. It then regenerates normalized selection/task results byte-for-byte apart from explicitly excluded presentation timestamps. Any mismatch, missing repeat, duplicate, unknown skill, or partial condition fails closed.

CI tests use committed synthetic fixtures and, after an authorized run, committed redacted transcripts. No default CI path reads provider environment variables or needs network access. Catalog-level selection is always labeled separately from live agent loader discovery or automatic skill invocation.

### 5. Rewrite descriptions only between registered measurements

After the baseline development run, replace each product description with at most two sentences: what the skill does and when it applies, with at most one natural-language scope sentence. Remove literal trigger lists and hobby-word exclusions. Replace the template test that requires `Triggers:` with structural description checks and selection-regression fixtures.

Use development confusion pairs for edits. Run the final held-out comparison once against both the frozen baseline and candidate catalogs. Preserve all misses and repeats. Skill membership remains ten unless evidence triggers a new proposal decision.

### 6. Reconstruct task evals on the same envelope

Create the missing task prompts and rubrics as a new registration rather than pretending the historical aggregate tables are replayable. For every skill, record with-skill and baseline conditions using the same provider/model/settings, case, repeat policy, and order randomization. Store raw bounded responses needed by assertions, token/time/cost observations, and judge/human records when used.

Historical Markdown stays dated. The current report is generated from replayable records and reports `k/n`, spread across repeats, every negative delta, and unavailable fields.

### 7. Aggregate existing verification without hiding failures

Add `scripts/verify_all.py` as a foreground orchestrator over fixed trusted command vectors for unit discovery, `tests/mutate.py`, `scripts/doctor.py --root . --json`, and footprint verification. Preserve each native exit status. Where a stage lacks structured output, add a backward-compatible JSON mode rather than scrape decorative prose.

The receipt uses an atomic temporary-file replacement and records schema version, tested commit, relevant dirty state, UTC time, Python/platform, command argv, duration, exit/status/counts, sanitized output digests, skipped/unavailable capabilities, input hashes, and overall result. A failing run still writes a failure receipt and exits nonzero. Relevant input hashes prevent a later docs-only receipt commit from recursively invalidating its tested source revision.

Footprint records exact catalog/body bytes and consumes matching actual-loader accounting for catalog, router, selected bodies, repeats, and unexpected content across Lite, Standard, and Critical. Without it, token and maximum-lane fields remain unverified; `chars/4` is never promoted to observation.

### 8. Validate only explicitly marked current claims

Use unique, bounded claim markers adjacent to current result text in `README.md`, `LIMITATIONS.md`, and `PATCH-NOTES.md`. Each marker names a receipt JSON path and expected unit/status. A focused test resolves markers against `evals/results/latest.json`, verifies relevant input hashes, and reports exact mismatches.

Dated historical counts without current markers are left alone. This prevents a broad number scanner from rewriting release history or mistaking dates, versions, and old negative results for current claims.

## Risks / Trade-offs

- **[Risk] Corpus authors tune to known cases** -> Freeze registration first, separate development/held-out reports, run held-out only after edits, and retain every transcript.
- **[Risk] Provider output or cost is incomplete** -> Enforce request limits independently, mark cost unverified, and never infer missing values.
- **[Risk] External descriptions change or carry instructions** -> Pin bounded attributed snapshots and treat all catalog text as data, not executable guidance.
- **[Risk] Transcripts leak secrets** -> Use synthetic prompts, minimal child environment, bounded fields, credential/secret scanning, and fail before persistence.
- **[Risk] Replay is mistaken for a fresh live run** -> Record mode and source transcript IDs prominently; replay proves deterministic scoring only.
- **[Risk] Aggregate verification becomes slow** -> Keep stages foreground and individually timed; reuse existing CI stages, but never skip mutation to manufacture a passing full receipt.
- **[Risk] Claim checks erase history** -> Validate only explicit current markers and preserve unmarked dated records.
- **[Risk] Actual loader tokens remain unavailable** -> Publish exact bytes and `unverified` token fields; acceptance remains incomplete until an authorized matching loader record exists.

## Migration Plan

1. Start apply only on a new request. Reclassify final paths, record a fresh named Critical implementation approval, and leave unrelated active-change tasks unchanged.
2. Add failing-first schema, corpus, provider-double, replay, cap, redaction, and claim-drift tests. Implement registration validation and offline replay before any live call.
3. Commit the registrations, baseline catalog, external provenance, and fixed criteria with explicit commit authorization. Do not inspect provider results before that commit exists.
4. Obtain separate authorization for provider spend/credentials, run development baseline, rewrite descriptions, and run candidate development cases. Preserve failures and costs.
5. Reconstruct and run paired task evals. Finalize descriptions, then run the paired held-out selection comparison once with at least three repeats.
6. Implement aggregate verification, actual-loader receipt validation, current-claim markers, and deterministic replay in CI. Run focused and full Windows/WSL suites plus all mutation checks in the foreground.
7. Validate OpenSpec and Critical evidence, then obtain two independent human reviews. No agent-generated reviewer identity or approval is accepted.
8. Roll back by restoring the prior descriptions and current-claim text while retaining registrations, transcripts, and negative results as dated evidence. Disable live provider configuration without changing offline replay or runtime entry points.
