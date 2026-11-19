# owned-runtime-lifecycle Specification

## Purpose

Make installed runtime state inspectable and maintainable without losing ownership history, overwriting user work, or treating editable metadata as authority to delete arbitrary files.

## Requirements

### Requirement: Existing ownership records remain compatible
Lifecycle operations SHALL preserve the version-1 ownership record shape, hash semantics, path checks, and legacy installer entry points. They SHALL account for recognized previously managed files rather than silently dropping records when the current selection changes. Invalid or unsupported state SHALL fail before mutation.

#### Scenario: Adopt an existing version-1 installation
- **GIVEN** a valid existing version-1 installation record
- **WHEN** the installation is inspected or updated
- **THEN** its recorded files remain understandable and unchanged user content is not reclassified through a silent state migration

#### Scenario: Malformed ownership state
- **GIVEN** ownership state with unsafe paths, duplicate keys, unsupported fields or version, or invalid hashes
- **WHEN** a lifecycle operation validates that state
- **THEN** it reports an error without rewriting or deleting project files

### Requirement: Status is read-only and evidence-based
Status SHALL report missing, matching, modified, and update-eligible managed files against the invoked runtime and current canonical policy, along with intentionally user-owned inputs. It SHALL not fetch an unspecified latest release, repair state, or infer an installed release identity from an opaque hash without evidence.

#### Scenario: Inspect an edited installation
- **GIVEN** an installation containing unchanged, missing, and user-modified managed files
- **WHEN** status inspects it
- **THEN** status distinguishes those states and leaves all files and ownership records unchanged

### Requirement: Update uses explicit trusted runtime content
Update SHALL use the invoked or explicitly selected trusted distribution, validate the complete intended operation before publication, and overwrite only recognized files that still match their owned state. It SHALL preserve canonical user policy and unrelated files, with no implicit network upgrade or force-overwrite mode.

#### Scenario: Safe update
- **GIVEN** managed outputs that are unmodified and a compatible selected distribution with new content
- **WHEN** update reconciles the installation
- **THEN** it installs the new owned content, retains user policy, and records verified resulting hashes

#### Scenario: Update conflict
- **GIVEN** a planned replacement that conflicts with user edits or an unsafe path
- **WHEN** update performs preflight
- **THEN** it refuses mutation and identifies the conflict instead of accepting new hashes as proof of ownership

### Requirement: Uninstall removes only eligible owned output
Uninstall SHALL delete only recognized toolkit outputs whose current type/content still matches valid ownership records. It SHALL retain `AGENTS.md`, unowned files, and unrelated directories. Metadata alone SHALL not authorize unrecognized or unsafe paths; symlinks and modified files SHALL not be deleted. A blocked or incomplete removal SHALL not be reported as clean success.

#### Scenario: Clean uninstall
- **GIVEN** recognized managed outputs that remain unchanged
- **WHEN** uninstall validates and removes the installation
- **THEN** it removes eligible outputs and completed ownership state while retaining canonical project policy and unrelated content

#### Scenario: Forged or edited removal target
- **GIVEN** ownership metadata naming unrelated content or an owned file that has changed
- **WHEN** uninstall validates the requested removal
- **THEN** it refuses the unsafe removal and reports the retained paths without deleting them

### Requirement: Publication failures remain observable
Lifecycle operations SHALL revalidate relevant source/target state before publication and report partial failure honestly. They SHALL not claim whole-install atomicity beyond their implementation or publish ownership metadata asserting files that were not verified. Retrying a failed operation SHALL remain conservative and idempotent.

#### Scenario: Target changes after preflight
- **GIVEN** a planned lifecycle operation that passed initial preflight
- **WHEN** a target or canonical input changes before publication
- **THEN** the operation stops without silently incorporating the concurrent change into ownership

#### Scenario: A late write fails
- **GIVEN** a lifecycle publication where an earlier permitted file operation completed
- **WHEN** a later write fails
- **THEN** the result identifies the incomplete operation and recovery needs, preserving honest state rather than reporting a fully installed or removed bundle
