# spec-first examples

## 1. A vague request, rewritten

Request: "make login faster".

| Draft criterion | Problem | Rewrite |
|---|---|---|
| Login is faster | No threshold, no scenario | AC1: p95 login latency drops \| pass: p95 under 300 ms on fixture warm-cache (800 ms today) |
| Works well on mobile | "Well" is not assertable | AC2: login completes on a throttled connection \| pass: success within 2 s on the 3G profile |
| Secure | Not a behavior | AC3: wrong password is rejected \| pass: HTTP 401 and no session cookie set |

If you cannot name a number, that is an open question for a human, not a reason to keep the adjective.

## 2. A complete Standard spec that passes the checker

```spec
# Spec: faster login
Lane: Standard
Author: Dana Lee
Status: approved
Approved-by: Priya Rao (2026-10-02)

## Intent
Returning users sign in measurably faster without any change to how sessions work.

## Out of scope
- The password reset flow

## Acceptance criteria
- AC1: p95 login latency drops | pass: p95 under 300 ms on fixture warm-cache (was 800 ms)
- AC2: a wrong password is still rejected | pass: HTTP 401 and no session cookie set

## Constraints
- The session cookie format does not change

## Test expectations
- AC1 -> tests/test_login.py::test_p95_latency | fails-before: p95 is 800 ms today, so the assertion fails
- AC2 -> tests/test_login.py::test_bad_password | fails-before: the new cache path does not exist yet, so the test cannot pass

## Assumptions and open questions
- Assumed the warm-cache fixture reflects returning users; confirm with the owner

## Plan
Cache the credential lookup for 60 s and measure on the fixture.
```

## 3. A Lite change

Put this in the PR description:

```
## Intent
Fix the off-by-one in the pagination footer so the last page shows its items. Plan: correct the range in paginate(), add a test for 21 items at page size 10.
```

## 4. When a manual check is legitimate

`- AC4 -> manual: confirm the PDF renders in the print dialog on the three supported browsers | fails-before: the layout overflows today`

The checker warns on every `manual:` line on purpose. Say under Assumptions why it cannot be automated, and who will check it.

## 5. Common mistakes
- A criterion without a pass condition ("AC3: audit log entries exist").
- A test expectation whose `fails-before` is "n/a": a test that never failed proves nothing.
- Specifying the implementation ("use Redis") when only a behavior is required.
- Editing the spec after approval to match the code without re-approval.
