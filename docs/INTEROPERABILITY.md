# Upstream Specification Interoperability Guide

This guide describes how `ai-native-sdlc-plus` integrates with existing upstream specification frameworks—**OpenSpec** and **GitHub Spec Kit**—allowing teams to validate their existing specifications as lane-appropriate evidence without duplicating documents or rewriting into native format.

---

## 1. Supported Upstream Bundles

The spec validator (`check_spec.py`) and evidence gate (`scripts/sdlc.py check evidence` / `evidence_check.py`) accept supported directory bundles in-place:

| Framework | Directory Profile | Required Bundle Members | Evidence Resolution |
| --- | --- | --- | --- |
| **OpenSpec** | Change folder (`openspec/changes/<change>/`) | `proposal.md`, at least one `specs/**/spec.md`, `design.md`, `tasks.md` | `proposal.md` supplies intent; deltas supply acceptance units; `design.md` supplies architecture/plan context; `tasks.md` supplies test mappings and approval metadata. |
| **Spec Kit** | Feature folder (`specs/<feature>/`) | `spec.md`, `plan.md`, `tasks.md` | `spec.md` supplies user stories/scenarios, status, and FR/SC context; `plan.md` supplies constraints; `tasks.md` supplies test mappings and approval metadata. |
| **Critical Extension** | Either framework | `threat-note.md`, `rollout-plan.md` (in addition to base profile) | Required for Critical changes. Both artifacts must contain substantive content (>= 20 non-filler characters); placeholder or empty artifacts are rejected. |

---

## 2. Scenario-to-Test Mapping Format

Both OpenSpec and Spec Kit record their SDLC evidence within their existing `tasks.md` document under a `## SDLC evidence` section.

### Metadata Header
```markdown
## SDLC evidence

Status: approved
Approved-by: Dana Lee (2026-11-10)
```
- `Status`: `draft` or `approved`.
- `Approved-by`: `Name (YYYY-MM-DD)` format.
- For Spec Kit, status and approval may alternatively be declared in the header of `spec.md`.

### Evidence Mapping Table
```markdown
| Source | Unit | Test | Fails before | Expected result |
| --- | --- | --- | --- | --- |
| specs/widget/spec.md | ["ADDED", "Create widget", "Valid creation"] | tests/test_widget.py::test_create | endpoint does not exist yet | status code 201 |
```

- **Source**: Bundle-relative path to the specification file containing the unit.
- **Unit**: Native acceptance unit identifier encoded as a JSON array string:
  - **OpenSpec ADDED/MODIFIED**: `["ADDED", "<Requirement Title>", "<Scenario Title>"]` or `["MODIFIED", "<Requirement Title>", "<Scenario Title>"]`.
  - **OpenSpec REMOVED**: `["REMOVED", "<Requirement Title>"]`. Must have Reason and Migration in spec, and an explicit regression test expectation in the table.
  - **OpenSpec RENAMED**: `["RENAMED", "<Old Title>", "<New Title>"]` (or `["RENAMED", "<Title>"]`). Must have an explicit transition expectation.
  - **Spec Kit**: `["<Story ID>", "<Scenario Title>"]`, for example `["US1", "Scenario 1"]`.
- **Test**: Repository-relative path to the test asserting the behavior (`tests/path/test_file.py::test_fn`).
- **Fails before**: Explanation (at least 8 non-filler characters) of why this test fails on current code before the implementation.
- **Expected result**: Measurable outcome. For ADDED/MODIFIED scenarios with an authored `THEN` clause, the mapping reflects that outcome; the mapping cannot silently alter or replace the source `THEN` outcome.
- **Escaped table pipes**: Escaped pipe characters (`\|`) inside table cells survive parsing and decoding.

---

## 3. Workflow-Step-to-Evidence Mapping

The table below maps native `/opsx:*` and logical `/speckit.*` workflow steps to the artifacts they produce, their role in SDLC risk lanes, and remaining verification requirements.

