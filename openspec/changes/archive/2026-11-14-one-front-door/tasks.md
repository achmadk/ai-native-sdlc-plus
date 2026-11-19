## 1. Approval and Baselines

- [x] 1.1 Re-read the proposal/specs/design and `prompt.md`, classify the final implementation paths, and obtain named approval for the Critical scope before coding. Record the actual baseline and verify WS2 and other pending work remain outside this change.
- [x] 1.2 Capture legacy helper/installer behavior and define the fresh-init fixture, doctor action-count rules, and bootstrap/Lite evaluation boundary before measuring them. Verify the cases retain raw failures and existing evidence requirements; commit any benchmark registration only when explicitly authorized.
- [x] 1.3 Reconfirm native profile formats and record the client/package-runner versions available for verification. Verify that missing tools are recorded as unverified coverage and obtain separate permission before installation, live-agent execution, or external dependency changes.

## 2. Front Door and Actionable Checks

- [x] 2.1 Add public CLI contract tests in `tests/test_sdlc_cli.py` for command discovery, delegation, stdin, JSON, native errors, and unknown operations. Observe named assertion failures on the baseline before implementation, not uncaught missing-file, import, or environment errors.
- [x] 2.2 Implement `scripts/sdlc.py` as the fixed front door over existing lane/spec/brief/evidence helpers. Verify `check evidence` is the published integration form, delegated flags/output/exit behavior matches direct helpers, and neither `gate` nor a fake `lite` implementation is introduced.
- [x] 2.3 Add failing-first grouped-doctor and explain tests, then implement the presentation/catalog. Verify raw IDs/statuses/counts survive, strict failures remain blocking, unknown findings remain visible, exact next commands are safe, and an explanation never performs remediation or claims enforcement.
- [x] 2.4 Exercise source and installed command resolution from unrelated CWDs and hostile target repositories. Verify isolated CI invocation cannot import head/CWD replacements, missing owned runtime dependencies fail nonzero, and legacy installer/checker entry points retain their existing contracts.

## 3. Ownership and Lifecycle

- [x] 3.1 Add state/planning tests, then expose read-only status and dry-run planning through the shared installer engine. Verify version-1 fields/hash semantics remain compatible, invalid metadata fails before mutation, no status/dry-run directories are created, and recognized existing ownership is not dropped.
- [x] 3.2 Add failing-first update cases, then implement reconciliation to the invoked trusted distribution. Verify unchanged owned output can update, user policy and edited/unowned files remain untouched, unknown paths block unsafe plans, and no network upgrade or force option is used.
- [x] 3.3 Add failing-first uninstall cases, then implement eligible owned-output removal. Verify canonical `AGENTS.md` and unrelated files/directories survive, forged unrelated targets/symlinks/modified files cannot be deleted, conflicts block preflight, and state is removed only after verified completion.
- [x] 3.4 Run lifecycle race, injected-publication-failure, retry, and legacy-installation tests. Verify late partial failures are reported honestly, ownership never asserts unverified writes, and retry does not overwrite concurrent user changes.

## 4. Native Agent Bootstrap

- [x] 4.1 Add canonical-policy and generation tests, then implement the shared renderer/profile registry. Verify an existing `AGENTS.md` is byte-preserved and unowned, a starter is created only when absent, dry-run/preflight is non-mutating, and policy races or unsafe input fail without a silent replacement.
- [x] 4.2 Add Claude, Cursor, Copilot, and Codex profiles using the documented native surfaces. Verify snapshots, paths, actual command spellings, manual-only command behavior where supported, and that Copilot prompt files are not advertised as a CLI feature. Keep source product discovery at ten canonical skills.
- [x] 4.3 Add Gemini CLI, OpenCode V2, and Kilo profiles. Verify native TOML/Markdown/skill paths and namespaces, no Antigravity substitution or new legacy Kilo directories, no permission/model changes, and no automatic shell evaluation of supplied policy or arguments.
- [x] 4.4 Extend built-in Critical coverage for newly emitted control paths and supported nested locations. Add negative cases using permissive Lite/non-executable configuration and verify every generated instruction/command/skill format still fails to downgrade or obtain a test exemption.
- [x] 4.5 Integrate generated output with the complete owned runtime manifest and hot-path usage guidance. Verify additive selection, duplicate/case/path collision handling, source drift versus user edits, and installed helper/resource availability. Run native fixture/load checks where authorized, recording configuration, discovery, and execution as distinct levels rather than marking untested clients green.

## 5. Local Wheel

- [x] 5.1 Add failing packaging contracts for allowed files, license/metadata/RECORD content, Python floor, console entry, missing resources, and zero runtime dependencies. Verify the tests reject checkout/cache/secret inclusion and do not require publication.
- [x] 5.2 Implement the standard-library wheel builder and thin namespaced launcher over the canonical dispatcher. Build to an explicitly selected output directory and verify archive contents/hashes and source-versus-wheel command parity; do not add a build dependency without a separate approved decision.
- [x] 5.3 Install the local wheel in an authorized isolated environment and exercise it without Node or the source checkout, including unrelated CWDs and required resource access. Run actual local-wheel `pipx`/`uvx` checks when available, record versions/results, and leave unexecuted runner/Python/platform coverage unverified. Do not upload or tag the artifact.

## 6. Acceptance and Handoff

- [x] 6.1 Execute the declared empty-repository setup and subsequent genuine Lite fixture through the front door. Record every setup command, doctor raw findings and action groups, and the actual local gate result; verify zero FAIL and at most three genuine needs-human groups without labeling installation/control changes Lite or claiming a hosted merge.
- [x] 6.2 Run the focused CLI, installer, agent-generation, packaging, and legacy tests, then `python -B -m unittest discover -s tests -v` in the main foreground on authorized Windows/POSIX environments. Verify the Python floor and applicable shell lint, recording real counts and any unavailable coverage.
- [x] 6.3 Add targeted mutation controls for dispatcher bypasses, unsafe ownership/deletion, dropped generated records, hidden doctor failures, and missing native-control protection. Run `python -B tests/mutate.py` in foreground and record actual outcomes without dropping surviving controls to improve the result.
- [ ] 6.4 With an explicitly authorized committed candidate, produce canonical repeated red/green proof for the focused CLI/lifecycle contracts. Verify assertion-based baseline failures and candidate success, preserving native positive/negative controls; leave proof pending if no committed candidate is authorized.
- [x] 6.5 Record actual profile/wheel/setup evidence, the published WS3 command/runtime contract, two independent reviewer notes, and threat/rollback verification. Run `openspec validate one-front-door --strict --no-interactive`, whitespace/scope checks, and the applicable evidence check using collected evidence. Keep missing reviews/executions pending and stop before WS4/WS2 implementation, publication, or hosted activation.
