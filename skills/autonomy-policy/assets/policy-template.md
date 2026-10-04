# Autonomy policy: ___ (team / repo)

Owner: ___    Approved by: ___    Date: YYYY-MM-DD    Next review (default 90 days): YYYY-MM-DD
Status: draft | active

## 1. Scope
Repos, agents and tools covered: ___
Out of scope: ___

## 2. Tier by lane
The lane caps the tier. Suggested defaults are in brackets; change them only with a reason.

| Lane | Max tier | Human gate before apply | Review required |
|---|---|---|---|
| Lite | ___ [suggested: 3 for named flows, else 2] | ___ | ___ |
| Standard | ___ [suggested: 2] | ___ [spec approved before build] | ___ |
| Critical | ___ [suggested: 1] | ___ [human applies] | ___ [two-person] |

## 3. Actions
Copy the rows your team uses from `references/action-catalog.md`. "Enforced by" must name a control, or say "norm".

| Action | Tier needed | Unattended? (yes / no) | Enforced by (control or "norm") |
|---|---|---|---|
| ___ | ___ | ___ | ___ |
| Edit gate files (scripts/, .github/workflows/, CODEOWNERS, hooks/) | Human only | No | CODEOWNERS + required review |

Named Tier 3 flows (each one needs a rollback and an owner):
- ___ : trigger ___ ; allowed to ___ ; rollback ___ ; owner ___

## 4. Escalation
The agent submits: action attempted, tier rule and lane, why needed, risk if wrong, rollback.
Who answers: ___    Response window: ___    If nobody answers: blocked (do not proceed).
Routing around a denial is a violation: ___ (who is told)

## 5. Demotion triggers
Drop the affected scope one tier (Critical areas to Tier 1) on: ___ [suggested: incident traced to an agent action, gate bypass, secret exposure, unreviewed Critical change found after merge, failed reconstruction test]
Who decides: ___    Restore when: ___

## 6. Phase and entry evidence
Current phase (individual / pilot / org-wide): ___
Entry evidence for the next phase (cite artifacts, not opinions):
- Gate honesty >= 2: required check proven on ___ (date) by ___
- Trace durability >= ___ : sample of ___ PRs, result ___
- Other: ___
Held for a full review cycle? yes / no

## 7. Exceptions log
| Date | Who approved | What was allowed | Why | Expires |
|---|---|---|---|---|
| ___ | ___ | ___ | ___ | ___ |

## 8. Regulated use
Unsupported today. This suite is not designed or tested against any compliance regime. Compliance owner consulted: ___ (name or "not applicable")

## 9. Review log
| Date | Reviewer | Changes made | Next review |
|---|---|---|---|
| ___ | ___ | ___ | ___ |
