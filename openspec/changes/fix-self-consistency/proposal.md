## Why

The shipped repository fails its own doctor: the workflow selects a pinned Gitleaks v3 action, but the inspector recognizes only an older pin. Tracked bytecode, session state, and duplicated generated OpenSpec instructions also undermine a reproducible source checkout; WS0 must restore self-consistency before expanding the product.

## What Changes

- Move the bounded set of supported scanner references into a reviewed, versioned data file distributed with doctor. Load it only from the running inspector's own trusted directory, retain exact owner/repository and full-SHA validation, and continue rejecting unknown pins and unsupported workflow shapes.
- Add the currently shipped v3 reference after provenance/contract review, while preserving recognition of the existing supported v2 reference. Recognition remains structural evidence, not proof that a hosted scan or an obsolete runtime executed successfully.
- Include the profile data in the explicit install manifest and owned-file verification so installed doctor remains self-contained when the toolkit source checkout is unavailable.
- Add zero-overall-failure regressions against the real source workflow and an installed copy. Preserve independent protocol fixtures and add negative coverage for unknown pins, invalid/missing trusted data, and an inspected repository attempting to supply its own approval list.
- **BREAKING (contributor checkout setup only):** stop tracking the 42 enumerated cache/session/generated entries and document local OpenSpec regeneration. Preserve working copies, authored agent adapters, the ten product skills, project specifications, and Git history; extend ignore rules only for generated instruction paths not already covered.
- Add source-index hygiene and clean-distribution skill-discovery checks, including exact discovery of the ten shipped skills. Keep network/tool provisioning separately authorized.

## Capabilities

### New Capabilities

- `ci-security`: Add trusted scanner-profile data and shipped/installed self-consistency requirements. This reuses the capability path already proposed by `harden-sdlc-foundation`, with distinct added requirement names rather than duplicating or rewriting that change's delta.
- `repository-hygiene`: Define the tracked-source exclusions, preservation/regeneration boundary for contributor tooling, and product-skill discovery guarantees.

### Modified Capabilities

None. Existing durable capability requirements, public command forms, lane-config version 1, and the advisory-hook/fail-closed-CI model remain unchanged.

## Impact

- Implementation is Critical. Expected runtime changes are confined to `scripts/doctor.py`, a new `scripts/scanner-profiles.json`, and `scripts/install-manifest.json`; tests and existing compatibility documentation cover the new bundle and cleanup contracts.
- The data file is part of the doctor distribution, not a new third-party runtime dependency. Python 3.8+, standard-library execution, and offline default inspection remain supported. An updated doctor without its required data must fail visibly, never silently accept arbitrary actions.
- Cleanup changes the Git index for an explicit reviewed inventory. Fresh contributor clones regenerate their chosen OpenSpec instructions locally; existing local copies are not deleted. New hand-authored Kilo commands and agents remain under `.kilo/`.
- The already pinned scanner workflow, Dependabot configuration, credentials, permissions, hosted controls, and other active changes are not rewritten. An inspected repository does not need to provide an approval registry to an external inspector.
- Unified CLI work, Skills-only bootstrap repair, artifact-format interop, Lite automation, stronger test-proof semantics, new model evaluations, footprint/description rewrites, and compliance claims belong to later workstreams.
- This request authorizes planning only. No runtime edit, cleanup, dependency installation, Git staging/removal, commit, push, agent registration, or hosted action will run until separately authorized.
