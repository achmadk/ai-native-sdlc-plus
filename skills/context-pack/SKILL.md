---
name: context-pack
description: "Pack prior decisions, incidents, and standards into a brief with sources. Use when an agent lacks org context or the answer depends on history. Triggers: context brief, prior decisions, incident record, standards doc, staleness check."
---

# context-pack — close the context gap

Agents fail when acceptance criteria live in tickets and decisions live in Slack. You pack what they cannot see.

## Build the brief

1. Gather: prior decisions, relevant incidents, security rules, standards, ticket acceptance criteria.
2. Keep each item to a link plus one-line summary plus staleness date. Reference, never reproduce. Minimum excerpt only.
3. Mark stale or superseded sources explicitly with their replacement.

Why links over copies: briefs rot slower and stay reusable across turns.

## Lane depth

- Lite: pointer list only, max five minutes of reading.
- Standard: short brief with the items that change the answer.
- Critical: full brief with security and incident sections.

## Staleness

Every source carries a date and a freshness window. Past the window, flag stale and name the replacement or say none exists. A brief without dates is unfinished.

