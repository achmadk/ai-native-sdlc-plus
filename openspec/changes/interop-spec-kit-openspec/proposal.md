## Why

WS2 in `prompt.md` calls for adopting the gate without replacing an existing OpenSpec or Spec Kit workflow. Today the spec linter expects native AC rows and the evidence gate resolves local file links rather than upstream bundles, leaving those users to translate or duplicate their evidence.

## What Changes

- Accept an OpenSpec change folder as a Standard specification and, for Critical changes, resolve its proposal and delta specs as intent and specification evidence. Read the accompanying design and tasks without moving them.
- Accept a Spec Kit feature folder containing `spec.md`, `plan.md`, and `tasks.md` as specification context. Preserve upstream requirement/scenario identifiers and add test mappings to the existing tasks document instead of generating a native-format copy.
- Share bounded format interpretation between the spec linter and evidence gate. In CI, verify every selected local artifact at the evaluated Git revision; folder existence, working-tree edits, or upstream completion flags are not evidence.
- Ship a native OpenSpec `sdlc-governed` schema with lane-conditional threat-note and rollout-plan artifacts, plus an opt-in configuration fragment for apply/archive guidance.
- Ship a Spec Kit extension with a gate command/hook and a separate preset that augments plan/task templates. The command delegates to WS3's published evidence-check interface, using that workstream's actual command contract rather than assuming a `sdlc gate` alias. It does not implement another policy engine or fork core Spec Kit commands.
- Provide one workflow-step-to-evidence mapping guide and scripted clean-room adoption runs for existing OpenSpec and Spec Kit projects, with observed adoption step counts under a counting rule declared before execution.
- Preserve native formats, helper invocation forms, approval semantics, criterion limits, local warning behavior, and CI failure behavior. Document which checks validate structure and which evidence still requires human or hosted verification.

## Capabilities

### New Capabilities

- `specification-interoperability`: Read supported upstream bundles in place, retain source-native test traceability, and verify revision-bound, lane-appropriate evidence without relaxing native behavior.
- `upstream-governance-adapters`: Provide native OpenSpec and Spec Kit adoption packages with explicit compatibility, delegation, workflow-to-evidence mapping, and measured real-CLI adoption contracts.

### Modified Capabilities

- `spec-first`: Permit an existing supported upstream bundle to fulfill the logical intent/specification input without requiring another authored specification format; retain the native lane-specific outputs and human-approval requirement.

## Impact

- Runtime targets: `scripts/evidence_check.py`, the canonical `skills/spec-first/scripts/check_spec.py`, a small shared adapter beside that checker, `scripts/install-manifest.json`, and the minimal trusted-payload extraction update in `skills/ai-sdlc/assets/ci-generic.sh`. The root spec-checker entry point and older trusted-base behavior remain compatible.
- Delivery targets: `adapters/openspec/`, `adapters/spec-kit/`, interoperability fixtures/tests, `docs/INTEROPERABILITY.md`, and focused adoption/compatibility guidance. Core checks remain offline, Python 3.8-compatible, and standard-library-only; upstream CLIs are development verification tools, not gate dependencies.
- The intended implementation scope classifies Critical because it changes evidence enforcement and trusted runtime delivery. The proposal does not supply implementation approval, independent review, or a passing runtime result.
- Dependencies follow `prompt.md`: WS3 `one-front-door` and WS4 `lite-fast-path` precede WS2 implementation. WS3 supplies the front door, evidence-check mode, and runtime/installation lifecycle contracts; WS4 is the preceding Lite-path and ceremony workstream, not the owner of those lifecycle interfaces. This change neither implements those workstreams nor invents their command syntax.
- Acceptance requires actual CLI-scaffolded OpenSpec and Spec Kit fixtures, recorded tool versions and fixture edits, Standard passes, Critical failures until required risk/rollout artifacts are populated, and unchanged native-format results. Adding the gate to each existing upstream project must also have a scripted clean-room run with a measured adoption step count and a matching workflow-to-evidence guide. Missing tooling leaves acceptance pending rather than replacing it with lookalike fixtures or estimates.
- Excluded: a third specification framework, core upstream command forks, new test-execution attestation policy from WS5, automatic catalog publication, tool installation, hosted/settings changes, and edits to other workstreams. This amendment changes planning artifacts only and does not start implementation.
