## Why

WS3 in `prompt.md` calls for one usable entry point over the existing gate, validators, doctor, and installer. Today those tools have separate invocation and ownership conventions, while copying adapter examples does not reliably register a working workflow with the user's agent.

## What Changes

- Add `scripts/sdlc.py` with `init`, `lane`, `check spec`, `check brief`, `check evidence`, `doctor`, `update`, `uninstall`, `status`, and `explain <check-id>`. Delegate existing policy checks rather than reimplementing their rules, flags, or exit semantics. Do not invent a `gate` alias; `lite` is added by WS4.
- Make `init --agents claude,cursor,copilot,codex,gemini,opencode,kilo` generate project-local native instruction, skill, and command entries for the selected profiles from shared sources. Register commands only through supported native mechanisms and document surface-specific spellings.
- Treat root `AGENTS.md` as user-owned canonical policy, as confirmed during exploration: preserve it when present, create a starter only when absent, generate adapters from it, and retain it on uninstall. Never rewrite project instructions merely to make initialization pass.
- Provide read-only status and safe update/uninstall operations over recognized, hash-owned files. Preserve the existing `.sdlc-install.json` version-1 shape and legacy installation entry points, and refuse unsafe or edited-file operations without a force escape hatch.
- Group doctor results into blocking, needs-human, and informational actions with exact next commands, retaining every underlying finding and failure/strict-mode meaning.
- Prepare a local, zero-runtime-dependency wheel with an `sdlc` entry point and the complete allowlisted runtime. Verify local wheel use without publishing a package or introducing Node as a gate prerequisite.
- Protect newly generated agent-control paths as Critical, test generated-file drift and native path validity, and document what is configured versus actually loaded or behavior-tested.

## Capabilities

### New Capabilities

- `sdlc-front-door`: A compatible CLI, actionable doctor presentation, isolated runtime resolution, and an offline distributable entry point.
- `agent-native-bootstrap`: Selected native profiles, canonical user policy, complete runtime delivery, and explicit registration/verification boundaries.
- `owned-runtime-lifecycle`: Read-only state inspection and conservative, version-1-compatible update/uninstall behavior.

### Modified Capabilities

None. Existing lane/evidence, approval, and verification requirements remain the authority behind these new interfaces.

## Impact

- Expected targets: `scripts/sdlc.py`, installer/manifest support, a shared agent-profile renderer, wheel preparation, targeted lane protection, doctor presentation, and hot-path usage guidance. Legacy `install.sh`, `install.ps1`, and `python scripts/evidence_check.py --ci` remain usable.
- Runtime remains Python 3.8+ and standard-library-only with Git where inspection needs it. Optional agent and package-runner tooling is verification infrastructure, not a new runtime dependency.
- Acceptance includes an empty-repository initialization fixture reaching a passing local Lite gate, fresh-init doctor output with zero FAIL and at most three genuine needs-human action groups, and snapshot/path tests including Claude and Copilot. Raw findings and actual setup actions remain visible; grouping cannot hide a miss.
- The intended implementation classifies Critical because it changes executable delivery, lifecycle operations, and agent-control surfaces. Named implementation approval, tests, canonical proof, and independent reviews remain future requirements.
- WS3 supplies the command/runtime contract needed by WS4 and WS2. This proposal does not implement those workstreams, activate hosted settings, install external tools, create commits, or publish the wheel. Only planning artifacts are authorized now.
