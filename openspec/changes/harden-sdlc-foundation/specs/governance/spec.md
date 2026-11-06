## ADDED Requirements

### Requirement: Explicit merge-protection readiness profile

The toolkit SHALL publish a supported GitHub merge-protection profile that requires the `evidence` and `gitleaks` checks from the expected GitHub Actions application, PR-based changes to the protected branch, and required owner review covering the entire gate execution boundary. The profile SHALL require fresh review after reviewable changes and up-to-date branch/check evaluation. Administrative and ruleset bypass settings SHALL be disclosed; absent or inaccessible information MUST NOT be presented as proof that bypass is impossible. A merge queue or unsupported workflow shape SHALL remain outside the verified profile. Installation and planning MUST NOT activate this profile or mutate GitHub settings.

#### Scenario: Evidence check is not required
- **WHEN** the read-only inspection authoritatively finds that `evidence` is not required on the target branch
- **THEN** it reports that the merge gate is not enforced and strict readiness exits nonzero

#### Scenario: Scanner is optional or check identity is wrong
- **WHEN** `gitleaks` is not required or a required context belongs to a different application or merely has a similar name
- **THEN** the profile is not reported ready and the exact missing or mismatched prerequisite is named

#### Scenario: Owner review or review freshness is missing
- **WHEN** ownership files exist but owner review is not required, or reviewable pushes can retain stale approval without a fresh-review control
- **THEN** the inspector distinguishes ownership declarations from enforced review and strict readiness does not succeed

#### Scenario: Unsupported merge queue is enabled
- **WHEN** the target branch requires a merge queue without the separately supported merge-group evidence workflow
- **THEN** readiness reports the unsupported event path instead of claiming the PR-only gate covers queued merges

#### Scenario: Operator receives activation guidance
- **WHEN** an installation lacks one or more protection prerequisites
- **THEN** the toolkit provides read-only diagnostics and separately authorized setup instructions without changing branch rules, bypass actors, or hook configuration

### Requirement: Diagnostics distinguish observed configuration from enforcement

Doctor SHALL distinguish installation health, recognized local workflow shape, observed hosted settings, and controls that remain unverified. Default inspection SHALL remain offline. The existing opt-in remote check SHALL remain supported, and an explicit strict enforcement-readiness invocation MUST fail when a required prerequisite is false, missing, unsupported, or unverified. Positive claims MUST use the exact check identity and expected application identity, not only a matching suffix or any nonzero app ID. Arbitrary workflow text MUST NOT be treated as proven execution merely because it contains expected command or permission strings.

REST inspection SHALL use GET requests. The only permitted POST operation SHALL execute the fixed read-only GraphQL query for merge-queue state, with repository and branch supplied as variables rather than executable query text. Provider mutations MUST NOT be issued.

#### Scenario: Classic merge-queue state needs GraphQL
- **WHEN** classic protection requires a queue-state check that REST cannot establish
- **THEN** doctor may send only the fixed read-only GraphQL query via POST and treats errors or missing data as unverified rather than assuming no queue
- **AND** no configuration write or GraphQL mutation is performed

#### Scenario: Hosted settings are inaccessible
- **WHEN** authentication, API permissions, network access, or provider support prevents inspection of a required setting
- **THEN** the result is unverified with a reason, not a successful enforcement verdict, and strict readiness exits nonzero

#### Scenario: Gate strings occur in a skipped or ignored step
- **WHEN** workflow text contains the expected gate command but an execution condition skips it or failures are ignored
- **THEN** doctor does not report effective enforcement as verified and strict readiness cannot pass

#### Scenario: Recognized complete profile is observed
- **WHEN** the supported workflow profile and all required hosted protection settings are established by read-only evidence
- **THEN** doctor reports the observed branch, exact checks, application identity, ownership/freshness controls, and limits of the inspection without claiming code correctness or runtime agent isolation

#### Scenario: Offline installation health remains available
- **WHEN** doctor runs without the explicit remote-inspection option
- **THEN** it performs no network calls, retains its local health-check contract, and clearly labels hosted merge enforcement unverified
