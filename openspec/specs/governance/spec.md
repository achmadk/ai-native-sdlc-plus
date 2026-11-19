# governance Specification

## Purpose

Gives leaders policy, rollout, and measurement tools to govern agent autonomy and reinvest AI capacity gains into quality, while protecting junior understanding of the systems they ship.

## Requirements

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

The system SHALL tag every non-trivial quality or outcome claim as report-stated, measured-here, or extrapolated, flagging where evidence is silent, and SHALL publish supported adoption positions. Current measured claims marked in `README.md`, `LIMITATIONS.md`, or `PATCH-NOTES.md` SHALL resolve to fields in a revision-bound verification receipt and fail validation when their value, status, unit, or tested revision is stale.

#### Scenario: Survey figure cited honestly
- **GIVEN** a perception-survey figure from an identified external source
- **WHEN** documentation cites that figure
- **THEN** it is tagged report-stated and phrased as respondent perception rather than a measured project outcome

#### Scenario: Regulated use is marked unsupported
- **GIVEN** a regulated-compliance use case and unresolved evidence gaps
- **WHEN** the adoption table is evaluated
- **THEN** it marks the position unsupported with the specific gaps named

#### Scenario: Current measured claim matches its receipt
- **GIVEN** a recognized current-claim marker and a complete verification receipt for the cited tested revision
- **WHEN** claim validation runs offline
- **THEN** the rendered value, unit, status, and revision match the referenced receipt field exactly

#### Scenario: Current measured claim has drifted
- **GIVEN** a marked current claim whose value, unit, status, revision, or receipt field differs from the latest applicable receipt
- **WHEN** the documentation test runs
- **THEN** it fails and names the claim marker and mismatched field

#### Scenario: Historical measurement remains historical
- **GIVEN** a dated historical result not marked as current
- **WHEN** current-claim validation runs
- **THEN** it remains unchanged and is not compared to a newer receipt or silently presented as current evidence

### Requirement: Aggregate verification emits a revision-bound receipt
The system SHALL run unit discovery, mutation checks, doctor-on-self, and footprint verification through fixed trusted entry points and SHALL atomically write a versioned JSON receipt containing the tested commit, tree state, UTC date, Python/platform identity, command vectors, per-stage status, exit codes, counts, limitations, and overall status. A failed stage SHALL remain in the receipt and SHALL produce a nonzero command result.

#### Scenario: Complete offline verification succeeds
- **GIVEN** a clean committed revision and all required local verification capabilities
- **WHEN** aggregate verification completes every fixed stage successfully
- **THEN** the receipt records each successful stage and the overall status is passing for the tested revision

#### Scenario: Verification stage fails
- **GIVEN** a deterministic unit, mutation, doctor, or footprint failure
- **WHEN** aggregate verification runs
- **THEN** it returns nonzero and atomically records the failed stage without reporting later skipped stages as passed

#### Scenario: Working tree differs from the tested commit
- **GIVEN** tracked or relevant untracked inputs that differ from the recorded commit
- **WHEN** aggregate verification records provenance
- **THEN** the receipt marks the tree dirty and cannot support a clean-revision claim

#### Scenario: Receipt output is interrupted
- **GIVEN** an existing valid receipt and an interrupted or failed replacement write
- **WHEN** aggregate verification attempts to publish the new receipt
- **THEN** the previous receipt remains intact and no partial JSON file is accepted

### Requirement: Footprint separates catalog, bodies, and lane load
The verification receipt SHALL report description-catalog size, total skill-body size, and maximum observed per-lane loaded context as separate fields with units, source hashes, accounting method, and status. Character estimates or declared file lists SHALL NOT be labeled observed tokens; missing loader or token evidence SHALL remain `unverified` instead of zero.

#### Scenario: Actual loader accounting is available
- **GIVEN** a committed loader record matching the catalog, router, skill-body hashes, lane, checkpoint, and tested revision
- **WHEN** footprint verification consumes the record
- **THEN** it reports the three footprint values with observed token accounting and identifies unexpected or repeated loaded content

#### Scenario: Loader accounting is unavailable
- **GIVEN** exact catalog and body bytes but no matching actual loader token record
- **WHEN** footprint verification runs
- **THEN** it reports exact byte counts, marks token and maximum-lane observations unverified, and does not synthesize a `chars/4` value

#### Scenario: Loader record omits delivered content
- **GIVEN** a loader record whose listed sources or hashes do not cover the delivered catalog, router, or skill bodies
- **WHEN** footprint verification validates provenance
- **THEN** the footprint stage fails rather than discarding the unexpected or repeated content
