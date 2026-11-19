## Context

See [proposal.md](proposal.md) for scope. `scripts/install.py` already preflights collisions, compares whole-file hashes, stages writes, rechecks targets, and publishes version-1 ownership metadata. It accepts exactly the existing top-level and per-file fields. It does not provide update/uninstall/status operations or register native agent files, and its replacement ownership map needs care when preserving additional managed profiles.

The helpers already expose the relevant interfaces: `lane.py`, `check_spec.py`, `check_brief.py`, `evidence_check.py`, and `doctor.py`. The evidence checker has real Git/body and JSON modes as well as explicitly manual attestation. Doctor exposes structured findings and preserves strict-mode failures. Reuse those contracts rather than building another evaluator.

The user confirmed during exploration that root `AGENTS.md` is user-owned canonical policy: preserve an existing file, create a starter only when absent, and retain it on uninstall. This is a design decision, not implementation approval. Cross-module delivery, destructive lifecycle operations, and new instruction surfaces require this design; it is not conditionally skipped.

## Goals / Non-Goals

- Publish a stable front-door contract that WS4 and WS2 can consume, with transparent delegation and explicit tool/data roots.
- Preserve legacy entry points, version-1 ownership, and non-overridable gate boundaries while adding lifecycle behavior in the shared installer engine.
- Generate selected project-local profiles from common sources without global settings, permission/model overrides, automatic hook activation, or network bootstrap.
- Prepare a complete local wheel, not a release or package-index publication. Do not implement WS4's Lite composer or WS2 interoperability here.
- Preserve the ten canonical product skills and historical evaluation records. New command adapters are not additional product skills or evidence of live-agent correctness.

## Decisions

### 1. Publish a thin, explicit command surface

| Command family | Contract |
| --- | --- |
| `init --root PATH [--agents CSV] [--dry-run]` | Initialize the complete owned runtime and canonical policy; add selected profiles. No agents means explicitly reported core-only setup, not inferred client selection. |
| `lane ...` | Forward the existing lane arguments, including its `--repo-root`, config, revision, strict, and JSON options. |
| `check spec ...`, `check brief ...`, `check evidence ...` | Forward each helper's own arguments and stdin; do not invent common aliases that change its parser or semantics. |
| `doctor ...` | Use existing doctor inputs and records, with the grouped default view; retain raw results and strict/explicit-enforcement behavior. |
| `status --root PATH [--json]` | Read owned state, policy source, current files, and invoked distribution without mutation or network. |
| `update --root PATH [--dry-run]` | Reconcile recognized installed profiles and runtime to the invoked distribution, not an unspecified online latest version. |
| `uninstall --root PATH [--dry-run]` | Remove eligible owned project output; retain user policy and unrelated content. |
| `explain CHECK_ID --root PATH` | Explain a known check or safe check family and its next action; never execute remediation. |

`python3 <tool-root>/scripts/sdlc.py check evidence ...` and installed `sdlc check evidence ...` are the integration interface. The Python executable follows the host's supported interpreter; examples/tests distinguish Windows and POSIX. There is no `sdlc gate` alias. `lite` is added later by WS4, not a working-looking stub in this release.

Dispatch uses a fixed command-to-helper mapping in the invoked tool tree. Preserve delegated stdout/stderr, stdin, native options, and exit codes; doctor presentation is an explicit rendering layer over unchanged underlying meanings. New lifecycle commands use 0 for completion, 1 for conflicts/incomplete operations, 2 for usage, and 3 for inspection/I/O failures. Inspecting another repository must not import its code. CI retains isolated, trusted-runtime invocation, not a head or CWD fallback.

### 2. Separate user policy from owned generated output

```text
user-owned AGENTS.md ----+
trusted skill catalog ---+--> deterministic profile renderer --> owned native files
trusted command registry-+                                  --> owned runtime
```

Existing `AGENTS.md` is a read-only input. A missing file gets a clearly identified starter from the trusted distribution, deliberately outside tool-owned deletion state. Do not add block-level ownership or extra version-1 fields. Preflight the planned starter and all owned outputs before publishing anything, and recheck the policy input for races. Reject unsafe/symlink or unreadable inputs rather than replacing them.

