# Spec Delta

## Purpose

Gives leaders policy, rollout, and measurement tools to govern agent autonomy and reinvest AI capacity gains into quality, while protecting junior understanding of the systems they ship.

## ADDED Requirements

### Requirement: Trust tiers with lane-mapped escalation

The system SHALL define trust tiers stating what agents may do unattended, what needs approval, and escalation rules per lane, shipped as a fill-in policy template with a phased rollout plan.

#### Scenario: Unattended action respects tier
- **WHEN** an agent attempts an unattended action outside its tier (e.g., production migration without approval)
- **THEN** the action is held for human escalation citing the tier rule and lane

#### Scenario: Phased rollout progresses by evidence
- **WHEN** a team moves from individual to pilot to org-wide adoption
- **THEN** each phase lists entry evidence required before widening autonomy

### Requirement: Readiness scoring and dividend metrics beyond velocity

The system SHALL score organizational readiness on the governed-system-of-record gap and SHALL recommend quality-weighted metrics (change confidence, maintainability, review latency, rework rate, time to onboard, innovation ratio) with explicit Goodhart warnings, never velocity alone.

#### Scenario: Leader receives reinvestment plan
- **WHEN** capacity gains from AI assistance are measured
- **THEN** the report recommends quality and testing reinvestment first with named metrics and warns where optimizing each metric would distort behavior

### Requirement: Claims ledger and adoption positions

The system SHALL tag every non-trivial quality or outcome claim as report-stated, measured-here, or extrapolated, flagging where source evidence is silent, and SHALL publish an adoption-position table stating which positions (individual, pilot, org-wide, regulated) are supported.

#### Scenario: Survey figure cited honestly
- **WHEN** documentation cites a perception-survey figure
- **THEN** it is tagged report-stated and phrased as what respondents report, never as a measured outcome

#### Scenario: Regulated use is marked unsupported
- **WHEN** a regulated-compliance use case is evaluated
- **THEN** the adoption table marks it unsupported today with the specific gaps named
