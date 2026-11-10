## Why

WS4 in `prompt.md` calls for Lite work to have low process overhead without lowering the evidence bar. The current repository has separate checks, scaffold-only OpenSpec context, and ceremony/footprint reports that mix observations with estimates, so neither the fast path nor its cost is established by a repeatable measurement.

## What Changes

- Add `sdlc lite` through WS3's front door. It resolves an explicit committed change range, uses the existing classifier, drafts minimal Intent/Plan/Trace from supplied intent and recorded Git/verification facts, runs the real evidence checks, and reports exactly what remains missing.
- Keep drafting read-only by default, with explicit safe output-file selection. Reject non-Lite, empty, uninspectable, or conflicting inputs without a lane override, invented approval, inferred test execution, or replacement policy engine.
- Populate this repository's OpenSpec context/rules with its real stack and workflow constraints. Keep prompt guidance separate from runtime enforcement and protect newly active agent-control configuration without weakening classification or exemptions.
- Define and execute preregistered Lite/Standard/Critical ceremony fixtures and the comparison flow, retaining observed timings, approval requirements/events, reruns, and failures. Preserve the existing Lite target of under five minutes and zero workflow pre-approvals; publish misses instead of adjusting the bar after execution.
- Measure actual loaded context with recorded loader/input provenance and token accounting, as selected by the user. Separate names/descriptions, router, and skill bodies against finite per-lane budgets fixed before the run. A declared payload or `chars/4` estimate does not satisfy this metric.
- Produce `evals/ceremony-measured.md` and a dogfood case study from observed history and explicit sources for PR sizes, reruns/failures, and overhead. Supersede current estimated claims while preserving historical records and labeling unavailable data honestly.

## Capabilities

### New Capabilities

- `lite-workflow`: A grounded, fail-closed Lite drafting/checking path with no additional workflow pre-approval and real project instruction context.

### Modified Capabilities

- `verify-evals`: Add preregistered ceremony measurement, actual loader/token evidence, and source-qualified dogfood reporting requirements without changing existing red/green or negative-result obligations.

## Impact

- Expected targets: the WS3 command registry, a Lite composer, measurement/reporting tooling and fixtures, owned runtime delivery, focused router guidance, `openspec/config.yaml`, targeted control-file protection, and evaluation/adoption documentation.
- WS3 must be implemented and its command/runtime contract verified before applying WS4. WS2 remains paused until the requested WS3 -> WS4 -> WS2 sequence is satisfied; these proposals do not supply that implementation evidence.
- Runtime remains Python 3.8+, standard-library-only, and offline. Actual loader/provider runs, token-accounting tools, hosted read-only data collection, and benchmark-registration commits require their own authorization before execution.
- The intended implementation classifies Critical because it changes workflow instructions and executable checking orchestration. Gate logic, legacy interfaces, default-lane safety, and required evidence remain intact; planning approval is not a human implementation or review attestation.
- Excluded: WS2 adapters, WS5 execution/authorship attestation policy, WS6 trigger-description tuning, fabricated human or hosted results, package publication, and automatic merge/settings changes. Only the planning artifacts are being created now.
