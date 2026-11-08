## Purpose

Protects CI enforcement through immutable action selection, trusted execution boundaries, and honest inspection of supported scanner configurations without confusing recognition with hosted execution proof.

## ADDED Requirements

### Requirement: Trusted scanner compatibility data

Scanner recognition SHALL use a versioned set of reviewed immutable references supplied with the running inspector. An accepted reference MUST identify the expected scanner owner/repository and a full commit SHA, and MUST be present in that trusted set. Recognition MUST continue to enforce the existing bounded workflow, credential, permission, event, and comment-disable requirements. The inspector MUST NOT obtain approvals from the inspected repository, ambient configuration, or an automatic network lookup.

#### Scenario: Shipped reviewed scanner is recognized
- **WHEN** the shipped workflow selects the reviewed Gitleaks v3 reference and satisfies the existing scanner contract
- **THEN** the inspector recognizes that scanner configuration instead of rejecting it solely because a different release was previously hard-coded

#### Scenario: Arbitrary immutable reference is not approval
- **WHEN** a scanner step uses an unlisted full SHA, an unexpected owner/repository, a tag, or a shortened reference
- **THEN** scanner recognition does not report that step as verified and identifies the unsupported or invalid reference

#### Scenario: Invalid trusted data fails visibly
- **WHEN** the inspector's own compatibility data is missing, malformed, unsupported in version, duplicated ambiguously, or contains invalid references
- **THEN** inspection returns an actionable failure without an unhandled traceback or fallback that accepts arbitrary scanner code

#### Scenario: Inspected repository cannot approve its own scanner
- **WHEN** a repository under inspection includes data that lists its otherwise unapproved scanner as supported
- **THEN** the external inspector ignores that attempted approval and evaluates the scanner against its own trusted distribution

#### Scenario: Existing supported reference remains compatible
- **WHEN** the previously supported Gitleaks v2 reference remains in the reviewed compatibility set and its workflow satisfies the existing contract
- **THEN** its structural recognition remains compatible, without claiming that a hosted scan or legacy runtime actually executed

### Requirement: Owned scanner bundle consistency

The toolkit's clean source checkout and its completely installed distribution SHALL pass their own default local doctor inspection without failures. All inspector-owned compatibility data SHALL be included in the owned installation payload and validated as a required part of that inspector bundle. This guarantee MUST NOT suppress genuine warnings or unverified hosted controls, activate hooks, or change repository settings. An external inspector MUST NOT require the inspected repository to supply its own approval registry.

#### Scenario: Source distribution is checked as a whole
- **WHEN** default local doctor inspection runs against the toolkit's real source checkout
- **THEN** the overall failure count is zero, including scanner compatibility, while unresolved external configuration remains honestly reported

#### Scenario: Installed inspector works without source checkout
- **WHEN** a clean target receives the complete payload and the original toolkit source is unavailable
- **THEN** the installed doctor locates its own compatibility data and completes local inspection without failures or source-checkout dependencies

#### Scenario: Inspection does not require target-owned approval data
- **WHEN** an external inspector with a complete trusted bundle checks a compatible repository that has no scanner registry of its own
- **THEN** that absence does not invalidate scanner recognition or allow the target to redefine approvals

#### Scenario: Registry participates in non-destructive ownership
- **WHEN** installation or an owned upgrade would conflict with a locally modified or unowned registry destination
- **THEN** the installer applies the existing conflict and no-overwrite rules instead of replacing local data to force consistency

#### Scenario: Future pin update loses compatibility
- **WHEN** a dependency update selects a scanner revision not yet admitted by a reviewed compatibility update
- **THEN** source/installed consistency verification fails rather than automatically approving the new pin or weakening recognition
