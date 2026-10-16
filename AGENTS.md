# Agent Guidelines for AI-native SDLC

This repository enforces an evidence-based, risk-proportional SDLC gate (`scripts/evidence_check.py`).

## 1. Classify Before Coding
Always run the lane classifier on the paths you intend to touch:
```bash
python3 scripts/lane.py --paths <files...>
```
- **Lite:** Docs, comments, low-risk test tweaks. Needs short intent, test changes, and trace block.
- **Standard:** Normal feature/bugfix code. Needs an approved spec, test changes, trace block, and review notes.
- **Critical:** Security, auth, migrations, CI workflows, hooks, or payment logic. Needs formal intent, spec, threat note, failing-first test verification, trace block, 2-reviewer notes, and rollout/rollback plan.

## 2. Red-to-Green Test Verification
Before writing implementation code for a fix or feature:
1. Write the test that asserts the intended behavior.
2. Confirm the test fails on base/current code.
3. Use `scripts/redgreen.py` to produce deterministic red-to-green proof for the PR trace.

## 3. Pull Request Requirements
Every PR description must carry evidence matching its lane:
- `## Intent` (Lite) or `Spec: path/to/spec.md` (Standard/Critical)
- `## Trace` (Tools used, key decisions, rejected alternatives, attribution trailers)
- `## Review notes` (What was verified, known edge cases)
- `## Threat note` (Critical only: boundaries, failure modes, data security)
- `## Rollout plan` (Critical only: canary stages, monitoring signals, rollback steps)

Verify evidence locally before pushing:
```bash
python3 scripts/evidence_check.py --lane <Lane> --present <evidence_keys...>
```
