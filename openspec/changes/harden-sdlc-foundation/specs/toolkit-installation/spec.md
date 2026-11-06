## ADDED Requirements

### Requirement: Complete manifest-driven foundation payload

The installer SHALL use one versioned source manifest for POSIX and PowerShell installation. The foundation payload SHALL contain the supported root scripts, canonical spec/brief/red-to-green entry points and their skill-local implementations, referenced skill assets and guidance, the generic CI runner and adapter templates, the PR template, the evidence and secret-scan workflows, and the hook dispatcher and implementations. Installed commands and resources MUST work without the original toolkit checkout. Git metadata, bytecode, caches, raw sessions, and machine-local agent configuration MUST NOT be included.

#### Scenario: Clean target has usable documented commands
- **WHEN** either installer successfully installs the foundation into a clean target
- **THEN** the manifest's required files exist with their expected content and executable modes where applicable
- **AND** the documented root-script entry points and generic CI runner resolve from that target after the original toolkit source is unavailable

#### Scenario: Toolkit source and installed helper paths agree
- **WHEN** an operator invokes `scripts/check_spec.py`, `scripts/check_brief.py`, or `scripts/redgreen.py` in the toolkit checkout or a completed installation
- **THEN** the entry point invokes the same authoritative skill-local implementation and preserves its arguments, output, and exit status

#### Scenario: Local artifacts are excluded
- **WHEN** the source checkout contains ignored caches, a raw session transcript, or machine-local agent files
- **THEN** none of those files enter the destination through installation

### Requirement: Non-destructive managed-file updates

The installer SHALL preflight the entire requested payload before changing destination files. It SHALL retain installed hashes for files it manages. An existing file SHALL be replaceable only when it matches its recorded installed version; a file already identical to the incoming payload SHALL be retained without rewriting. Differing unowned or locally modified files MUST produce an explicit conflict and nonzero exit before payload writes. Missing or malformed ownership state MUST NOT grant overwrite permission.

#### Scenario: Repeated installation is stable
- **WHEN** the same payload is installed again without intervening edits
- **THEN** existing file bytes and modification times remain unchanged and the installer reports the retained files

#### Scenario: Local policy or template is preserved
- **WHEN** a destination lane configuration, PR template, workflow, hook, or skill file differs from both the incoming file and its recorded installed hash
- **THEN** installation reports the conflicting path, exits nonzero, and leaves the destination payload unchanged

#### Scenario: Legacy installation has no ownership record
- **WHEN** installation encounters pre-existing files without valid managed-file state
- **THEN** identical incoming files can be recognized without rewriting, while differing files remain untouched and require manual reconciliation

#### Scenario: Destination changes after preflight
- **WHEN** a managed file changes between the preflight comparison and its replacement
- **THEN** the installer refuses to replace that file, reports the race as an installation failure, and does not claim completion

### Requirement: Contained paths and explicit installation failures

The installer SHALL locate sources relative to its own distribution rather than the caller's working directory. It MUST validate source completeness, runtime prerequisites, and containment of managed destination paths before writing. Symlinks or Windows reparse points that escape the selected root MUST be rejected. Files SHALL be published using per-file atomic replacement, and installation state SHALL describe a completed payload only after verification succeeds. A later I/O failure MUST report which files changed and exit nonzero; all-or-nothing rollback is not implied. Installation MUST NOT execute an arbitrary or stale destination doctor to establish success.

#### Scenario: Installation from a different working directory
- **WHEN** an installer is invoked by absolute path from an unrelated directory and the target path contains spaces
- **THEN** it reads the intended distribution, writes only within the selected target, and produces the same payload as invocation from the toolkit directory

#### Scenario: Missing source or escaping destination
- **WHEN** a required source is missing or a managed path resolves outside the target root
- **THEN** the installer fails during preflight without changing the destination payload

#### Scenario: Copy fails after preflight
- **WHEN** an I/O error occurs after some verified files were installed
- **THEN** the installer returns nonzero, identifies the partial result, and does not publish a successful-installation record or a successful destination health verdict

### Requirement: Installation does not activate external controls

Installation SHALL distinguish files installed, hook activation, and hosted merge enforcement. It MUST NOT change `core.hooksPath`, write `.git/hooks`, register skills with an agent, install dependencies over the network, or modify GitHub settings. It SHALL provide explicit follow-up instructions and report pre-existing activation without claiming installation caused or verified hosted enforcement.

#### Scenario: Existing hook setup is preserved
- **WHEN** a repository already uses another hook manager or has a custom `core.hooksPath`
- **THEN** installation leaves that configuration and existing Git hook files untouched

#### Scenario: Files installed but enforcement not configured
- **WHEN** payload verification succeeds but the hook is inactive or hosted protection has not been checked
- **THEN** the report distinguishes those states from installation success and does not label the repository merge-protected

### Requirement: Consistent supported-platform behavior

POSIX and PowerShell entry points SHALL use the same install plan and failure contract. Interpreter discovery SHALL validate a usable interpreter against the supported Python floor rather than only its command name. The installed Git hook dispatcher SHALL use a supported implementation on Windows as well as POSIX and retain its advisory exit behavior.

Managed `.gitattributes` rules SHALL keep shell entry points in LF form across Git checkout. The attributes file SHALL obey the same non-destructive manifest/ownership contract as other installed files and SHALL be part of the Critical control boundary.

#### Scenario: Checkout does not break the hook interpreter
- **WHEN** installed shell hooks are committed and rematerialized with `core.autocrlf=true`
- **THEN** their shebangs and shell contents retain LF endings and an actual Git-dispatched advisory hook remains executable without changing the user's Git configuration

#### Scenario: Windows has python but not python3
- **WHEN** a supported Windows environment has a working `python` command and no working `python3`
- **THEN** installation and an explicitly activated Git-dispatched hook both locate the supported interpreter rather than silently skipping the advisory check

#### Scenario: Installation fails under PowerShell
- **WHEN** preflight, copying, or installation verification fails through the PowerShell entry point
- **THEN** the caller receives a nonzero native process exit status and an actionable error
