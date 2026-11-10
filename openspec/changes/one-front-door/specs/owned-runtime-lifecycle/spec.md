## Purpose

Make installed runtime state inspectable and maintainable without losing ownership history, overwriting user work, or treating editable metadata as authority to delete arbitrary files.

## ADDED Requirements

### Requirement: Existing ownership records remain compatible
Lifecycle operations SHALL preserve the version-1 ownership record shape, hash semantics, path checks, and legacy installer entry points. They SHALL account for recognized previously managed files rather than silently dropping records when the current selection changes. Invalid or unsupported state SHALL fail before mutation.

#### Scenario: Adopt an existing version-1 installation
- **WHEN** a valid existing installation is inspected or updated
- **THEN** its recorded files remain understandable and unchanged user content is not reclassified through a silent state migration

#### Scenario: Malformed ownership state
- **WHEN** state has unsafe paths, duplicate keys, unsupported fields/version, or invalid hashes
- **THEN** the operation reports an error without rewriting or deleting project files

### Requirement: Status is read-only and evidence-based
Status SHALL report missing, matching, modified, and update-eligible managed files against the invoked runtime and current canonical policy, along with intentionally user-owned inputs. It SHALL not fetch an unspecified latest release, repair state, or infer an installed release identity from an opaque hash without evidence.

#### Scenario: Inspect an edited installation
- **WHEN** the installation contains unchanged, missing, and user-modified managed files
- **THEN** status distinguishes those states and leaves all files and ownership records unchanged

### Requirement: Update uses explicit trusted runtime content
Update SHALL use the invoked or explicitly selected trusted distribution, validate the complete intended operation before publication, and overwrite only recognized files that still match their owned state. It SHALL preserve canonical user policy and unrelated files, with no implicit network upgrade or force-overwrite mode.

#### Scenario: Safe update
- **WHEN** managed outputs are unmodified and a compatible distribution provides new content
- **THEN** update installs the new owned content, retains user policy, and records verified resulting hashes

#### Scenario: Update conflict
- **WHEN** any planned replacement conflicts with user edits or an unsafe path
- **THEN** preflight refuses mutation and identifies the conflict instead of accepting new hashes as proof of ownership

### Requirement: Uninstall removes only eligible owned output
Uninstall SHALL delete only recognized toolkit outputs whose current type/content still matches valid ownership records. It SHALL retain `AGENTS.md`, unowned files, and unrelated directories. Metadata alone SHALL not authorize unrecognized or unsafe paths; symlinks and modified files SHALL not be deleted. A blocked or incomplete removal SHALL not be reported as clean success.

#### Scenario: Clean uninstall
- **WHEN** all recognized managed outputs remain unchanged
- **THEN** uninstall removes eligible outputs and completed ownership state while retaining canonical project policy and unrelated content

#### Scenario: Forged or edited removal target
- **WHEN** ownership metadata names unrelated content or an owned file has changed
- **THEN** uninstall refuses the unsafe removal and reports the retained paths without deleting them

### Requirement: Publication failures remain observable
Lifecycle operations SHALL revalidate relevant source/target state before publication and report partial failure honestly. They SHALL not claim whole-install atomicity beyond their implementation or publish ownership metadata asserting files that were not verified. Retrying a failed operation SHALL remain conservative and idempotent.

#### Scenario: Target changes after preflight
- **WHEN** a target or canonical input changes between planning and publication
- **THEN** the operation stops without silently incorporating the concurrent change into ownership

#### Scenario: A late write fails
- **WHEN** publication fails after an earlier permitted file operation
- **THEN** the result identifies the incomplete operation and recovery needs, preserving honest state rather than reporting a fully installed or removed bundle
