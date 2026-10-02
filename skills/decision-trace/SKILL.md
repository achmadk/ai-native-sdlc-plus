---
name: decision-trace
description: "Leave a reconstructible reasoning record as a PR byproduct. Use when recording why a change was made or reading history months later. Triggers: trace block, decision record, why was this changed, reconstruct reasoning."
---

# decision-trace — reasoning as byproduct

You assemble trace from work already written because extra paperwork gets skipped.

## Compose, never retype

Build the block from spec intent, review verdict, and session metadata (prompts, tool, model, date). No field duplicates text already written; link to it. Template in `assets/trace-block.md`.

## Lane sizes

- Lite: what + why + risk (3 fields).
- Standard: add alternatives rejected and test evidence.
- Critical: add threat note and rollout links.

## Redaction

Scrub secrets, tokens, and personal data before merging. Prefer links to tickets over pasted quotes. A trace that leaks is worse than none.

## Test

Six simulated months later with no session history, a fresh agent reading only the trace must state what changed, why, rejected alternatives, and accepted risk. If it cannot, the trace failed.