| Workflow Step | Produced Artifacts | SDLC Evidence Role | Remaining Checks & Enforcements |
| --- | --- | --- | --- |
| `/opsx:propose <idea>` | `proposal.md` | Standard/Critical Intent base | Drafting only. Not approved; requires delta specs, design, tasks, and human approval. |
| `/opsx:explore` | Scratch notes / discussion | Context / Discovery | Informational only; not gate evidence. |
| `/opsx:apply` | Code changes, tests, updated `tasks.md` | Implementation & Test Evidence | Tasks must link tests via `## SDLC evidence`. Does not substitute for gate execution. |
| `/opsx:archive` | Merged living specs in `openspec/specs/` | Living spec sync | Pre-archive check: Run `sdlc check evidence` before archiving. |
| `/speckit.specify` | `spec.md` | Feature Intent & Scenarios | Drafting only. Status remains draft until approved. |
| `/speckit.plan` | `plan.md` | Plan & Constraints | Architecture context. Requires tasks and test mappings. |
| `/speckit.tasks` | `tasks.md` | Tasks & SDLC Mapping Table | Must populate `## SDLC evidence` with valid unit tuples and test references. |
| `/speckit.implement` | Code changes & tests | Implementation & Test Evidence | Must verify red-to-green test execution and passing gate check. |

> [!IMPORTANT]
> **Configuration is not execution.** Declaring an extension hook, authoring a template, or checking task checkboxes does not prove that tests ran, reviews occurred, or repository policies were satisfied. Gate enforcement requires running `sdlc check evidence` or `python scripts/evidence_check.py --ci`.

---

## 4. Verification and Checker Invocations

### Validating a Local Bundle
```bash
# Validate an OpenSpec change folder
python scripts/sdlc.py check spec openspec/changes/my-change --lane Standard

# Validate a Spec Kit feature folder
python scripts/sdlc.py check spec specs/my-feature --lane Standard

# Require approved status and verified existing test files
python scripts/sdlc.py check spec openspec/changes/my-change --lane Critical --require-approved --require-tests-exist
```

### Pull Request Evidence Linkage
In your pull request description (or `--pr-body-file`):
```markdown
Spec: openspec/changes/my-change
```
For Critical OpenSpec changes:
- If `Intent link:` is omitted, the gate automatically resolves intent to `openspec/changes/my-change/proposal.md`.
- If `Intent link:` is explicitly provided, that explicit link is validated and must resolve to a valid tracked blob.
- `threat-note.md` and `rollout-plan.md` in the bundle satisfy the Critical threat note and rollout plan requirements.

---

## 5. Security Architecture, Snapshot Semantics, and Rollback

### Snapshot Semantics
The evidence gate (`scripts/evidence_check.py`) enforces strict Git commit snapshot semantics:
- All constituent bundle members are resolved strictly as regular tracked blobs (`100644 blob` or `100755 blob`) within the evaluated Git tree (`SDLC_HEAD` in CI or current commit).
- The gate never reads candidate checkout bytes, untracked working-tree files, or newer commits. Even if a local file is modified or repaired in the working directory, the gate will fail if the committed blob is invalid or missing.
- Symlinks, gitlinks (submodules), and uncommitted modifications are rejected with actionable errors.

### Trusted Dependency Delivery in CI
In automated CI runners (such as `skills/ai-sdlc/assets/ci-generic.sh` and `.github/workflows/sdlc-gate.yml`):
- All gate tooling (`scripts/evidence_check.py`, `scripts/lane.py`, `scripts/lane-config.yaml`) and helper modules (`skills/spec-first/scripts/spec_inputs.py`) are extracted **exclusively from the trusted base commit (`SDLC_BASE`)**.
- A candidate PR cannot weaken, inject, or tamper with the validator by committing modified or forged helpers in the branch.
- Older base commits lacking `skills/spec-first/scripts/` continue to function for standard single-spec files. If an upstream folder bundle is evaluated on an older base commit lacking the helper, the gate fails closed with a tooling error (exit code 3) rather than accepting unverified input.

### Bootstrap-Compatible PR References
Pull request descriptions remain backward compatible:
- Single-file specification paths (`Spec: specs/user-service.md`) remain fully supported.
- Folder-based specification bundles (`Spec: openspec/changes/user-service` or `Spec: specs/user-service`) are detected and validated transparently.
- Explicit `Intent link:` declarations remain supported for all lanes. For OpenSpec Critical bundles, omitting `Intent link:` defaults to `proposal.md` within the bundle.

### Static Verification vs Dynamic Execution
- **Non-executed test expectations**: The spec checker and evidence checker statically verify that referenced test paths and functions exist, follow required conventions, and contain non-filler justification. They do not execute the test runner. Dynamic red-to-green proof requires running `scripts/redgreen.py`.
- **Unverified URLs**: External URLs declared in intent or spec documents are validated for format and domain reachability rules, but content verification remains subject to reviewer attestation.

### Rollback and Revert Safety
- The gate maintains no mutable state, background daemon, or hidden cache.
- Reverting a change commit via `git revert` returns the gate policy and specification tree to the exact prior snapshot state immediately.


