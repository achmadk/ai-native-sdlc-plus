# Spec Delta

## MODIFIED Requirements

### Requirement: With-skill versus baseline deltas
The system SHALL evaluate each skill task both with and without the skill against preregistered prompts and assertions, and SHALL report assertion pass rate, observed token usage, wall time, tested revision, repetitions, and negative results. Automated-judge results SHALL retain the existing caveat and sampled-human-review obligations.

#### Scenario: Negative result is reported honestly
- **GIVEN** a registered paired task case and unchanged pass criteria
- **WHEN** a with-skill run underperforms baseline on any metric
- **THEN** the report publishes the negative delta and scoped correction without relabeling the case or retuning the criterion

#### Scenario: Paired task result is replayed offline
- **GIVEN** recorded with-skill and baseline transcripts whose request, catalog, case, and revision hashes match the registration
- **WHEN** the task evaluation is replayed without a provider or network
- **THEN** it reproduces the assertions, per-pair metrics, caveats, and verdict from the recorded inputs

#### Scenario: Task transcript provenance does not match
- **GIVEN** a task transcript with a mismatched case, revision, catalog, or request hash
- **WHEN** the evaluator attempts to include it in a result
- **THEN** evaluation fails without substituting or partially scoring the transcript

### Requirement: Trigger accuracy with pushy descriptions
The system SHALL publish each product skill description in at most two concise sentences describing what it does and when to use it, with at most one real-language scope sentence. It SHALL measure repeated model selection against preregistered should-trigger and near-miss cases; lexical overlap SHALL be labeled historical and SHALL NOT be presented as agent selection accuracy.

#### Scenario: Near-miss does not trigger
- **GIVEN** a registered near-miss with expected, allowed, and forbidden selections
- **WHEN** the same catalog and request are evaluated for at least three recorded repeats
- **THEN** the product skill's per-case and aggregate false-positive outcomes are reported without a fixture-specific exclusion list

#### Scenario: Description exceeds the public contract
- **GIVEN** a product skill description with more than two sentences or more than one scope sentence
- **WHEN** the catalog is validated before evaluation
- **THEN** validation fails before any selection score is accepted

#### Scenario: Lexical baseline is displayed
- **GIVEN** the retained keyword-overlap experiment and its dated result
- **WHEN** current selection evidence is summarized
- **THEN** the old value is named `lexical overlap` and is not combined with or substituted for model-selection precision or recall

## ADDED Requirements

### Requirement: Selection corpus is preregistered and split
The system SHALL require a committed selection registration with at least 30 should-trigger and 30 near-miss cases across all ten product skills, unique case IDs, development and held-out splits, expected/allowed/forbidden labels, pass criteria, catalog identity, and at least three repeats before accepting a model-selection result.

#### Scenario: Complete registered corpus is accepted
- **GIVEN** a committed corpus meeting the case-count, coverage, split, label, criterion, catalog, and repeat requirements
- **WHEN** evaluation begins against the registered Git revision
- **THEN** the evaluator records the registration identity and reports development and held-out outcomes separately

#### Scenario: Incomplete or post-run registration is rejected
- **GIVEN** a corpus with missing coverage, labels, finite criteria, catalog identity, repeats, or a registration not committed before its transcripts
- **WHEN** a result is evaluated
- **THEN** the result is blocked rather than assigned implicit defaults or a passing score

#### Scenario: External distractors are measured reproducibly
- **GIVEN** pinned, attributed OpenSpec and Superpowers skill-description snapshots in the registered catalog
- **WHEN** product-skill selection is evaluated offline
- **THEN** confusion with each external distractor is scored from the committed snapshot without a network fetch

### Requirement: Provider recording is capped and replayable
The system SHALL support an explicitly configured provider process for authorized live recording, enforce finite request and cost limits, and store redacted transcripts with provider/model identity, usage, response, registration hash, request hash, catalog hash, tested revision, repeat, and timestamp. Default CI SHALL use deterministic offline replay and SHALL NOT require credentials or network access.

#### Scenario: Authorized provider recording stays within limits
- **GIVEN** a local provider test double, explicit request and cost caps, and a valid registration
- **WHEN** live-record mode runs
- **THEN** each request is accounted for and recording stops nonzero before another request could exceed either cap

#### Scenario: Provider cost cannot be established
- **GIVEN** a provider response without usable cost accounting
- **WHEN** a monetary-cap claim is requested
- **THEN** the cost result is `unverified` and cannot satisfy the cap, while observed request and token counts remain separately reported

#### Scenario: Offline replay invokes no provider
- **GIVEN** complete committed transcripts matching the registered inputs
- **WHEN** replay runs in an environment with no provider command or credentials
- **THEN** it produces the same selection records and aggregate metrics without attempting an external process or network call

#### Scenario: Transcript contains a secret-shaped field
- **GIVEN** a provider response or metadata field containing configured credential material or a recognized secret pattern
- **WHEN** the recorder prepares a persistent transcript
- **THEN** recording fails or redacts the field and never writes the credential value