Use one renderer/profile registry, provisionally `scripts/agent_profiles.py`, plus the canonical skill resources and instruction source. Render ordinary instruction files from project policy where the target requires them; do not inline untrusted policy into command mechanisms that automatically evaluate shell substitutions. Commands remain thin instructions to invoke the front door with the target root identified. No automatic shell interpolation of supplied arguments or permission/model grants.

Selection is additive: re-running init with another profile does not delete earlier managed profiles. Recover recognized selections from their validated owned destinations; preserve all their records. Deduplicate identical destination requests, reject case/path/content collisions, and test overlapping native discovery roots. Status can compare current renderer output with owned hashes: unchanged owned bytes with newer source input mean regeneration is available; edited output is a conflict.

### 3. Use current, explicit native profiles

The following are proposed surfaces reviewed on 2026-11-10, not executed compatibility claims. Pin and record tested client versions before declaring a profile verified. All locations are relative to the explicitly selected project, never global user directories.

| Profile | Instruction/skill surface | Command surface and limit |
| --- | --- | --- |
| Claude Code | Generated `CLAUDE.md`; `.claude/skills/<product>/` | Supported `.claude/commands/sdlc/<operation>.md` gives `/sdlc:<operation>`; command files are a supported older form now unified with skills. |
| Cursor | User-owned `AGENTS.md`; `.cursor/skills/<product>/` | Current commands are manual skills, e.g. `sdlc-check` with `disable-model-invocation: true`; do not pretend deprecated command files are current. |
| Copilot, VS Code surface | `.github/copilot-instructions.md`; `.github/skills/<product>/` | `.github/prompts/sdlc-<operation>.prompt.md`; prompt files are not a Copilot CLI/cloud-agent feature. |
| Codex | `AGENTS.md`; `.agents/skills/<product>/` | Explicit skill invocation and the CLI; do not invent a custom slash-command file mechanism. |
| Gemini CLI | Generated `GEMINI.md`; `.gemini/skills/<product>/` | `.gemini/commands/sdlc/<operation>.toml` gives `/sdlc:<operation>`; record the actual available Gemini CLI surface, not a silent Antigravity substitution. |
| OpenCode V2 | `AGENTS.md`; `.opencode/skills/<product>/` | `.opencode/commands/sdlc/<operation>.md` gives `/sdlc/<operation>`, not a colon spelling; V2 does not use `CLAUDE.md` as an instruction fallback. |
| Kilo | `AGENTS.md`; `.kilo/skills/<product>/` | Canonical `.kilo/command/sdlc-<operation>.md`; do not create new `.kilocode/` configuration. |

