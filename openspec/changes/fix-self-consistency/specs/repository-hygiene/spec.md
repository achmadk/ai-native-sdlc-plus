## Purpose

Keeps the published repository reproducible by separating authored product sources from local runtime and generated contributor artifacts, while preserving local configuration and the intended product-skill inventory.

## ADDED Requirements

### Requirement: Tracked source excludes local generated artifacts

Tracked source SHALL exclude compiled Python bytecode, the reviewed local continuation-state files and session dump, and the identified generated OpenSpec skill copies in contributor-tool directories. Ignore rules and a source-index check SHALL make recurrence visible. Cleanup MUST be limited to the reviewed inventory and MUST NOT remove authored runtime code, product skills, adapters, project specifications, or unrelated files through broad path matching.

#### Scenario: Reviewed inventory is untracked
- **WHEN** the authorized WS0 cleanup is applied to the recorded baseline
- **THEN** the 42 identified entries are absent from the Git index and the applicable artifact classes remain ignored

#### Scenario: Generated artifacts are staged again
- **WHEN** a source checkout stages an excluded generated or local-runtime artifact despite ignore rules
- **THEN** the source-index hygiene check fails and names the offending path without printing its contents

#### Scenario: Cleanup encounters an unreviewed path
- **WHEN** discovery finds additional or differently named candidates outside the approved inventory
- **THEN** cleanup stops for scope review rather than deleting or untracking those paths automatically

### Requirement: Contributor regeneration preserves local configuration

Removing generated files from version control SHALL preserve their existing working copies unless filesystem deletion is separately authorized. Contributor documentation SHALL distinguish generated OpenSpec instructions from authored product adapters and explain explicit tool selection and regeneration. Cleanup MUST NOT register agents, initialize or rewrite project settings, overwrite local customizations, or rewrite Git history.

#### Scenario: Existing contributor workspace is preserved
- **WHEN** the reviewed generated files are removed from tracking
- **THEN** their local contents remain available and authored adapters, agent entry files, and unrelated configuration are unchanged

#### Scenario: Fresh contributor clone needs generated instructions
- **WHEN** a contributor needs OpenSpec instructions after cloning the cleaned repository
- **THEN** documentation identifies the explicit local regeneration procedure and the contributor selects the tools rather than receiving an implicit registration change

### Requirement: Discovery reflects the shipped product skills

A clean distribution of the candidate SHALL expose exactly the existing ten product skills through the supported Skills CLI listing operation: `ai-sdlc`, `spec-first`, `context-pack`, `review-by-intent`, `decision-trace`, `verify-and-evals`, `ship-and-observe`, `learning-mode`, `autonomy-policy`, and `ai-readiness-and-metrics`. Generated OpenSpec contributor instructions MUST NOT be exported as additional product skills. Verification MUST identify the tested candidate and CLI version and MUST NOT report an unavailable tool or unperformed listing as passed.

#### Scenario: Candidate inventory is listed
- **WHEN** Skills CLI discovery runs against a clean candidate export or clone
- **THEN** the discovered names equal the specified ten-skill set, with no missing skill or generated OpenSpec addition

#### Scenario: Local generated copies remain outside release inventory
- **WHEN** a contributor retains ignored generated instructions locally
- **THEN** they remain outside the tracked distribution used for the product-discovery acceptance check

#### Scenario: Discovery tooling is unavailable
- **WHEN** the required listing tool or an authorized execution environment is unavailable
- **THEN** verification records the missing prerequisite and remains incomplete rather than installing tools or claiming the expected count without execution
