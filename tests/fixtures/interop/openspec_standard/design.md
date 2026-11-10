# Design: Widget Management

## Context
See proposal.md - Why. Extends the service layer with standard HTTP handlers.

## Goals / Non-Goals
**Goals:** Add REST endpoints for widget creation and query.
**Non-Goals:** Batch widget deletion or async exports.

## Decisions
- Use in-memory SQLite for tests.
- Validate names with regex `^[a-zA-Z0-9_-]+$`.

## Risks / Trade-offs
[High concurrency] -> Connection pooling with retry.

