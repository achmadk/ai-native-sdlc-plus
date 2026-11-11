# Spec Delta: verify-evals

## ADDED Requirements

### Requirement: Semantic test verification with JUnit XML parsing
The system SHALL support a `--junit <path>` parameter in `redgreen.py` to inspect test execution results using standard-library XML parsing, detecting collection crashes, identifying zero-test executions, and validating that tests mapped to acceptance criteria actually ran.

#### Scenario: Collection crash is distinguished from red failure
- **WHEN** a test execution crashes during module import or collection on the base commit
- **THEN** `redgreen.py` reports a collection error rather than classifying the failure as a valid red assertion test

#### Scenario: Zero test run is rejected on head
- **WHEN** the test runner completes with exit code 0 but executes zero tests (`tests="0"`)
- **THEN** `redgreen.py` rejects the run with `NO_TESTS` or failure rather than classifying it as green

#### Scenario: Declared acceptance criteria tests are verified in report
- **WHEN** acceptance criteria units in `tasks.md` specify mapped test identifiers
- **THEN** `redgreen.py` checks that each mapped test identifier appears in the JUnit XML `<testcase>` records

