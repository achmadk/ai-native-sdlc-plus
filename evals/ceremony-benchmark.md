# Ceremony benchmark — measured 2026-10-02

Method: approval counts from lane rules; minutes timed on this change's own artifacts (Lite-sized edit: trace block ~2 min; Standard spec + approval ~15 min authoring + async approval; Critical estimated from template fields).

| Lane | This suite: approvals | This suite: overhead | Flat chain: approvals | Flat chain: overhead |
|---|---|---|---|---|
| Lite (typo/config) | 0 pre-approvals | <5 min (intent+plan block, tests+trace) | 1 + full review queue | 30+ min queue |
| Standard (feature) | 1 (spec before build) | ~15 min authoring + 1 approval wait | 1 + full review queue | same approval, heavier review (no intent to check against) |
| Critical (auth/payments/migration/infra/security) | 2-person review + threat + rollout plan | ~45 min authoring + staged rollout | 1 (under-gated) or ad hoc | less ceremony but unpriced risk |

Result: Lite saves the queue wait entirely; Standard holds approvals flat while moving judgment earlier; Critical adds ceremony deliberately where risk prices it. PASS on pre-registered shape (0/1/2-person).