Sources: [Claude skills/commands](https://code.claude.com/docs/en/skills), [Cursor skills](https://cursor.com/docs/context/skills), [Cursor commands](https://cursor.com/docs/context/commands), [Cursor rules](https://cursor.com/docs/context/rules), [Copilot skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills), [Copilot customization matrix](https://docs.github.com/en/copilot/reference/customization-cheat-sheet), [Codex skills](https://developers.openai.com/codex/skills/), [Gemini skills](https://geminicli.com/docs/cli/skills/), [Gemini commands](https://geminicli.com/docs/cli/custom-commands/), [OpenCode V2 instructions](https://opencode.ai/docs/instructions/), [OpenCode skills](https://opencode.ai/docs/skills/), and [OpenCode commands](https://opencode.ai/docs/commands/). Kilo paths come from the bundled `kilo-config` reference consulted in this session. Rolling docs are not proof that every installed client version supports the profile.

Keep generated native copies out of this repository's product-skill discovery surface: test snapshots can be data, and generation tests use isolated target directories. Verify ten canonical product skills separately from native manual-command adapters. Fixture/native-loader checks must identify the surface and level; duplicate/overridden native definitions and untested clients remain visible. WS7 owns the broader loaded/behavior-tested matrix, not an inferred success claim here.

### 4. Extend the existing lifecycle engine, not ownership authority

Reuse the installer's path validation, snapshots, preflight, staging, and owned-hash checks. Separate planning from publication so `--dry-run` and status do not create directories or metadata. Keep version-1 state fields unchanged; `source_manifest` remains the declared source-manifest identity, not proof of a release or approval. Generated records refer to trusted renderer/template sources and hash their actual output; canonical user policy is not owned.

Update uses the currently invoked distribution and validated installed-profile set. No update-to-latest request, remote fetch, or arbitrary plugin module is implied. Preserve recognized older records rather than dropping ownership when assembling a new payload. Legacy entry points continue to use this same engine, with their existing invocation and conflict behavior.

Uninstall validates the whole requested plan before removing recognized, unchanged owned files. A state record alone cannot authorize arbitrary paths: intersect it with trusted current/supported-legacy output definitions, never a broad directory-delete rule. Unknown historical paths, malformed state, changed files, and symlink hazards block preflight. Do not recursively prune unrelated directories. Keep canonical policy and unrelated content, and remove ownership state only after eligible removal is verified.

The existing publication model is not whole-install atomic. Recheck sources/targets at publication boundaries, retain per-file atomic replacement where available, and report any late partial failure without committing a false ownership map. Metadata hashes are local integrity/ownership records, not authenticated human provenance.

### 5. Make doctor actionable without changing the diagnosis

Build the view from native doctor records plus the new lifecycle/discovery checks, not by rescanning policy differently. A trusted remediation catalog maps check IDs/families to groups and exact command argument lists. If information such as repository binding or owner identity is missing, the next command can be `sdlc explain ...` to obtain that information; label it as discovery rather than a fix. Unknown checks stay visible.

FAIL always remains blocking. Strict-mode fatal warnings stay fatal. Optional non-strict findings can be informational only when their optionality is explicit, with their raw status/details retained. Publish both raw counts and action groups. Group only findings resolved by the same action, not unrelated warnings to hit a target. Configuration, enabled state, verified execution, and hosted enforcement remain separate.

Predeclare the fresh-init fixture, expected human actions, and evaluation boundary. It must demonstrate zero FAIL and at most three genuine needs-human groups without hiding required work. Initialization/control installation is not a Lite diff; the subsequent Lite test uses an explicit committed range and existing exemption rules. Fixture bootstrap commits are test setup, not commits or approvals in this repository. Record setup commands and unresolved hosted actions rather than claiming an end-to-end hosted merge.

### 6. Build a local wheel from an explicit payload

Use the [wheel format](https://packaging.python.org/en/latest/specifications/binary-distribution-format/) with an `sdlc` console entry and a private namespaced payload retaining the current scripts/skills resource layout. The canonical dispatcher remains `scripts/sdlc.py`; a package launcher delegates to that payload rather than defining another CLI. Test installed use, not unsupported direct zip-import tricks.

Prepare the wheel with a small standard-library builder over an explicit allowlist, including required license/metadata/RECORD hashes, console entry metadata, and Python compatibility. Do not recursively package the checkout, secrets, Git data, caches, or generated test workspaces. An explicit unreleased test version is not a publication or tag. No runtime `Requires-Dist` entries; adding a build dependency instead requires a separate decision and authorization.

Keep artifacts in an explicitly selected output directory. Validate contents and run the wheel in an isolated environment without Node or a source checkout. Actual `pipx`/`uvx` checks require available, authorized tooling and remain unverified otherwise. No upload, release, tag, or global installation occurs as part of this proposal.

## Risks / Trade-offs

- New destructive operations could over-trust editable state. Mitigation: recognized-output bounds, unchanged hashes/types, full preflight, race checks, and malformed/forged-state negative controls.
- User policy edits could leave adapters stale. Mitigation: source-aware rendering and status, preserving user policy and refusing edited generated-file replacements.
- Native format drift or overlapping search roots could break discovery. Mitigation: version/surface-specific fixtures and loader evidence, no global changes, and explicit unsupported/unverified rows.
- Agent instructions could become accidental shell programs. Mitigation: no shell-expansion embedding of project policy/arguments, no permission overrides, and hostile-text rendering tests.
- Grouped health could conceal governance gaps. Mitigation: retain raw findings, require a real fresh-init result, and never promote configuration to execution or enforced review.
- Newly emitted control files are not all covered today. Add exact supported native-control protections, including nested locations where applicable, to `lane.py`; never broaden non-executable/Lite exemptions to accommodate them.
- Adding dependencies could fragment runtime delivery. Mitigation: complete allowlisted payloads, source/installed/wheel smoke tests, and missing-component failures with no target-code fallback.

## Migration Plan

1. Obtain named approval for the Critical implementation scope; reclassify final paths and record the implementation baseline. Preserve pending WS2 and other changes.
2. Add failing-first CLI, ownership, rendering, and trust tests. Introduce delegation and lifecycle behavior without changing existing native entry-point results.
3. Exercise legacy installations, empty targets, user-policy targets, conflicts, native profiles, and fresh-init doctor/Lite fixtures on Windows and POSIX. Reconfirm Python 3.8 support in an authorized environment.
4. Build and validate the local wheel, then test its actual installed entry point and optional runners. Record exact versions and missing coverage, not assumed compatibility.
5. For a supported downgrade that the older updater cannot safely reconcile, validate the target's documented entry point and profile capabilities before mutation. Use the current trusted distribution to inspect/uninstall eligible output, then restore with that selected distribution. Keep an external trusted entry point available. Preserve user policy and stop on conflicts or unsupported restoration; do not let an older tool guess, delete, or forget unfamiliar records.
6. Record trace, two independent reviewer notes, threat/rollback verification, and canonical red/green proof from an explicitly authorized committed candidate before handoff. No approval, execution proof, or publication is supplied by this planning capture.

Approved-by: Achmad Kurnianto (2026-11-10). Explicit scope approval covers WS3 working-tree implementation (`scripts/sdlc.py`, `scripts/agent_profiles.py`, `scripts/install.py`, `scripts/install-manifest.json`, `scripts/lane.py`, `scripts/build_wheel.py`, `skills/ai-sdlc/**`, `docs/COMPATIBILITY.md`, `LIMITATIONS.md`, `README.md`, WS3 test modules, `tests/mutate.py`, and `openspec/changes/one-front-door/` records) plus offline local verification. Commits, tags, pushes, publishing, tool installation, live-agent runs, hosted settings, and WS2/WS4 are excluded. This is scope authorization, not an independent reviewer approval.

## Implementation Evidence

- Task 1.1 (`[measured here, 2026-11-10]`): baseline `HEAD` is `bcd73678bb4a8ec49d08faa87c87cf4ec4e7c91a`. `python -B scripts/lane.py --paths ...` across the planned WS3 runtime, doc, test, and record paths classified `Critical: matched Critical rule scripts/** (built-in) (scripts/sdlc.py +6 more)`. Pre-existing working-tree items (`openspec/changes/interop-spec-kit-openspec/`, `openspec/changes/lite-fast-path/`, `.kilo/`, and contributor OpenSpec/Kilo workflow diffs in `.agents/`, `.claude/`, `.kilocode/`, `.opencode/`) were verified outside WS3 and remain untouched.
- Task 1.2 (`[measured here, 2026-11-10]`): legacy baseline captured — source `doctor.py --root . --json` returned exit `0` (`31 verified, 0 FAIL, 2 WARN, 1 info, 2 unverified`); clean-room `install.py` installed 64 files in `1.3089s` and `doctor.py` returned exit `0` (`29 verified, 0 FAIL, 4 WARN, 1 info, 3 unverified`); `lane.py`, `check_spec.py`, `check_brief.py`, and `evidence_check.py` exit/diagnostic contracts confirmed. Predeclared boundary: fresh-init fixture initializes an empty `main` Git repo with `README.md`, runs `sdlc init` + `sdlc doctor` (raw counts retained; `FAIL` and `--strict` `WARN` -> `blocking`; genuine operator work grouped only by shared action into `define-codeowners`, `bootstrap-default-branch`, and `activate-hosted-enforcement`; unknown non-verified checks stay unmerged; optional non-strict `hook-active`/`rule-dead-critical`/`rule-critical-share` stay `informational` with raw `WARN` preserved). Fixture bootstrap commit is Critical setup, never relabeled Lite; the subsequent Lite gate check runs on a separate `docs/**`/`README.md` commit range. No benchmark commit created.
- Task 1.3 (`[measured here, 2026-11-10]`): reconfirmed the 7 native project-local surfaces in Decision 3. Available local verification tools: Windows Python `3.15.2`, `pip 26.2.2`, `venv`, Git `2.45.1.windows.1`, PowerShell `7.6.9`, Node `v26.13.0`, cached offline `skills 1.7.0`, `openspec 1.17.0`, `shellcheck 0.9.0`, `opencode v2.2.5`, and WSL Ubuntu `Python 3.14.4`. Unavailable locally (recorded `unverified`, not installed): `uv`/`uvx`, `pipx`, `python3.8`, `gh`, `claude`, `cursor`, `codex`, `gemini`, `kilo`, and Copilot CLI/VS Code loader.
- Task 2.1 RED (`[measured here, 2026-11-10]`): `python -B -m unittest tests.test_sdlc_cli -v` ran 5 tests in `2.380s` (`FAILED (failures=13)`, 0 errors), verifying direct helper controls and failing solely on named missing-front-door assertions.
- Task 2.2 GREEN (`[measured here, 2026-11-10]`): implemented `scripts/sdlc.py` fixed dispatch over `lane`, `check spec`, `check brief`, and `check evidence` (no `gate` alias or `lite` stub); `python -B -m unittest tests.test_sdlc_cli -v` passed (`Ran 5 tests in 10.054s — OK`).
- Task 2.3 RED->GREEN (`[measured here, 2026-11-10]`): added `DoctorAndExplainContract` (RED: `Ran 8 tests in 24.990s — FAILED (failures=11)`, 0 errors), then implemented `group_doctor_results` and `lookup_check_catalog` over unchanged `scripts/doctor.py`; GREEN: `Ran 8 tests in 46.346s — OK` (raw counts/statuses retained, `--strict` `WARN` -> `blocking`, unknown checks unmerged, safe quoted argv, read-only `explain`).
- Task 2.4 (`[measured here, 2026-11-10]`): added `RuntimeIsolationContract` exercising source and installed `sdlc.py` from hostile CWDs/PYTHONPATH against poisoned target repos (both `-I` and non-`-I`), missing runtime-component fail-closed checks (`exit 3`), and legacy `install.py`/`install.sh`/`install.ps1`/`doctor.py` parity (`Ran 11 tests in 92.798s — OK`).
- Task 3.1 RED->GREEN (`[measured here, 2026-11-10]`): added `StatusAndDryRunPlanningContract` in `tests/test_lifecycle.py` (RED: `Ran 4 tests in 4.068s — FAILED (failures=13)`), then implemented shared read-only `status_project` and non-mutating `plan_install`/`init_project` in `scripts/install.py`; GREEN: `tests.test_lifecycle` (`Ran 4 tests in 30.264s — OK`) and `tests.test_install.FilesystemSafety` (`Ran 17 tests in 48.118s — OK (skipped=3)`).
- Task 3.2 RED->GREEN (`[measured here, 2026-11-10]`): added `UpdateReconciliationContract` (RED: `Ran 2 tests in 2.508s — FAILED (failures=2)`), then implemented `update_project` reconciling unchanged recognized owned outputs to the invoked distribution while preserving `AGENTS.md`/unowned files and blocking on edited or forged state paths (`Ran 2 tests in 5.433s — OK`).
- Task 3.3 RED->GREEN (`[measured here, 2026-11-10]`): added `UninstallContract` (RED: `Ran 2 tests in 2.879s — FAILED (failures=2)`), then implemented `uninstall_project` removing only unchanged recognized owned files, preserving `AGENTS.md` and unrelated files/directories, blocking on modified/forged/junction targets, and removing `.sdlc-install.json` last (`Ran 2 tests in 9.372s — OK`).
- Task 3.4 (`[measured here, 2026-11-10]`): added `LifecycleRaceAndFailureContract` covering mid-publication replacement failures (`changed` paths reported honestly without publishing new `.sdlc-install.json`), post-preflight target/state/policy races, partial-uninstall state retention + concurrent-edit retry protection, and legacy `install.py -> status -> update -> uninstall` end-to-end (`Ran 11 tests in 36.844s — OK`).
- Task 4.1 RED->GREEN (`[measured here, 2026-11-10]`): added `CanonicalPolicyAndRegistryContract` in `tests/test_agent_profiles.py` (RED: `Ran 4 tests in 1.664s — FAILED (failures=4)`), then implemented `scripts/agent_profiles.py` and unified policy snapshot/UTF-8/race verification in `scripts/install.py`; GREEN (`Ran 4 tests in 5.302s — OK`).
- Task 4.2 RED->GREEN (`[measured here, 2026-11-10]`): added `ClaudeCursorCopilotCodexProfilesContract` (RED: `Ran 8 tests in 10.184s — FAILED (failures=4)`), then implemented `claude` (`CLAUDE.md`, `.claude/skills/*`, `.claude/commands/sdlc/<op>.md` -> `/sdlc:<op>`), `cursor` (`.cursor/skills/*`, manual `.cursor/skills/sdlc-<op>/SKILL.md` with `disable-model-invocation: true` -> `/sdlc-<op>`, no `.cursor/commands`), `copilot` (`.github/copilot-instructions.md`, `.github/skills/*`, `.github/prompts/sdlc-<op>.prompt.md` with VS Code-only disclaimer), and `codex` (`.agents/skills/*`, no fake slash-command files), keeping source discovery at 10 canonical product skills; GREEN (`Ran 8 tests in 13.082s — OK`).
- Task 4.3 RED->GREEN (`[measured here, 2026-11-10]`): added `GeminiOpencodeKiloAndHostilePolicyContract` (RED: `Ran 3 tests in 5.308s — FAILED (failures=3)`), then implemented `gemini` (`GEMINI.md`, `.gemini/skills/*`, `.gemini/commands/sdlc/<op>.toml` -> `/sdlc:<op>`, valid TOML, no `!{...}` or Antigravity substitution), `opencode` (`.opencode/skills/*`, `.opencode/commands/sdlc/<op>.md` -> `/sdlc/<op>` slash namespace, no `CLAUDE.md` fallback or `` !`...` ``), `kilo` (`.kilo/skills/*`, `.kilo/command/sdlc-<op>.md` -> `/sdlc-<op>`, no `.kilocode/`), and hostile-policy rendering isolation; GREEN (`Ran 11 tests in 24.691s — OK`).
- Task 4.4 RED->GREEN (`[measured here, 2026-11-10]`): added `NativeAgentControlBoundary` in `tests/test_lane.py` (RED: `FAILED (failures=232)`), then extended `BUILTIN_CRITICAL` in `scripts/lane.py` across all generated instruction/command/skill formats and nested `.agents`/`.gemini`/`.opencode`/`AGENTS.override.md`/`CLAUDE.local.md`/`opencode.json`/`kilo.jsonc` locations; GREEN on `tests.test_lane` + `tests.test_doctor.ResumedOwnershipProof` (`Ran 62 tests in 13.022s — OK (skipped=2)`).
- Task 4.5 RED->GREEN (`[measured here, 2026-11-10]`): added `ManifestAdditiveDriftAndDiscoveryContract` (RED: `Ran 3 tests in 8.263s — FAILED (failures=2)`), added `scripts/sdlc.py` and `scripts/agent_profiles.py` to `scripts/install-manifest.json` (`66` core files), updated `skills/ai-sdlc/**` + `docs/COMPATIBILITY.md` + `LIMITATIONS.md` + `README.md` (including skill-only `"run sdlc init --root ."` fallback), and verified offline discovery via cached `skills 1.7.0` (`npx --no-install --offline skills add --list` -> `Found 10 skills` on both core-only and `--agents cursor` targets); GREEN across `test_agent_profiles` (`14/14`), `test_install.FilesystemSafety` (`17/17`, 3 skips), `test_comparison_docs` + `test_repository_hygiene` + `test_templates` (`46/46`).
- Task 5.1 RED (`[measured here, 2026-11-10]`): added `WheelPackagingContract` in `tests/test_wheel.py` asserting allowlisted archive contents, checkout/cache/secret exclusion, `METADATA` (`Requires-Python: >=3.8`, zero `Requires-Dist`), `WHEEL`, `LICENSE`, `entry_points.txt`, `RECORD` SHA-256 verification, and missing-resource failure (`Ran 2 tests in 0.013s — FAILED (failures=2)`, 0 errors).
- Tasks 5.2 & 5.3 GREEN (`[measured here, 2026-11-10]`): implemented stdlib `scripts/build_wheel.py` (`ai_native_sdlc_plus-0.0.0.dev0-py3-none-any.whl`, `_sdlc_runtime.cli:main` thin launcher over `_sdlc_runtime/scripts/sdlc.py`) and `InstalledWheelExecutionContract` installing via `pip 26.2.2` (`--no-index --no-deps`) into an isolated `venv`, deleting the source copy, stripping Node from `PATH`, and verifying source-vs-wheel parity + full lifecycle (`Ran 3 tests in 25.937s — OK`; Windows `WinError 4551` Smart App Control on unsigned `%TEMP%` distlib `.exe` stubs handled via `venv` `importlib.metadata.entry_points` loader, while WSL Ubuntu executes `venv/bin/sdlc` directly; `pipx`/`uvx` and Python 3.8 remain `unverified`; no upload or tag).
- Task 6.1 (`[measured here, 2026-11-10]`): `EmptyRepoSetupAndSubsequentLiteGateContract` (`tests/test_sdlc_cli.py`, `Ran 12 tests in 55.598s — OK`) ran `git init -b main` + `README.md` commit -> `sdlc init --root <repo> --json` (`setup_mode=core-only`, `policy.action=create-starter`) -> `sdlc doctor --root <repo> --json` (`29 verified, 0 FAIL, 4 WARN, 1 info, 3 unverified`; `blocking=0`, `needs_human=3`: `define-codeowners`, `bootstrap-default-branch`, `activate-hosted-enforcement`) -> `sdlc lane` on bootstrap (`Critical: matched Critical rule scripts/** (built-in)`) + Critical bootstrap commit on `main` -> branch `docs/lite-note` adding `docs/onboarding-note.md` -> `sdlc lane --base <main> --head <branch> --strict` (`Lite: matched Lite rule docs/**`) -> `sdlc check evidence --ci --base <main> --head <branch> --pr-body-file -` (`exit 0`, `evidence ok for Lite`; no hosted merge claimed).
- Task 6.2 (`[measured here, 2026-11-10]`): focused WS3 suites passed (`test_sdlc_cli` 12/12, `test_lifecycle` 11/11, `test_agent_profiles` 14/14, `test_wheel` 3/3); `shellcheck -S warning install.sh hooks/pre-push hooks/pre-push.sh skills/ai-sdlc/assets/ci-generic.sh` exited `0`; full foreground suites passed on Windows (`Python 3.15.2`: `Ran 683 tests in 1128.938s — OK (skipped=16)`) and WSL Ubuntu POSIX (`Python 3.14.4`: `Ran 683 tests in 609.648s — OK (skipped=28)`). Python >= 3.8 stdlib/syntax compatibility verified across all scripts; live Python 3.8 and macOS runtime execution remain `unverified` locally.
- Task 6.3 (`[measured here, 2026-11-10]`): added 16 targeted WS3 mutants in `tests/mutate.py` covering dispatcher bypasses (`sdlc.py`), hidden doctor failures (`sdlc.py`), unsafe ownership/deletion & dropped generated records (`install.py`), manual command safety (`agent_profiles.py`), required wheel source checks (`build_wheel.py`), and native-control `BUILTIN_CRITICAL` patterns (`lane.py`). Full foreground `tests/mutate.py` run exited `0` (`killed 192 / 192 non-equivalent mutants; 2 equivalent survivor(s) documented`).
- Task 6.4 (Pending): commits are excluded from user scope authorization (`Approved-by: Achmad Kurnianto (2026-11-10)`), so no committed candidate SHA exists; Task 6.4 remains unchecked (`- [ ]`) in `tasks.md` pending an authorized committed candidate revision.
- Task 6.5 (`[measured here, 2026-11-10]`): `openspec validate one-front-door --strict --no-interactive` -> `Change 'one-front-door' is valid`; whitespace, scope, and Critical evidence results recorded in Review notes below. Two independent human reviewer approvals remain pending before merge.

Intent link: openspec/changes/one-front-door/proposal.md
Spec: openspec/changes/one-front-door/specs/sdlc-front-door/spec.md

## Threat note

- **Trust boundaries:** Untrusted target repository files, CWDs, `PYTHONPATH`, `.sdlc-install.json`, and user-owned `AGENTS.md` vs. the trusted invoked runtime (`scripts/sdlc.py`, `scripts/install.py`, `scripts/agent_profiles.py`, `scripts/build_wheel.py`, `_sdlc_runtime`).
- **Mitigations verified:** `_scrub_import_paths` and `resolve_runtime_file` prevent importing target/CWD modules (`RuntimeIsolationContract`); `validate_recognized_ownership` intersects `.sdlc-install.json` with trusted manifest/profile outputs and blocks forged paths, symlinks, junctions, and modified files (`LifecycleRaceAndFailureContract`); user policy text is copied verbatim only into plain instruction adapters (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) and never into command/prompt files, which `agent_profiles.py` renders solely from fixed trusted templates with no shell-evaluation syntax or model/permission overrides (`GeminiOpencodeKiloAndHostilePolicyContract`); policy text itself is not sanitized, so instruction-file content remains the user's responsibility; `BUILTIN_CRITICAL` protects all generated and nested control paths (`NativeAgentControlBoundary`); `build_wheel.py` packages only explicit allowlisted files (`WheelPackagingContract`).

## Rollout plan

- **Stage 1 (Local & CI opt-in):** Ship `scripts/sdlc.py`, `scripts/agent_profiles.py`, extended `scripts/install.py`, and `scripts/build_wheel.py` while keeping legacy `scripts/lane.py`, `scripts/evidence_check.py`, `scripts/doctor.py`, `scripts/install.py`, `install.sh`, and `install.ps1` entry points unchanged.
- **Monitoring signals:** Zero regressions across the 683-test suite on Windows and POSIX, `192/192` killed non-equivalent mutants in `tests/mutate.py`, and `0 FAIL` / `<= 3` `needs_human` groups on fresh `sdlc init` + `sdlc doctor`.
- **Rollback steps:** For target projects, run `sdlc uninstall --root <path>` to remove unchanged owned files while preserving user-owned `AGENTS.md` and unowned project files; for this repository, revert the WS3 changeset (`git revert <commit>` once committed) with zero schema migration because `.sdlc-install.json` remains version 1.

## Trace

### Change
Implemented the unified `scripts/sdlc.py` front door (`init`, `lane`, `check spec|brief|evidence`, `doctor`, `status`, `update`, `uninstall`, `explain`), conservative lifecycle management in `scripts/install.py`, deterministic 7-profile native agent bootstrap in `scripts/agent_profiles.py`, expanded `BUILTIN_CRITICAL` coverage in `scripts/lane.py`, stdlib local wheel builder `scripts/build_wheel.py`, updated `ai-sdlc` docs/skills, and added 41 new contract test methods plus 16 mutation controls.

### Why
Eliminate multi-script path friction and manual onboarding boilerplate while preserving strict evidence gates, version-1 ownership safety, user-owned `AGENTS.md` policy, and zero external runtime dependencies.

### Alternatives rejected
- Adding a `sdlc gate` alias or a stub `sdlc lite` subcommand: rejected by spec (`check evidence` is the sole gate integration command; `lite` belongs to WS4).
- Adding `--force` overwrite or recursive directory deletion on `update`/`uninstall`: rejected to prevent destructive loss of user edits or unowned files.
- Packaging via external `build`/`wheel`/`setuptools` dependencies or direct zip-import tricks: rejected in favor of a deterministic stdlib PEP 427 builder and installed `console_scripts` entry point.

### Test evidence
Observed failing-first RED then GREEN across `tests.test_sdlc_cli` (12 tests), `tests.test_lifecycle` (11 tests), `tests.test_agent_profiles` (14 tests), `tests.test_wheel` (3 tests), and `tests.test_lane.NativeAgentControlBoundary`; full foreground `unittest discover` passed on Windows (`683` tests, `16` skipped) and WSL Ubuntu (`683` tests, `28` skipped); `tests/mutate.py` killed `192/192` non-equivalent mutants.

### Risk accepted
Live agent CLI execution (`claude`, `cursor`, `codex`, `gemini`, `kilo`, Copilot), `pipx`/`uvx` runners, macOS, and live Python 3.8 interpreter execution remain `unverified` on this workstation and are documented as such in `docs/COMPATIBILITY.md`; canonical `scripts/redgreen.py` proof (Task 6.4) awaits an authorized committed candidate.

### Provenance
Assisted-by: Antigravity (human-reviewed: pending two independent Critical lane reviewers)

## Review notes

- **Verified locally:** Fixed front-door dispatch and exit codes, grouped `doctor` + `explain` catalog with raw findings retained, version-1 `.sdlc-install.json` compatibility, race/partial-failure safety, user-owned `AGENTS.md` preservation, 7 native profile surfaces, `BUILTIN_CRITICAL` self-protection, offline `venv` wheel execution without Node or source checkout, and fresh empty-repo setup reaching a passing local Lite gate.
- **Pending human review:** Two independent human reviewer approvals required for Critical lane changes remain pending (`Approved-by: Achmad Kurnianto (2026-11-10)` is scope authorization only, not a code review sign-off).
