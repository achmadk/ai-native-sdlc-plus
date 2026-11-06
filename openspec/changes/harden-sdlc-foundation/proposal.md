## Why

The toolkit's foundation currently permits destructive installer reruns, incomplete installations, structurally invalid evidence, and under-classified security paths; its PR secret scanner is missing a required token, and the audited repository does not require its evidence check at merge. Fix these concrete gaps before expanding adoption, while keeping the distinction between evidence presence, human review, and verified merge protection explicit.

## What Changes

- Repair the Gitleaks PR integration with the required token and least-privilege permissions, disable unnecessary commenting, and pin enforcement workflow actions to immutable commits.
- Replace unchecked copying with a shared, manifest-driven installation contract: source-relative resolution, complete runtime and referenced resources, conflict detection, managed-file hashes, explicit partial-failure reporting, and repeatable POSIX/PowerShell behavior.
- Provide canonical project-root entry points for the existing spec, brief, and red-to-green helpers without duplicating their implementations. Keep skill discovery and agent registration separate from copying the toolkit payload.
- **BREAKING:** refuse conflicting installer updates instead of overwriting locally modified or unrelated files; return nonzero on incomplete installation. Do not automatically change hooks, agent configuration, or repository settings.
- **BREAKING:** raise the built-in risk floor for the full gate execution boundary and agent-control files; expand shipped nested auth/payment/infrastructure rules; prevent executable or ambiguous changes from receiving documentation-only exemptions. Existing custom lane configurations remain format-version 1 and require explicit calibration rather than replacement.
- Harden Markdown evidence parsing, preserve malformed-path diagnostics, and reject repository metadata or untracked files as local spec/intent evidence. Preserve local advisory behavior and CI failure on missing or indeterminate required evidence.
- Run enforcement tooling with isolated imports from the trusted base revision, including the generic CI runner, so adjacent modules cannot shadow standard-library dependencies.
- Define an explicit merge-protection readiness profile, improve read-only doctor diagnostics, and document separately authorized activation. A local installation or green evidence job must not be described as proof that merges are protected.
- Use GET for REST inspection and a fixed read-only GraphQL query via POST solely to establish merge-queue state; never issue provider mutations. Distribute managed `.gitattributes` LF rules for shell entry points so Windows checkout preserves executable hook scripts.
- Add regression and clean-target integration tests for the shipped policy, installer, helper paths, security workflows, and readiness failure cases; update only documentation affected by these contracts.

## Capabilities

### New Capabilities

- `toolkit-installation`: A complete, non-destructive, manifest-driven toolkit installation with canonical helper paths, safe updates, and actionable failure reporting.
- `ci-security`: Immutable and least-privilege security workflows, functioning PR secret scans, and isolated trusted gate execution.

### Modified Capabilities

- `lane-router`: Conservative shipped risk rules and execution-boundary floors, correct evidence parsing and exemptions, and tracked local evidence references.
- `governance`: Explicit merge-protection prerequisites and read-only readiness reporting that distinguishes observed settings from unverified controls.

## Impact

- Implementation targets: `install.sh`, `install.ps1`, `scripts/`, `hooks/`, `.github/workflows/`, `skills/ai-sdlc/assets/ci-generic.sh`, relevant skill guidance/assets, installer payload metadata, and nearby tests and onboarding documentation.
- Implementation lane: **Critical**, because the change modifies CI, hooks, and the gate itself. Implementation requires approved planning, failing-first regression evidence, a threat note, two independent human reviews, and a staged rollout/rollback record. These artifacts are a proposal, not evidence that those reviews occurred.
- Keep the Python standard-library runtime and existing CLI invocation forms. No Node.js runtime, hosted service, new agent framework, or new OpenSpec schema is required.
- Non-goals: authenticating approvals or waivers, a revision-bound evidence platform, stronger red-to-green verdict semantics, real-agent evaluation infrastructure, runtime agent permission enforcement, regulatory certification, general release/uninstall tooling, and unrelated documentation cleanup.
- External boundary: describe and inspect required-check, owner-review, stale-approval, bypass, and branch-freshness settings, but do not mutate GitHub settings, enable hooks, or activate an organization's workflows as part of this change. Those operational actions require separate explicit authorization.
