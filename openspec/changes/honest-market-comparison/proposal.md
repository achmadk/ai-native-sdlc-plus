## Why

The README's comparison omits OpenSpec and uses characterizations that no longer match the primary documentation for several tools. Readers need a dated, evidence-labeled comparison and a concrete example of this toolkit's gate behavior, not unsupported claims of superiority or capabilities that belong to later workstreams.

## What Changes

- Add `docs/COMPARISON.md` covering Spec Kit, OpenSpec, Kiro, BMAD, Superpowers, and the currently relevant Tessl registry/governance platform. Record the reviewed version or rolling surface, primary URLs, and checked date for every row.
- Separate source-reported capabilities, local measurements, and recommendations using `[report-stated]`, `[measured here]`, and `[extrapolated]`. Use explicit scoped uncertainty instead of interpreting missing documentation as absence.
- Rewrite the README's opening into one concise positioning paragraph, a prepared-checkout demonstration of blocked Critical PR evidence, and a pointer for users who already use OpenSpec or Spec Kit. Replace the old comparison with a five-tool summary linking the detailed discussion, with source/date metadata retained.
- Add an offline unittest documentation contract that fails when required comparison rows lack valid source, version/surface, or date metadata. Include negative controls so an empty table or a permissive parser cannot produce a false pass; existing unittest discovery supplies CI execution without changing workflows.
- Preserve runtime commands, evidence requirements, advisory-hook behavior, and the distinction between local gate results and actual hosted enforcement. No product or security setting changes are included.

## Capabilities

### New Capabilities

- `comparison-documentation`: Sourced, versioned, uncertainty-aware tool comparison; a grounded README entry point and blocked-evidence demonstration; and offline validation of the documentation metadata contract.

### Modified Capabilities

None. This adds documentation and its validation contract without changing the lane, evidence, installation, or agent-behavior requirements.

## Impact

- Future implementation is confined to `README.md`, new `docs/COMPARISON.md`, and new `tests/test_comparison_docs.py`, plus this change's records. These paths classify Standard.
- Primary-source discovery has already been performed for the planned rows. It must be refreshed if source state changes before implementation; source descriptions are not independently reproduced feature or performance benchmarks.
- The demonstration uses existing commands and recorded Git history. The sixty-second target applies only after documented prerequisites and checkout preparation, not package installation, network cloning, live PR creation, or hosted CI. A missed timing target cannot be hidden or silently weakened.
- No new runtime dependency, CI workflow edit, agent installation, publication, or live-model evaluation is required. Historical benchmark records and evaluation criteria are not retuned in this workstream.
- Unified CLI work, artifact translators, Lite automation, stronger evidence semantics, model-graded evaluations, adapter generation, and the broader compliance/demo program remain separate workstreams.
- This phase authorizes planning only. WS1 implementation requires the human approval note and a subsequent apply request; proof completion for earlier changes is not WS1 approval.
