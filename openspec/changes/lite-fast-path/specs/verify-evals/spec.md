## ADDED Requirements

### Requirement: Ceremony runs use committed preregistration
Ceremony cases, boundaries, comparison flow, metrics, repeats, criteria, and finite per-lane token budgets SHALL be declared and committed before benchmark execution. A run SHALL identify that registration and tested revision. Missing registration or budgets SHALL prevent a passing measurement claim, and criteria SHALL NOT be retuned after results to flatter the suite.

#### Scenario: Run a registered case
- **WHEN** an authorized measurement starts
- **THEN** it records the committed case/criterion identity, tool and policy versions, execution boundary, and comparison inputs before collecting results

#### Scenario: Registration is incomplete
- **WHEN** required criteria, finite lane budgets, or registration identity are missing
- **THEN** the measurement is blocked or unverified rather than using an implicit unlimited budget or a post-run threshold

### Requirement: Ceremony reports contain observed timings and outcomes
Lite, Standard, and Critical fixtures and their comparison flow SHALL have scripted observed results with steps, elapsed time, failures, reruns, and approval requirements/events distinguished. Estimates and synthetic fixture metadata SHALL NOT be described as measured human review time or genuine approval. Unobserved hosted/merge latency SHALL remain unverified.

#### Scenario: Lite acceptance target
- **WHEN** the registered Lite workflow is measured
- **THEN** the report evaluates the existing under-five-minute and zero-workflow-pre-approval target within the declared boundary and publishes a miss if either condition fails

#### Scenario: A run stops for human evidence
- **WHEN** a Standard/Critical run cannot complete without unsupplied human input
- **THEN** the report records the stop and observed duration without inventing completed review events or a completed end-to-end time

### Requirement: Token measurements require actual loader evidence
Per-lane loaded-token claims SHALL come from a recorded selected agent/loader run with input provenance and token accounting. Reports SHALL separate description/catalog context, router, loaded skill bodies, and other or unobservable context. Declared file selection, assembled payload size, or character estimates SHALL NOT satisfy an actual-loaded metric.

#### Scenario: Actual context is observed
- **WHEN** a run supplies loader/input records and valid token accounting
- **THEN** the report identifies the loaded sources and hashes, model/tokenizer or provider accounting, measurement checkpoint, and comparison with the preregistered lane budget

#### Scenario: Unexpected bodies are loaded
- **WHEN** the selected loader loads additional skills or repeated content
- **THEN** those inputs remain in the measurement and are not discarded to make the expected router-plus-required-skills budget pass

#### Scenario: Loader or accounting is unavailable
- **WHEN** the actual input set or token accounting cannot be established
- **THEN** the loaded-token result stays unverified, without substituting `chars/4`, declared payload tokens, or zero

### Requirement: Dogfood metrics identify their actual sources
The dogfood report SHALL identify its repository/range, current policy, and sources for lane history, PR sizes, workflow reruns/failures, and overhead. It SHALL distinguish path-only backtests from full change metadata, commits from PRs, and missing labels from measured zero errors. Missing provider data SHALL remain unavailable rather than inferred from commit messages.

#### Scenario: Git-only history
- **WHEN** only Git data and a path-based backtest are available
- **THEN** the report labels those limits and does not claim observed PR sizes, historical gate enforcement, or CI failure/rerun counts

#### Scenario: Provider metadata is available
- **WHEN** authorized read-only PR/workflow data is collected
- **THEN** the report records the actual source/run identifiers and aggregation rules without modifying repository settings or publishing anything

### Requirement: New measurements supersede estimates without rewriting history
`evals/ceremony-measured.md` SHALL contain the new observations and limitations. Current documentation SHALL use those results or mark missing measurements unverified. Earlier ceremony and footprint records SHALL remain identifiable historical artifacts; negative results, changed methods, and comparison gaps SHALL NOT be erased or relabeled as successful measurements.

#### Scenario: Replace a current estimated claim
- **WHEN** new measured evidence is available
- **THEN** current references point to it and clearly distinguish it from the retained earlier estimate and its method

#### Scenario: A target or comparison is not met
- **WHEN** a measured result regresses or required data is missing
- **THEN** the report publishes the negative or unavailable result and a scoped correction plan without changing the criterion after the run
