## Context

See [proposal.md](proposal.md) and the [comparison contract](specs/comparison-documentation/spec.md). This design is included because source qualification, a bounded documentation grammar, and the demonstration's measurement boundary need agreement before implementation.

Planning uses repository revision `06c2ab56d1f790f17203c586108c53112be563cd`. The current README has no OpenSpec comparison row and includes fixed-depth/IDE-only characterizations that current primary documentation does not support. `docs/COMPARISON.md` and a comparison-specific test module do not yet exist. Existing unittest discovery can run the new check without CI workflow changes.

## Goals / Non-Goals

**Goals:** make tool-selection claims traceable and qualified; give existing OpenSpec/Spec Kit users a clear entry point; demonstrate the implemented fail-closed gate; and catch metadata regressions offline.

**Non-Goals:** a leaderboard, new vendor benchmarking, installation of competing tools, a new runtime CLI, enforcement/approval changes, historical evaluation retuning, agent-description rewrites, or broad compliance-document replacement. No README/test implementation occurs in this planning phase.

## Decisions

### 1. Use reviewed primary sources, not inherited comparison claims

Primary sources below were read on 2026-11-09. These are `[report-stated]` product descriptions and release records, not observed executions or comparative benchmarks. Refresh the affected row before implementation if its source state has changed.

