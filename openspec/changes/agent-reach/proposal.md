# Proposal

## Why

The toolkit renders seven native agent profiles, but generated-file tests do not prove native loader discovery or behavioral compliance, and public adapter tables describe different paths from the renderer. WS7 needs a test-result-derived support matrix, source-generated adapters with drift detection, and a coherent release identity instead of the current changelog, doctor, and wheel version mismatch.

## What Changes

- Consolidate declared profile metadata, supported selectors, native paths, recovery markers, and command surfaces around the existing profile renderer. Keep the manifest as the skill-file source and preserve the seven profiles, ten product skills, user-owned `AGENTS.md`, and version-1 installation ownership.
- Generate repository adapter policy from `AGENTS.md` rather than maintain independent policy copies. Retain both `.cursorrules` and `.cursor/rules/sdlc.mdc`, with format-specific wrappers and drift tests; compatibility files do not become additional skills or evidence of client support.
- Preregister three independent evidence levels per profile and surface: instruction files generated and present; skills discovered by that client's loader in an isolated scratch project; behavior confirmed by a reviewed recorded transcript. Require native positive and negative controls and bind results to client version, platform, candidate revision, source hashes, and probe identity.
- Target Levels 1 and 2 for all seven profiles and Level 3 for Claude Code and OpenCode V2. Missing clients, unsafe startup, failed discovery, or missing behavioral evidence leave the relevant target incomplete rather than lower the target.
- Generate the support matrix from validated test/probe records. Make `docs/COMPATIBILITY.md` its detailed presentation and link to it from README and adapter guidance; reject hand-edited matrix drift, stale source hashes, and invalid evidence promotion.
- Reconcile product version outputs through one shared source with the owner-selected release `0.3.0`. Bring `CHANGELOG.md` forward using verified history while retaining dated legacy entries and cumulative patch notes.
- Add release preflight for coherent version, changelog, wheel metadata, artifact hashes, clean candidate provenance, verification receipt, and tag collision checks. Create a local annotated `v0.3.0` tag only after separate explicit tag authorization; do not backfill historical tags or publish remotely.
- Preserve the archived `one-front-door` warning: task 6.4 was not completed. Its existing implementation and synced capability are dependencies, not proof supplied or repaired by this change.

## Capabilities

### New Capabilities

- `release-hygiene`: One product release identity, history-preserving changelog maintenance, reproducible artifact preflight, and explicitly authorized tag creation.

### Modified Capabilities

- `agent-native-bootstrap`: Source-driven adapter generation, three-level native evidence with fixed acceptance targets, and a reproducible support matrix generated from validated results.

## Impact

- Expected implementation targets include `scripts/agent_profiles.py`, profile-selector consumers in `scripts/sdlc.py`, installer/manifest and wheel integration, a shared version resource, repository-only native probe/result tooling, and focused profile, evidence, release, packaging, and mutation tests.
- Documentation targets include README, `docs/COMPATIBILITY.md`, `adapters/README.md`, `CHANGELOG.md`, and the identified repository-self adapter files. Adapter adoption during apply must be explicit and limited to named paths; initialization must still preserve differing unowned target-project content.
- Native discovery and behavioral tests require separately authorized client setup and bounded calls. Kilo's earlier canonical-skill token probes and generic skill scans do not establish discovery of generated native profiles; Kilo cannot substitute for OpenCode V2 or Claude Code.
- Python 3.8+ and standard-library-only runtime remain unchanged. Client tools are optional verification infrastructure, not new gate dependencies; default CI validates deterministic fixtures and committed redacted evidence without model credentials or live calls.
- Non-goals: no new agent integration, permission bypass, global configuration rewrite, runtime sandbox, hosted service, additional product skills, skill-body redesign, silent path deletion, invented human approval, changed evaluation history, remote publication, or completion of other changes' missing proof tasks.
- This request authorizes planning only. Apply requires fresh named Critical-scope approval; commits, client installation, credential use, paid calls, tags, and remote publication are not authorized by the selected planning choices.
