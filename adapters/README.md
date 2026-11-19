# Adapters — use alongside incumbents, not instead of them

## spec-kit

Keep `.specify/` flow; add lane classification before `/speckit-plan` and evidence check after `/speckit-implement`. Map: spec-kit spec -> spec-first Standard; bug-fix extension -> ship-and-observe unplanned loop. Smoke test: classify three spec-kit artifact paths, expect lanes without touching `.specify/`.

## Superpowers

Keep existing commands; invoke ai-sdlc routing first, then the matching Superpowers workflow for build depth. Evidence gate runs unchanged at PR. Details unverified against current Superpowers internals — adapter is a thin shim, issues welcome.

## OpenSpec

This repo's own planning used OpenSpec changes. Map: OpenSpec proposal -> spec-first intent; specs -> acceptance criteria; `evidence_check.py --lane` reads artifact presence from the change directory. Smoke test: `openspec status` green plus evidence check on the change's tasks.

## Agent Adapters

Repository compatibility files are generated from user-owned root `AGENTS.md`:

- `.claude/CLAUDE.md`
- `.cursorrules`
- `.cursor/rules/sdlc.mdc`
- `.github/copilot-instructions.md`
- `GEMINI.md`

These files are not installer-owned. They are separate from the native profiles that `sdlc init --agents ...` installs into a target project. For example, a native Claude profile uses root `CLAUDE.md`, not the repository compatibility path `.claude/CLAUDE.md`. See the [native profile matrix](../docs/COMPATIBILITY.md) for exact paths and client surfaces.

Both Cursor compatibility formats carry the same canonical policy in format-specific wrappers. These generated files do not prove native discovery, precedence, or behavior by a real client. Gemini CLI, Antigravity, OpenCode V2, and Kilo remain distinct verification targets.

Inspect drift without writing:

```bash
python -I -B scripts/agent_profiles.py repository --root . --check --json
```

After explicit owner approval, reconcile adapter-only safeguards in `AGENTS.md` and review the resulting check report. Adopt only that exact policy and five-file snapshot:

```bash
python -I -B scripts/agent_profiles.py repository --root . --adopt \
  --policy-sha256 "<policy_sha256 from the reviewed report>" \
  --adapters-sha256 "<adapters_sha256 from the reviewed report>" --json
```

The hashes bind the reviewed bytes and modes; they do not authenticate the approver. Changed snapshots or linked paths are refused. Generation preserves `AGENTS.md`, installation state, and unrelated files; it does not make these compatibility files owned by the installer. Rerun the read-only check after publication. Local verification commands remain `python -B -m unittest discover -s tests -v`, `python -B tests/mutate.py`, and the repository's ShellCheck command when that executable is available.

## Native Evidence Protocol

`scripts/agent_reach.py` validates versioned registration and result records offline:

```bash
python -I -B scripts/agent_reach.py validate --root . --registration "<registration.json>" --json
python -I -B scripts/agent_reach.py replay --root . --registration "<registration.json>" --records "<result-ledger.json>" --json
```

Registration records bind the candidate SHA, complete allowlisted source hashes, trusted profile registry hash, all seven client/version/surface/platform targets, independent required levels, fixed cases, skill-only nonce, controls, repeats, and finite resource limits. A result carries `registration_sha256`, candidate/source identities, exact client identity, `capture_kind`, `reviewed_by`, and positive/negative capture pairs with terminal exit codes and stdout/stderr digests.

The capture observation is a reviewed JSON object: generation records list file hashes and unchanged policy hashes; discovery observations list native-discovered skill names and absolute scratch paths; behavior observations add loaded skills, response text, and tool events. Preserve and review original native outputs when preparing this observation. Metadata and hashes do not establish that a native client really ran, and replay does not authenticate a client or reviewer.

`capture_kind: synthetic` exercises parser and error branches only and never certifies native support. Level 1 generation does not promote Level 2 discovery or Level 3 behavior. Client/version/surface substitutions, stale hashes, missing repeats, false-positive negative controls, prompted nonces, and secret material are rejected or retained as failed outcomes.

The Python `run_capture` collector uses explicit argv, `shell=False`, a caller-supplied environment, finite time/stream limits, atomic storage, and a persistent pre-call reservation ledger. Cache identity includes argv, binary hash, environment digest, working directory, and case context; replaying a cache entry is not another attempt. Failed or secret-bearing attempts still consume their reservation, and secret content is not persisted.

Actual native capture requires explicit approval and verified client-version setup, including binary hash, exact argv, disposable home/configuration, disabled updates/plugins/hooks/MCPs, and denied unrelated tools. Credential environment variable names are allowlisted; values are never stored in setup/evidence records. Reserved tokens/cost are worst-case bounds, not observed usage or proof of provider pricing.

Only documented candidate operations have fixed command adapters. Kilo's `debug skill` and Gemini CLI's `skills list` remain distinct; Claude and OpenCode behavior use their own headless surfaces. Other discovery surfaces require retained interactive or version-specific API evidence after setup. An undocumented command, unsafe startup, or unavailable client leaves the target unverified rather than substituting another client. No live capture runs as part of default CI or offline replay.

## CI Adapters

Enterprise pipeline configurations:
- **GitLab CI:** `adapters/ci/gitlab-ci.yml`
- **Azure DevOps:** `adapters/ci/azure-pipelines.yml`
- **Bitbucket Pipelines:** `adapters/ci/bitbucket-pipelines.yml`
- Full documentation in [adapters/ci/README.md](file:///home/achmadkurnianto/PROJECTS/OPEN_SOURCES/ai-native-sdlc-plus/adapters/ci/README.md)
