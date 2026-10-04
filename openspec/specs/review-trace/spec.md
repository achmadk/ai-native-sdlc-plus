# review-trace Specification

## Purpose

Reviews agent-produced changes against stated intent and risk rather than line by line, and leaves a reconstructible reasoning record as a byproduct of review and the pull request itself.

## Requirements

### Requirement: Intent-anchored review with failure checklist

The system SHALL review each change against its intent and lane risk, applying an AI-specific failure-mode checklist, and SHALL record the verdict plus uncovered intent gaps in the pull request.

#### Scenario: Intent mismatch blocks approval
- **WHEN** implementation diverges from approved intent or acceptance criteria
- **THEN** the review verdict names the violated criterion and requests correction before approval

#### Scenario: AI failure modes are checked
- **WHEN** a change is reviewed
- **THEN** the checklist covers at minimum hallucinated APIs, ignored constraints, untested edge cases, and leaked secrets, with each finding linked to evidence

### Requirement: Explain-back check

The system SHALL require the author to state in their own words why the change works before merge, as a lightweight understanding check that also preserves human skill.

#### Scenario: Author explains reasoning
- **WHEN** a Standard or Critical change is ready for review
- **THEN** the pull request contains a short author explanation of mechanism and risk, distinct from generated summaries

#### Scenario: Junior pairing uses learning mode
- **WHEN** learning mode is enabled for a junior author
- **THEN** the check expands into guided questions that build understanding rather than a single statement

### Requirement: Trace as byproduct with lane-proportional size

The system SHALL auto-draft decision records and prompt/agent trace blocks from the session, spec, and review outputs without requiring separate authoring, sized by lane (Lite minimal, Standard fuller, Critical fullest with threat and rollout links).

#### Scenario: Trace assembles without retyping
- **WHEN** spec and review already state intent and rationale
- **THEN** the trace block is composed from those sources plus session metadata, and no field duplicates already-written content

#### Scenario: Six-month reconstruction succeeds
- **WHEN** a fresh agent with no session history reads only the merged trace six simulated months later
- **THEN** it can state what changed, why, what alternatives were rejected, and what risk was accepted
