# Interoperability Fixture Provenance

## Environments and Tool Versions
- **OpenSpec**: CLI v1.14.3 (WSL Ubuntu) / v1.17.0 (Windows), profile `spec-driven`. Scaffolding executed via `openspec init --tools none` and `openspec new change <id> --schema spec-driven`.
- **Spec Kit**: Upstream template profile v1.3.2 (`github/spec-kit` spec-template.md, plan-template.md, tasks-template.md).

## Fixtures

### 1. `openspec_standard`
- **Origin**: Scaffolding baseline generated via `openspec new change widget-management --schema spec-driven`.
- **Authored Content**:
  - `proposal.md`: Problem statement, capabilities declaration (`widget-management`).
  - `specs/widget-management/spec.md`: ADDED Requirements (`Create widget`, `Query widget status`) with Given/When/Then scenarios.
  - `design.md`: Context, architectural boundaries, validation decisions.
  - `tasks.md`: Task checklist with `## SDLC evidence` block mapping scenario tuples to tests with fails-before rationale.
- **Approval & Execution Disclaimer**: Synthetic approver `Dana Lee (2026-11-10)` is mock fixture metadata for deterministic testing. No real-agent execution or project approval is claimed.

### 2. `openspec_critical`
- **Origin**: Derived from `openspec_standard` with Critical lane additions.
- **Authored Content**:
  - `proposal.md`, `specs/auth-service/spec.md`, `design.md`, `tasks.md`.
  - `threat-note.md`: Threat considerations covering credential stuffing and HMAC expiry.
  - `rollout-plan.md`: Canary stages, latency/error monitoring signals, and rollback triggers.
- **Approval & Execution Disclaimer**: Synthetic approver `Dana Lee (2026-11-10)` is mock fixture metadata.

### 3. `speckit_standard`
- **Origin**: Spec Kit 1.3.2 feature directory layout (`spec.md`, `plan.md`, `tasks.md`).
- **Authored Content**:
  - `spec.md`: User stories (US1) with numbered scenarios (Scenario 1, Scenario 2), FR-1, SC-1.
  - `plan.md`: Architecture context and technical constraints.
  - `tasks.md`: Task breakdown and `## SDLC evidence` table with native story/scenario unit tuples (`["US1", "Scenario 1"]`).
- **Approval & Execution Disclaimer**: Synthetic approver `Alex Rivera (2026-11-10)` is mock fixture metadata.

### 4. `speckit_critical`
- **Origin**: Derived from `speckit_standard` with Critical lane additions.
- **Authored Content**:
  - `spec.md`, `plan.md`, `tasks.md`.
  - `threat-note.md`, `rollout-plan.md`.
- **Approval & Execution Disclaimer**: Synthetic approver `Alex Rivera (2026-11-10)` is mock fixture metadata.

