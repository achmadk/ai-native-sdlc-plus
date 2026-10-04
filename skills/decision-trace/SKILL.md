---
name: decision-trace
description: "Leave a reconstructible reasoning record as a by-product of the PR, so someone can explain months later what changed, why, and what was rejected. Use when writing the Trace section of a PR, recording why a change was made, reading history, or testing whether reasoning can be reconstructed. Triggers: trace block, decision record, why was this changed, reconstruct reasoning, provenance, ADR."
---

# decision-trace — reasoning as a by-product

Only 15% of ICs (25% of leaders) report being very confident they can reconstruct AI-assisted reasoning after six months [report-stated], and review is the moment where reasoning gets captured or lost. You assemble the trace from work already written, because extra paperwork gets skipped.

## Compose, never retype

Fill `assets/trace-block.md` from what already exists: the intent or spec (link it), the review verdict (link it), and session facts (tool, model, date, what was rejected). No field repeats text written elsewhere. Paste it into the PR description under the heading `## Trace`: the CI gate looks for exactly that heading and for real content under it.

For Critical changes the gate also needs `## Threat note` and `## Rollout plan` as their own sections. Do not repeat them inside the trace.

## Lane sizes

- Lite: Change, Why, Risk accepted.
- Standard: add Alternatives rejected and Test evidence (paste the `redgreen.py` output from `verify-and-evals`).
- Critical: the same, with the threat note and rollout plan as separate sections, and Provenance recorded in detail.

## Provenance: record what you know

Name the tool, the model, and the date. A commit trailer such as `Assisted-by: <tool> <model>` is checkable later with `git log`, unlike a note in a PR. Per-hunk attribution is rarely recoverable, so record it at commit granularity and add paths only where you actually know them. Do not invent attribution to look complete. Say "unknown" instead.

## Promote to a decision record when the decision outlives the PR

If the choice shapes the architecture, is hard to reverse, or others will need to rely on it, write a short decision record (for example `docs/adr/NNNN-title.md`) and link it from the trace. `context-pack` can then cite it, with a date and a freshness rule.

## Redaction

Never put secrets, tokens, credentials, or personal data in a trace. Prefer links to tickets over pasted quotes. If a secret was posted, editing the description does not reliably remove it, because edit history can retain it: rotate the credential. A trace that leaks is worse than none.

## Test it

Run the reconstruction test in `references/reconstruction-test.md`: a reader who was not involved, with no session history, answers four questions from the trace alone. It is also the evidence for the "trace durability" level in `ai-readiness-and-metrics`. If the reader cannot answer, the trace failed.