| Tool | Version or surface checked | Primary sources | Consequence for the comparison |
|---|---|---|---|
| Spec Kit | GitHub/PyPI 1.3.2, published 2026-11-06 | [release](https://github.com/github/spec-kit/releases/tag/v1.3.2), [versioned README](https://github.com/github/spec-kit/blob/v1.3.2/README.md), [PyPI](https://pypi.org/project/specify-cli/1.3.2/) | Documents independent SDD/bug/assessment entry points, extensions, presets, workflows, gates, overlays, and catalogs; do not call it inherently fixed-depth or advisory-only. |
| OpenSpec | 1.16.1, published 2026-11-07 | [release](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.16.1), [versioned README](https://github.com/Fission-AI/OpenSpec/blob/v1.16.1/README.md) | Documents core and custom workflows, native installers, and store support; distinguish artifact management from this toolkit's particular gate checks. |
| Kiro | IDE 1.4.121 and CLI 3.1.0 in 2026-11-05 entries; web/autonomous docs are rolling | [docs](https://kiro.dev/docs/), [changelog](https://kiro.dev/changelog/) | Explicitly has IDE, CLI, web/autonomous, ACP, and workflow surfaces; do not label it IDE-only. |
| BMAD | Latest stable release API returned 6.12.4, published 2026-11-07 | [release](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.12.4), [versioned README](https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/README.md) | Documents right-sized planning and direct build paths as well as deeper specialist workflows; cost/ceremony superiority needs measurement, not assumption. |
| Superpowers | 7.0.2, published 2026-11-03 | [release](https://github.com/obra/superpowers/releases/tag/v7.0.2), [versioned README](https://github.com/obra/superpowers/blob/v7.0.2/README.md) | Documents multiple harnesses, verification helpers, and behavioral evaluation results; retain those as publisher-reported evidence rather than ignoring them. |
| Tessl | CLI 0.119.0 in the 2026-10-30 changelog; platform docs are rolling | [docs](https://docs.tessl.io/), [CLI changelog](https://docs.tessl.io/changelog-cli), [platform](https://tessl.io/) | Registry remains relevant, but docs also describe governance, real-task evals, observability, and loops. Do not reduce it to a static registry or claim a fixed cloud version. |

Spec Kit's GitHub and PyPI pages now agree on 1.3.2, resolving the old version discrepancy for this check. Stars, customer logos, publisher performance percentages, and legal assurances are not needed for the decision matrix and should be omitted unless separately sourced and explicitly qualified.

Use a publisher as the authority for its own documented interfaces, not for its criticism of competitors. The reviewed OpenSpec/BMAD/Superpowers/Tessl prose includes positioning claims; do not adopt those as neutral measurements.

### 2. Use one explicit comparison format

The detailed table has six required tool rows. Use columns for tool, version/surface, documented capabilities, fit/limits, evidence qualification, primary sources, and checked date. Keep strengths and limitations on comparable dimensions: workflow flexibility, agent/distribution scope, runtime/setup requirements, documented verification/enforcement, and adoption fit.

Use scoped `unverified` statements when documentation is insufficient, naming the surfaces searched. Tag documented facts `[report-stated]`, local results `[measured here]`, and fit judgments `[extrapolated]`. Do not infer that a capability is absent because this audit did not find it. Distinguish shipped interfaces, extensions, optional services, and release channels.

The README summary has five rows: Spec Kit, OpenSpec, Kiro, BMAD, and Superpowers. Keep version/source/date metadata on each row and link to the detailed table; Tessl remains in the detailed comparison. The new top paragraph describes the currently implemented risk/evidence layer, not an unbuilt universal workflow product. Add an existing-users pointer without claiming WS2 format translation already works.

### 3. Make the blocked example reproducible without publishing

Use the existing checker and a recorded Critical commit range, not a new CLI, `--present`, or a fabricated hosted success/failure. The proposed example is a local replay of the missing-evidence failure mode observed on [PR #4](https://github.com/achmadk/ai-native-sdlc-plus/pull/4): base `e5e8ff20fb732064f9ad38271199b3357b398099`, head `0ee9a1b426778aa4bd2cf45092bf37eb852d52a7`, and an empty stdin body. State that the body is a simplified input, not the original event payload.

Prerequisites are an existing full-history checkout containing those refs, supported Python/Git, and no active step-summary output path. The example runs the current local checker with `--ci --pr-body-file -`; actual GitHub CI uses trusted-base tooling and a fresh event payload. Provide suitable shell spelling for the documented platform rather than assuming Unix `printf` exists in PowerShell.

During planning, this read-only replay returned exit 1, computed Critical, found 16 changed test paths, and listed the six missing metadata requirements. Elapsed time displayed as approximately 0.34 seconds on Windows with Python 3.15.2 and Git 2.45.1.windows.1 at the recorded checker revision. This is `[measured here]` for one prepared-checkout invocation only, not a cold-start, installation, hosted-PR, or comparative performance result.

Implementation must re-run and record the actual command, refs/body identity, environment, date, result, and timing before publishing the sixty-second claim. A missing ref, missing tool, or parser error is not the intended blocked-evidence result. Do not alter the gate or choose easier acceptance criteria after a timing miss; surface a miss for review.

### 4. Check metadata offline, review truth separately

Implement the bounded lint as `tests/test_comparison_docs.py`, using the standard library and normal unittest discovery. No new runtime helper, network check, or CI workflow step is needed. Validate only the two intended tables and their documented columns; reject missing/empty tables, missing or duplicate required tools, malformed cell counts, absent evidence labels, invalid/future dates, and empty version/surface descriptions.

Require HTTPS primary URLs tied to reviewed official repository/domain prefixes. Validate parsed host/path boundaries, not substring matches that accept lookalike hosts. Permit explicitly qualified rolling/unverified version descriptions with a reason, not arbitrary empty metadata. Dates record actual review events; syntactic validation cannot prove that a source was read or that a publisher is correct.

Use in-memory positive and negative fixtures before updating documents. The original repository must fail meaningfully because the comparison is absent/incomplete. Include mutations that remove one source/date/version/evidence field, empty a table, duplicate a tool, and substitute a lookalike source URL. Do not let a parser that finds no rows pass vacuously.

Keep the check offline and deterministic. Link liveness, legal interpretation, feature execution, and model quality remain human or separately authorized evaluation work. Do not use this lint as proof of source truth or agent support.

## Risks / Trade-offs

- Comparison rows could overstate absence or superiority -> qualified evidence classes, symmetric dimensions, explicit limits, and source review.
- Release metadata and rolling product surfaces can diverge -> record exact versions/surfaces and dates; refresh changed claims before implementation.
- README shorthand could erase caveats -> retain row metadata and links, and state implemented versus planned capabilities.
- A local replay could be mistaken for hosted enforcement -> identify its checker/ref/body inputs, prerequisites, and non-hosted boundary.
- A fast timing could omit setup or imply a general benchmark -> report the prepared-checkout boundary and actual reference environment; no cold-start or market-performance claim.
- A passing lint could launder unsupported prose -> limit its claim to metadata structure and require substantive review.
- The validator could become a general Markdown framework -> support the deliberately bounded format and fail ambiguous rows rather than adding dependencies.

## Verification and Migration Plan

1. Obtain the WS1 human approval note and a new apply request; verify scope and source freshness without retuning existing evaluation criteria.
2. Add failing-first documentation-contract tests, including negative controls, while README/COMPARISON remain unchanged. Record assertion failures for the missing/incomplete metadata, not import errors.
3. Create the detailed comparison and update only the approved README surfaces. Keep historical evaluation records dated and separate from current comparison claims.
4. Re-run the blocked-evidence demonstration, inspect its expected missing fields and exit code, and record the timing boundary and limitations. No PR creation or hosted rerun is implied.
5. Run the new lint tests, existing template/reference checks, and the full suite on the selected supported host. Record actual commands, counts, skips, and environment; do not reuse old pass counts as current evidence.
6. Run strict OpenSpec validation and scope/diff checks. Review all claims for sourcing, unsupported absence, unbuilt features, and lost safety caveats.

When an explicitly authorized committed candidate is available, use the existing red/green helper for the focused documentation contract. The base failure must identify missing/incomplete documentation rather than an import or tool error. Keep canonical proof pending when only uncommitted observations exist; do not create a commit merely to manufacture evidence.

No runtime or data migration is needed. If the documentation contract or demo proves misleading, hold publication and correct the claim/format after review; do not weaken runtime gates, backfill measurements, or silently change evaluation thresholds. Publishing, commits, live-agent evaluation, tool installation, and other workstreams require separate authorization.

Approved-by: Achmad Kurnianto, 2026-11-09. The user explicitly approved WS1 implementation for README.md, docs/COMPARISON.md, tests/test_comparison_docs.py, and this change's evidence records. Commits, publishing, tool installation, hosted/settings changes, live evaluations, and later workstreams are excluded. This is scope approval, not a source-truth or independent review attestation.

## Implementation Evidence

- Task 1.1: baseline remains `06c2ab56d1f790f17203c586108c53112be563cd`. Initial changes were prior proof records and this planning directory; they will be preserved. The complete WS1 file scope classifies Standard. No runtime code, workflow, agent, or evaluation-criteria changes are authorized.
- Task 1.2: on 2026-11-09 the versioned Spec Kit 1.3.2, OpenSpec 1.16.1, BMAD 6.12.4, and Superpowers 7.0.2 READMEs were reread. Kiro's live docs/changelog still identify IDE 1.4.121 and CLI 3.1.0; Tessl's live docs and changelog identify its rolling platform and CLI 0.119.0. Sources support configurable processes, multiple product surfaces, and documented gates/evals; they do not establish comparative superiority. No competing product, model benchmark, or new evaluation corpus was executed.
- Task 1.3 RED: `python -B -m unittest tests.test_comparison_docs -v` ran 12 tests in 0.078s. All ten validator/negative-control tests passed; the two published-document tests failed on missing `docs/COMPARISON.md` and the absent required README summary format. No documentation was edited before this assertion-based red result, and no network call is needed by the validator.
- Task 2.1: the detailed six-tool comparison is present and its contract passed (one test, 0.003s). Each row separates documented capabilities from fit judgments, records the reviewed surface/version, and cites primary HTTPS sources checked on 2026-11-09. Unexecuted behavior and current-toolkit limitations are explicit; no claim of comparative superiority or future implementation was added.
- Task 2.2: the approved README surfaces now have a bounded positioning paragraph, existing-users pointer, actual blocked-evidence replay, and five sourced comparison rows. The old unsupported comparison/star/survey assertions within that replaced section were removed; historical evaluation files and runtime code were not edited. All 12 comparison tests passed in 0.055s after the document updates.
- Task 2.3: the documented PowerShell replay returned exit 1 and the six expected missing metadata fields, while recognizing 16 changed test paths. Recorded checker revision is `06c2ab56d1f790f17203c586108c53112be563cd`, inputs are the declared historical base/head and empty stdin, host is Windows/Python 3.15.2/Git 2.45.1.windows.1, date 2026-11-09. Reference observations were approximately 0.30s and 0.681s, both below the declared prepared-checkout target. The POSIX spelling was also executed through WSL and produced the same expected block. No source file, GitHub state, gate condition, or measurement boundary changed to obtain these results.

### Task 3.1 verification, 2026-11-09

[measured here] Native Windows/Python 3.15.2 focused verification ran in the main foreground with the existing temporary directory confirmed first:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; $env:TEMP='C:\Users\ACHMAD~1\AppData\Local\Temp\kilo'; $env:TMP=$env:TEMP; python -B -m unittest tests.test_comparison_docs tests.test_templates tests.test_ci_adapters -v
```

Result: 44 tests in 2.826s, all passed, no skips. This covers the new contract and the existing template/reference and CI-adapter documentation checks, not a fresh full Windows suite.

[measured here] WSL Ubuntu/Python 3.14.4 full verification ran next, also in the main foreground, after confirming the POSIX temporary directory:

```powershell
wsl -d Ubuntu --cd /mnt/d/PROJECTS/PORTFOLIOS/ai-native-sdlc-plus --exec env PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
```

Result: 642 tests in 201.187s, `OK (skipped=28)`: 614 passed, 28 skipped, no failures or errors. Skips were 19 PowerShell installation invocations, two native Windows cross-volume/path checks, three Windows junction checks, two Windows command-line parsing checks, one Windows command fixture, and one ShellCheck invocation. These skips do not establish coverage of those host-specific paths; no tool was installed to change the result.

All 12 comparison-contract tests passed on both hosts. Source inspection and the network-blocking negative control confirm that the validator checks recorded metadata without fetching sources. Published-document failures name the document, and malformed or invalid rows include a line/tool diagnostic. These tests do not validate publisher claims, hosted enforcement, or real-agent behavior. The tested WS1 files remain uncommitted observations, not canonical committed proof.

Spec: openspec/changes/honest-market-comparison/specs/comparison-documentation/spec.md

## Trace

### Change

WS1 adds the detailed six-tool comparison, replaces the approved README entry and five-tool summary, and adds the offline documentation contract. The implementation remains in the working tree; no commit or publication is implied.

### Why

The [approved comparison contract](specs/comparison-documentation/spec.md) requires dated primary sources, qualified claims, and a real blocked-evidence replay instead of inherited market assertions. See the [decisions](#decisions) for the source ledger, bounded format, and measurement boundary.

### Alternatives rejected

- Retaining fixed-depth, IDE-only, or registry-only characterizations would contradict the reviewed documentation. Publisher statements are labeled rather than promoted to independent results.
- Live vendor benchmarks, a general Markdown parser, and a new CI job would exceed the approved need. The standard-library test checks two explicit sections using the existing scanner and unittest discovery.
- Manual `--present` attestations cannot demonstrate CI blocking. The README instead runs the real checker against identified Git revisions and a simplified body, without claiming a hosted replay.
- Creating a commit to obtain a green proof would exceed approval. Task 3.2 stays pending; previous workstreams' receipts are not WS1 proof.

### Test evidence

The [implementation evidence](#implementation-evidence) records the assertion-based red, subsequent green, measured demo, and fresh Windows/POSIX runs with their commands and skips. The README retains both actual demo shell spellings and the checker/base/head identities. The baseline is `06c2ab56d1f790f17203c586108c53112be563cd`; no committed WS1 candidate exists.

### Risk accepted

Source liveness and rolling product behavior can change after the checked date. Metadata validation does not establish source truth, effectiveness, reviewer identity, or hosted enforcement. Achmad approved bounded implementation, not independent acceptance of these residual risks; publication and canonical proof remain outside this approval.

### Provenance

Kilo used primary-source web reads, the OpenSpec CLI, Git, standard-library Python/unittest, PowerShell, and WSL Ubuntu. This trace and self-review were recorded on 2026-11-09. Attribution for the agent-authored WS1 edits: `Assisted-by: Kilo agentrouterr/gpt-6-astra`. This is an evidence-record attribution, not a trailer in an existing commit, and does not attribute pre-existing repository content. Achmad Kurnianto supplied scope approval; no independent reviewer or human authorship of the WS1 diff is attested.

## Review notes

- Task 3.3 self-review: the detailed rows and README summary retain the reviewed versions/surfaces, primary links, dates, and evidence labels. Fit judgments and unexecuted areas are explicit; no publisher performance figure, universal superiority claim, certification, or unbuilt WS2-WS8 capability was added.
- The local demo names its empty-body simplification, full-history/tool prerequisites, expected missing-evidence exit, and timing exclusions. Its measurements do not imply onboarding speed, competitor performance, or a hosted CI result.
- The offline parser rejects missing/empty/malformed tables, duplicate or absent tools, hidden content, missing metadata, invalid/future dates, and lookalike source URLs. Its network guard and document/row diagnostics were exercised; it does not verify prose truth or general Markdown compatibility.
- The new prose uses sourced specifics and ordinary documentation language without fabricated testimonials, unsupported numbers, or decorative assets. Existing README safety caveats outside the approved sections remain unchanged; no UI build or browser interaction is claimed.
- Independent source/implementation review and an independent trace-reconstruction review remain pending. This assistant self-review and Achmad's scope approval are not substitutes. Task 3.2 remains unchecked until a committed candidate is separately authorized; uncommitted red/green observations and the local evidence-section attestation must not be relabeled as canonical or hosted proof.

## Handoff Checks, 2026-11-09

- Task 3.4: `openspec validate honest-market-comparison --strict --no-interactive` returned `Change 'honest-market-comparison' is valid`.
- `git diff --check` passed. Because that command omits untracked files, `git diff --no-index --check -- /dev/null <path>` also ran sequentially for the two new implementation files and all five WS1 planning/record files. No whitespace errors were reported; Git's existing LF-to-CRLF notices were not suppressed and no Git configuration changed.
- `python -B scripts/evidence_check.py --lane Standard --present spec_link test_changes trace_block review_notes` returned `evidence ok for Standard`. Each key was explicitly `attested by --present, not verified`. This checks the declared local evidence set only, not committed spec membership, reviewer identity, canonical proof, or hosted CI readiness.
- `git status --short --untracked-files=all` and the README diff confirmed the WS1 scope: `README.md`, `docs/COMPARISON.md`, `tests/test_comparison_docs.py`, and this change's records. The four pre-existing design/task edits and two new proof receipts for `fix-self-consistency` and `fix-cross-volume-hook-reporting` remain separate and untouched. A tracked-tree diff excluding those prior edits and README was empty; runtime sources, workflows, historical evaluations, and other workstreams were not changed. `git diff --cached --name-status` was empty.
- HEAD remains `06c2ab56d1f790f17203c586108c53112be563cd`. The original WS0 `redgreen-proof.json` still hashes to `241d065709f83cf04bc369c4cf92077ac47f4635` with `git hash-object --no-filters`; its failed history was not overwritten. No WS1 commit, publish, archive, tool installation, settings change, or live evaluation occurred.
- Task 3.2 remains pending at handoff. A separately authorized committed WS1 candidate is required before the focused `scripts/redgreen.py` proof can be generated; the working-tree test results above do not satisfy that requirement.
