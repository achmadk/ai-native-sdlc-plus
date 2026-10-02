# Gap Analysis — 2026-10-02

Sources checked: timwukp/ai-native-sdlc repo front page (training portal, six stages, intent chain, verify.py stdlib, privacy scanner, fail-open hook / fail-closed CI framing), github/spec-kit front page (SDD plus bug-fix and assessment extensions, templates, CLI). Superpowers, OpenSpec internals, and GSD harnesses: unverified from this pass (docs not fetched); rows marked unverified below.

## What incumbents do well (match or exceed)

| Strength | timwukp/ai-native-sdlc | spec-kit | Superpowers / OpenSpec / GSD |
|---|---|---|---|
| Deterministic enforcement (hook fail-open + CI fail-closed, required-check honesty) | Yes — verified: hook fails open, PR check fails closed, green check is not a gate until branch protection requires it | Partial — verified: structured skills and checks; required-check wiring unverified | unverified |
| Mutation-tested scripts | Claimed in brief; file-level verification unverified | unverified | unverified |
| Threat model + clean scan + limitations published | Yes — verified: privacy scanner, limitations framing, 36/80 control rubric self-score | Partial — verified: SECURITY/CONTRIBUTING exist; threat-model depth unverified | unverified |
| Versioned COMPATIBILITY | unverified | Verified: CHANGELOG + releases exist; policy depth unverified | unverified |
| Trigger evals | Claimed; detail unverified | unverified | unverified |

## Our differentiators vs what was found (validate or drop)

1. Risk-proportional lanes — no lane system found on either front page; holds as differentiator pending deeper check.
2. Whole-SDLC including right-of-code (review/ship/monitor/incident loops) — timwukp portal covers six stages with gates; spec-kit covers SDD + bug-fix + assessment. Right-of-code rollout/observability depth beyond CI gate: likely differentiator, mark partially-validated.
3. Context packs closing the context gap — not found on either front page; holds.
4. Reasoning capture as PR byproduct — timwukp intent chain is adjacent (accepted intent/spec/plan bound to commit); byproduct trace without extra paperwork remains differentiating in degree, not kind.
5. Two audiences (IC + leader policy/measurement) — both incumbents read IC-process-first; holds.
6. Human-skill preservation (explain-back, learning-mode) — not found; holds.
7. Composable/portable via thin adapters — spec-kit has integrations matrix; thin-adapter claim holds only if our adapters stay shims (risk noted).
8. Measured quality with with-skill vs baseline — timwukp verify.py model is strong precedent to match; our broader eval battery (trigger, ceremony, context-gap, reconstruction, footprint) would exceed if executed honestly.

## Where they are better today

- timwukp: worked example history (intent chain readable in repo), honest control rubric, offline-first single-file portal, privacy scanner with never-print-values rule.
- spec-kit: maturity at scale (140k stars, extensions/presets/bundles, multi-agent integrations, docs site), existing-project onboarding path.

## Assumptions carried forward

- Lane config defaults need first-repo calibration (versioned, overridable).
- Judge model + sampling rate swappable; criteria shape fixed.
- Three adapters in phase one; GSD depth deferred on measured demand.
