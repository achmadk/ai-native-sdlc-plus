## Context

See [proposal.md](proposal.md) for motivation and scope. Planning snapshot: `bcd73678bb4a8ec49d08faa87c87cf4ec4e7c91a`, checked 2026-11-09. This is not the eventual red/green baseline; recapture that after the preceding workstreams and before implementation.

The root spec-checker delegates to `skills/spec-first/scripts/check_spec.py`. That checker reads one file, expects native sections/AC mappings, and has an existing Python API and JSON/exit contract. The evidence checker separately verifies local references as regular tracked blobs at the evaluated head. Its trusted-base loading, computed lane, and documentation-exemption rules are existing security boundaries. GitHub checks out the whole trusted tree; `skills/ai-sdlc/assets/ci-generic.sh` currently archives only `scripts/`, so the latter needs an explicit trusted-helper delivery update.

The installed OpenSpec CLI reports `1.11.0`; `specify` is not available on PATH. Current primary-source review covers OpenSpec `1.16.1` and Spec Kit `1.3.2` templates, with rolling Spec Kit manifest references. Those are proposed compatibility targets, not executed compatibility results. Obtaining the target tools requires separate authorization or an already provisioned environment.

The roadmap assigns the front door, evidence-check mode, and runtime/installation lifecycle to WS3 `one-front-door`. WS4 `lite-fast-path` addresses the Lite workflow and ceremony measurements and remains a preceding workstream by the requested order. WS2 consumes WS3's published interface; it does not presume that a `sdlc gate` alias exists or prescribe an unapproved invocation spelling.

Design is required: the change crosses two validators and owned runtime delivery, accepts new untrusted inputs, and ships two upstream integration formats. No design/spec artifact is skipped.

### Reviewed Sources

