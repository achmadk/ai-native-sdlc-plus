## Purpose

Give genuinely low-risk changes a short, fact-grounded drafting and verification path without adding workflow pre-approval or weakening the existing risk and evidence checks.

## ADDED Requirements

### Requirement: Lite eligibility comes from the real change
`sdlc lite` SHALL evaluate an explicitly identified committed change range with the existing classifier and policy. It SHALL resolve revision identities before collecting facts and reject empty, uninspectable, or non-Lite changes without producing a ready Lite result. User labels, output requests, or broad prose rules SHALL NOT override computed risk.

#### Scenario: Genuine Lite change
- **WHEN** the declared range is inspectable and all changes qualify as Lite
- **THEN** the workflow proceeds with the same classification and evidence obligations as the existing checker

#### Scenario: Higher risk or missing inspection
- **WHEN** metadata or paths make the range Standard/Critical, or inspection fails
- **THEN** the command exits nonzero, identifies the actual condition, and directs the user to the normal workflow without a downgrade

### Requirement: Drafts preserve facts and missing knowledge
The command SHALL draft minimal Intent, Plan, and Trace content from supplied intent, recorded commit text, diff metadata, assistance trailers, and explicitly supplied verification receipts. It SHALL identify those sources and distinguish reported receipts from independently verified execution. Unknown rationale, authorship, alternatives, approvals, or risk acceptance SHALL remain unknown rather than fabricated.

#### Scenario: Existing facts avoid retyping
- **WHEN** the input range and supplied metadata contain relevant facts
- **THEN** the draft reuses them with revision/source references without creating a separate specification or inventing judgments

#### Scenario: Required intent is absent
- **WHEN** no usable user intent or recorded intent is available
- **THEN** the draft and diagnostics identify the missing content instead of padding a filename/diff count into a claimed business rationale

#### Scenario: Receipt conflicts with the range
- **WHEN** a supplied receipt is malformed or names a different candidate/baseline
- **THEN** the command reports the problem and cannot use the receipt as passing evidence for this change

### Requirement: The existing evidence check remains authoritative
The Lite workflow SHALL run the real evidence checker against the selected revisions and generated body with fail-closed semantics. It SHALL report actual missing requirements and preserve existing test-change/exemption rules. It SHALL NOT use `--present`, fabricate reviews or test execution, or treat local warning-mode exit zero as proof that requirements passed.

#### Scenario: Evidence is missing
- **WHEN** required intent, trace, or test-change evidence is absent
- **THEN** the workflow reports the checker-derived missing items and returns nonzero

#### Scenario: Trusted documentation exemption applies
- **WHEN** the real checker establishes its existing non-executable exemption for the selected range
- **THEN** the workflow reports that exemption without creating a dummy test change or inventing a new exemption

### Requirement: Lite introduces no workflow pre-approval
The default Lite path SHALL require no additional plan/spec pre-approval beyond the user's authorization to perform the requested work. It SHALL retain explicit file-write consent, tool permissions, project policies, and merge-time obligations. This rule SHALL NOT authorize implementation from an exploration/planning request or waive Standard/Critical approvals.

#### Scenario: Prepared Lite evidence passes
- **WHEN** an authorized Lite change has the required evidence and checks pass
- **THEN** no extra workflow approval step is inserted before the result is produced

#### Scenario: External permission is required
- **WHEN** a tool or project policy requires consent
- **THEN** that consent is retained and separately reported rather than suppressed to improve the ceremony count

### Requirement: Output is non-destructive by default
The command SHALL leave project files, Git state, and hosted state unchanged unless an explicit output file is requested. A requested output SHALL be confined and protected from overwriting differing content or following unsafe links. Machine-readable and human output SHALL distinguish draft content, observed checks, unresolved fields, and unverified claims.

#### Scenario: Preview only
- **WHEN** no output file is requested
- **THEN** the draft/results are emitted without creating files, commits, PRs, or ownership records

#### Scenario: Output would overwrite user work
- **WHEN** the requested output conflicts with existing content or an unsafe path
- **THEN** the command refuses the write and preserves the existing file

### Requirement: Project planning context reflects reality
This repository's OpenSpec context/rules SHALL describe its actual stack, conventions, lane obligations, and command contracts rather than remain scaffold-only. They SHALL be verifiable through the selected OpenSpec CLI and remain guidance, not an enforcement substitute. Active planning configuration and schema controls SHALL remain protected from Lite/exemption bypass.

#### Scenario: Inspect artifact instructions
- **WHEN** the supported OpenSpec CLI returns instructions for this project
- **THEN** the relevant real context/rules appear and agree with the current implementation and approval boundaries

#### Scenario: Planning guidance attempts to lower risk
- **WHEN** a change edits agent-control configuration or guidance suggests skipping required evidence
- **THEN** the independent classifier/checker retains its Critical protection and required checks