| Source | Design consequence |
| --- | --- |
| [OpenSpec 1.16.1 concepts](https://raw.githubusercontent.com/Fission-AI/OpenSpec/v1.16.1/docs/concepts.md) | Keep proposals and deltas in their existing change folder. |
| [OpenSpec 1.16.1 schema](https://raw.githubusercontent.com/Fission-AI/OpenSpec/v1.16.1/schemas/spec-driven/schema.yaml) | Retain native artifact dependencies and ADDED/MODIFIED/REMOVED/RENAMED operations. |
| [OpenSpec 1.16.1 customization](https://raw.githubusercontent.com/Fission-AI/OpenSpec/v1.16.1/docs/customization.md) | Project schema templates and `operations.apply/archive.guidance` are supported; guidance is not enforcement. |
| [Spec Kit 1.3.2 README](https://raw.githubusercontent.com/github/spec-kit/v1.3.2/README.md) | Integration-specific delivery and logical command names must not be confused with one universal slash-command spelling. |
| [Spec Kit spec template](https://raw.githubusercontent.com/github/spec-kit/v1.3.2/templates/spec-template.md) and [tasks template](https://raw.githubusercontent.com/github/spec-kit/v1.3.2/templates/tasks-template.md) | Preserve Given/When/Then scenarios, FR/SC references, and story/task organization; replace sample content when authoring fixtures. |
| [Extension API](https://github.github.io/spec-kit/extensions/api.html) | Use the native manifest and declared command/hook mechanisms; a declared hook is not an executed check. |
| [Preset overview](https://github.github.io/spec-kit/presets/overview.html) and [API](https://github.github.io/spec-kit/presets/api.html) | Use composition rather than core overrides; dependency metadata is advisory and command delivery depends on the active integration. |

All links above were read during this planning session. The manifest pages are rolling documentation; validate the actual pinned CLI behavior before declaring compatibility. Do not infer broad version ranges from examples in those pages.

## Goals / Non-Goals

- Use one interpretation of supported bundle layouts, source identities, and test expectations across the validators, while preserving the native input path.
- Keep authoring checks against local files distinct from CI checks against a Git snapshot. Upstream CLI execution belongs in fixture/package verification, not the gate runtime.
- Add evidence metadata to existing upstream tasks/plan documents, not a mirrored specification, a new authoring framework, or a test-results attestation format.
- Consume WS3's public evidence-check and runtime-location/ownership/lifecycle contracts after they are available, retaining WS4 as an ordering prerequisite. Do not implement either workstream here or substitute an undocumented command.
- Leave live-agent evaluation, test-collection/execution attestation from WS5, hosted policy changes, catalog publication, and trigger-description tuning outside this change.

## Decisions

### 1. Shared interpretation, explicit readers

Add a small standard-library module beside the canonical spec checker, provisionally `skills/spec-first/scripts/spec_inputs.py`. It owns bounded bundle recognition, Markdown/source extraction, and structural mapping validation. The canonical checker uses a confined filesystem reader for authoring. The evidence checker supplies a reader for regular blobs from its explicit evaluated revision. The new module and its loading path must come from the running trusted tooling, never the inspected checkout, CWD, or an input-controlled module path.

```text
Native file -----------------------> existing native validation
OpenSpec folder --+
                  +--> bundle interpretation --> local spec diagnostics
Spec Kit folder --+                         +--> revision-bound CI evidence
```

Native `check()` calls, flags, caps, result shape, and exit meanings remain compatible. Folder inputs are recognized from their supported member layout; incomplete, unknown, or conflicting layouts fail with a useful diagnostic. No global repository search or automatic conversion is needed. Duplicate parsers in each validator and invoking upstream CLIs inside CI were rejected because they create drift or deployment dependencies.

### 2. Bounded profiles rather than arbitrary upstream customization

| Profile | Required members | Context and governance sources |
| --- | --- | --- |
| OpenSpec | `proposal.md`, at least one `specs/**/spec.md`, `design.md`, `tasks.md` | Proposal supplies intent; deltas supply acceptance units; design supplies constraints/plan; tasks supplies mappings and approval metadata. |
| Spec Kit | `spec.md`, `plan.md`, `tasks.md` | Spec supplies feature intent, native scenarios, status, and FR/SC context; plan supplies constraints/scope; tasks supplies mappings and approval metadata. |
| Critical extension of either | `threat-note.md`, `rollout-plan.md` | Required in addition to the complete base profile; headings/comments/placeholders alone do not qualify. |

Additional upstream research/support files are not recursively ingested merely because they exist. Unsupported custom layouts are diagnosed, not guessed. A directory path selects members; it is never itself a substitute for tracked file evidence. `skip_specs`, completed checkboxes, or workflow state do not grant policy exemptions.

For Critical OpenSpec references, an absent explicit intent link can resolve to the bundle's proposal. If an explicit intent link is supplied, validate that link and do not hide its failure. Spec Kit retains an explicit Critical intent reference, which can point to an appropriate existing feature document; it does not need a native-format duplicate.

### 3. Source-native mappings in the existing tasks document

Use one `## SDLC evidence` section in `tasks.md`, containing approval metadata and a bounded table with `Source`, `Unit`, `Test`, `Fails before`, and `Expected result` columns. Source paths are bundle-relative; test references remain repository-relative under the existing test-reference rules. This is supplementary evidence, not another specification or an execution-results manifest.

The `Unit` cell encodes a native identifier tuple as a JSON array, avoiding delimiter collisions without assigning AC numbers. OpenSpec scenario tuples contain operation, requirement title, and scenario title; removal tuples contain the removed requirement; rename tuples contain both names. Spec Kit scenario tuples contain the native story identifier and numbered scenario. Escaped Markdown pipes must survive decoding. Unknown, duplicate, ambiguous, or dangling units fail.

Scenario outcomes come from their native THEN content; the mapping must not replace that outcome. Operation-only deltas require an explicit `Expected result` and a test/fails-before mapping, so removal-only changes cannot pass with zero criteria. Spec Kit FR/SC identifiers remain source context; scenario mappings do not establish semantic coverage of every free-form requirement or metric.

Keep the existing criterion caps for normalized acceptance units. Preserve approval semantics: OpenSpec status comes from the SDLC block; Spec Kit status comes from its native spec header; named approval metadata is recorded explicitly in the tasks block. A draft never becomes approved because an upstream workflow says complete. Existing flags still distinguish drafting from approval-required and test-files-required checks.

The shared interpretation checks imported structure and mappings, but neither validator executes mapped tests or authenticates a human identity. Malformed test references retain the existing validation behavior and its documented limits; WS5 owns stronger execution/collection evidence. Renumbered Spec Kit scenarios and semantic edits still require review, just as reusing a native AC identifier does.

### 4. Snapshot and diagnostic safety stay fail-closed

In CI, enumerate only the declared profile members under the selected literal Git path and read their bytes at the evaluated head. Every selected member must be a nonempty regular blob. Preserve existing path confinement, metadata exclusion, literal-path handling, and Git-error classification; reject selected symlink/gitlink members and unsafe references. Never fall back to newer or working-tree contents.

Bound a bundle to 64 selected Markdown files and the existing `MAX_BYTES` budget in aggregate; apply the current criterion cap after normalization. Bound enumeration/read operations and retain Git timeouts. Invalid UTF-8 and dangerous hidden controls are errors. Scan raw selected content for the existing secret tripwires before emitting source-based diagnostics, including content in comments; comments and fences do not supply semantic evidence.

Diagnostics identify file, line, and safe unit context without echoing secret values or allowing workflow-command injection. Missing/malformed evidence is a validation failure; an unavailable revision or failed inspector read is a tooling failure. External URL evidence keeps its existing explicitly unverified behavior and is never fetched as a bundle.

### 5. Native OpenSpec package, with honest conditional semantics

Package `adapters/openspec/sdlc-governed/schema.yaml` and its native templates; do not activate it in this repository as part of WS2. Retain the core artifact types and add `threat-note`/`rollout-plan` with instructions that create them only for Critical changes. Include them in the tasks dependency set so the planning workflow evaluates their conditions, using its deliberate conditional-skip flow for Standard rather than inventing completed notes.

OpenSpec's graph is static and its status is based on files. Do not add an unsupported `when` field, use `skip_specs` for other artifacts, or claim a prompt-level skip is an enforced CLI state. Native workflow instructions handle deliberate skips; the independent gate checks the final computed lane and required files. Verify these distinctions with the actual target CLI/workflow.

Ship `adapters/openspec/config.fragment.yaml` for `operations.apply.guidance` and `operations.archive.guidance`. It names the canonical gate and requires explicit evaluation inputs, but cannot run a process by itself. Document an opt-in merge that preserves existing schema/context/rules/guidance and explicit `--schema sdlc-governed` selection. A new config-rewriting installer or automatic default-schema switch was rejected.

### 6. Separate Spec Kit extension and preset

Under `adapters/spec-kit/extension/`, use native `extension.yml` schema version `1.0`, a namespaced `speckit.sdlc.gate` command, a declared before-implementation hook, and a small executable delegate. This is the extension's command name, not a claim that the front door has a same-named subcommand. The delegate uses WS3's documented evidence-check/runtime invocation and propagates output and exit status; no shell interpolation of evidence, policy copy, automatic installation, or success-on-missing-runtime fallback is allowed.

Under `adapters/spec-kit/preset/`, use native `preset.yml` schema version `1.0` and `provides.templates` contributions with `strategy: append` for `plan-template` and `tasks-template`. Add missing governance context, mapping, approval, and Critical-artifact guidance while retaining core content. Do not ship replacements of `speckit.specify`, `speckit.plan`, or `speckit.tasks`.

Declare the companion extension/version constraints, but independently check runtime availability: the preset dependency warning is not enforcement. Validate actual manifests, active-integration materialization, and composed templates with Spec Kit `1.3.2` before advertising that profile. Use one explicitly selected supported integration in isolated tests; the generic integration does not demonstrate command registration. Do not claim all integrations or real-agent execution from that result.

### 7. Distribution and verification remain scoped

Extend the owned install manifest for the shared module and adapter payloads after reconciling WS3's accepted runtime/lifecycle contract. Test the root shim, canonical skill entry, and installed runtime from an unrelated CWD, including native Windows paths. Keep all ten product skills; update only the body of `spec-first` and focused adoption/compatibility docs to describe the new inputs, not its discovery/trigger metadata.

Update generic CI extraction to include the shared helper from the trusted base, not the head. Preserve older bases whose checker does not need that helper: inspect the base for the exact helper before extending the archive inputs, rather than making a missing new path invalidate an otherwise usable old archive. If the running base checker requires a missing or unusable helper, fail as a tooling error; never fall back to head-controlled code. Cover legacy scripts-only bases, new complete bases, missing dependencies, and malicious head shadows. Do not change hosted settings or the GitHub workflow merely to ship this dependency.

Create CLI-scaffolded fixtures under `tests/fixtures/interop/` with provenance recording executable versions, actual commands, template sources/hashes, and subsequent authoring edits. Both upstream CLIs scaffold workflows/templates rather than invent complete business requirements: fill fixture behavior explicitly, label synthetic data, and never describe those edits as CLI-generated or human approval of this project. No raw template with unfilled behavior qualifies as the positive fixture.

Default regression tests replay those committed fixtures offline. Separate real-CLI package/scaffolding checks must actually run for acceptance; absent tooling is a blocker to those checks, not a successful skip. Test Standard, both single-missing-artifact Critical variants, both-artifacts-present Critical, native fixtures, source mapping failures, and snapshot/unsafe-path controls. Canonical red/green tests must call existing public checker interfaces so the baseline fails by assertion, not by importing a future helper that does not yet exist.

### 8. Workflow mapping and measured adoption

Keep one `docs/INTEROPERABILITY.md` guide mapping the supported `/opsx:*` and logical `/speckit.*` workflow steps to produced artifacts, lane-evidence roles, and remaining gate/human checks. Show integration-specific spellings where relevant. This is separate from the scenario-to-test table: producing a plan, task list, or hook declaration does not prove that its checks ran.

Provide scripted clean-room adoption of the gate into both existing upstream project fixtures. Declare the start/end state, prerequisite versions, included operations, and exclusions before execution. Start with initialized, authored upstream fixtures and measure from the first gate-adoption action through the documented Standard gate attempt. Gate bootstrap/install actions are included when required; upstream-tool provisioning and fixture authoring are recorded as setup. Critical control checks have separately recorded actions, not hidden adoption steps.

Count each logged adoption command or required configuration-edit action once, including retries. Do not count internal function calls as user steps or collapse an entire automation script into one adoption step; show the automation entry command separately from its executed action list. Record tool versions, the evaluated revision, actual steps/counts, and outcomes per upstream tool. A failed or unstarted run is not a completed adoption result. Publish counts as measurements only after execution, and do not change the boundary after seeing results.

## Risks / Trade-offs

- Untrusted bundle content or paths could satisfy the wrong evidence or load head-controlled code. Mitigation: fixed trusted parser location, revision readers, bounded member selection, regular-blob checks, literal paths, and shadowing/escape negative controls.
- Conditional artifact guidance could look stronger than it is. Mitigation: keep the gate authoritative, reject Critical skips, and report native file-status limits instead of creating fake completion artifacts.
- Upstream schema/manifest drift could break installation or resolution. Mitigation: version-scoped profiles, real-CLI fixtures, native validation, and no unsupported compatibility ranges.
- Importing metadata could be mistaken for testing or approval. Mitigation: preserve source identities and verification-level labels; no inferred execution, authenticated reviewer, or hosted result.
- The Spec Kit scenario ordinal can survive a semantic edit. Mitigation: require review of the source and mapping together; this change checks references/structure, not test relevance.
- WS3's runtime and CLI contracts may change before they are available, and WS4 must still precede WS2. Mitigation: keep those prerequisites, recapture the implementation baseline, and stop for a plan amendment if the accepted WS3 interface conflicts with this design.

## Migration Plan

1. Obtain implementation approval for the Critical scope and confirm WS3/WS4 prerequisites. Provision target CLIs only through separately authorized setup; the current machine does not establish the proposed compatibility profiles.
2. Land failing contract tests and recorded fixture provenance, then add the shared adapter and native-compatible validator integration. Ship the complete owned runtime so the trusted checker cannot lose its new dependency. Use base-compatible regular-file intent/spec links for this change's own PR evidence; do not require unmerged bundle support from the trusted base that evaluates it.
3. Exercise native and imported fixtures before activating either upstream package. Validate source and installed entry points, profile limits, mutation controls, and the documented nonzero paths in foreground runs.
4. Run the documented opt-in adoption in isolated existing projects for both tools. Check effective templates, command materialization, direct delegate failures, and preservation of existing configuration/specifications; retain the workflow mapping and measured adoption step counts under the declared boundary. Keep hosted activation and publication separate.
5. For rollback, remove the opt-in preset/extension through the upstream CLI and restore the previous schema/guidance selection without deleting authored evidence. Revert the owned runtime as a complete reviewed release, not selected files. An older checker may reject folder references; it must never silently waive evidence during rollback.
6. Before handoff, record two independent reviewer notes, the approved intent/spec, actual red/green and compatibility results, and residual limits. Canonical proof needs an explicitly authorized committed candidate; no commit is created by this planning request.

## Planning Status

Planning artifact capture is authorized by the user's request to propose this change. Implementation, runtime edits, package installation, independent review, and compatibility/canonical proof are not completed or approved by these documents. All implementation tasks remain unchecked. There are no deliberately skipped planning artifacts or unresolved design choices hidden in the task list; missing prerequisites remain explicit execution gates.

## Apply Preflight, 2026-11-09

[measured here] At the 23:56:41Z prerequisite check, HEAD remained `bcd73678bb4a8ec49d08faa87c87cf4ec4e7c91a`. The OpenSpec change was ready at the artifact level but had 0/24 completed implementation tasks. `scripts/sdlc.py` was absent, neither `sdlc` nor `specify` was on PATH, and `openspec --version` returned `1.11.0`. The intended implementation paths classified Critical; these four planning-file corrections classified Standard.

The user approved corrections only to the proposal, this design, the task checklist, and the upstream-governance-adapters delta. They align the WS3/WS4 roles with `prompt.md` and restore its workflow-mapping and measured-adoption requirements. Task 1.1 remains incomplete; no named Critical implementation approval is supplied by this amendment. No code, dependency installation, other workstream, or execution-proof work starts until the prerequisites and separate authorization are satisfied.
