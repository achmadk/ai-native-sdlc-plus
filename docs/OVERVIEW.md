# The suite at a glance

Ten skills, one gate. The skills tell people and agents what to do; the gate checks that the evidence exists.

## The skills, by stage

| Stage | Skill | Main audience | What you get |
|---|---|---|---|
| All | `ai-sdlc` | everyone | Routes a change to its lane (Lite, Standard, Critical), says what evidence the lane owes, and installs and verifies the gate |
| Planning | `spec-first` | ICs | Intent, criteria and test expectations before code; `check_spec.py` |
| Planning | `context-pack` | ICs | A dated, sourced brief of what the agent cannot see; `check_brief.py` |
| Build | `learning-mode` | newer engineers | Guided pairing so AI-generated code is understood, not just shipped |
| Build | `autonomy-policy` | leaders | Trust tiers per lane, an action catalog, escalation, demotion |
| Verify | `verify-and-evals` | ICs | Red-to-green proof (`redgreen.py`), eval pre-registration, judge guidance |
| Review | `review-by-intent` | reviewers | Verdict per criterion, an AI failure checklist, review notes |
| Review | `decision-trace` | ICs | A reconstructible reasoning record as a PR by-product |
| Ship | `ship-and-observe` | ICs, on-call | Rollout plans, attributable changes, runbooks for unplanned loops |
| Measure | `ai-readiness-and-metrics` | leaders | A 0-3 readiness rubric and metrics beyond velocity, at team level |

## How a change flows

1. `lane.py` classifies the diff. The highest-risk path decides the lane. Lanes only go up.
2. Lite: a short intent, tests, a trace. Standard: a spec file, one human approval before build, review notes. Critical: intent statement, spec, threat note, rollout plan, a second human reviewer.
3. The PR description carries the evidence under fixed headings (`## Intent`, `## Trace`, `## Review notes`, `## Threat note`, `## Rollout plan`). The templates in each skill's `assets/` use those headings.
4. After merge, `ship-and-observe` covers rollout and the loops that follow incidents, findings and failing builds. Every loop ends in a new intent and a regression case.

## What is enforced, and what is advice

| Layer | Strength |
|---|---|
| The skills | Advice. They shape what an agent or person does but nothing stops a skip |
| `hooks/pre-push` | A reminder. Never blocks, and `--no-verify` skips it |
| The CI gate (`evidence_check.py`) | Blocks only once the check named `evidence` is required in branch protection. Checks that evidence exists and is structurally real, never that it is good |
| `doctor.py --check-branch-protection` | The only thing that can show the gate actually blocks merges |

The gate reads its scripts and lane config from the base branch, so a PR cannot weaken the gate judging it. Protect the gate files with CODEOWNERS and required code-owner review.

## Suggested adoption order for a team at "experimental"

1. **Install and verify the gate** (`ai-sdlc`, `references/init.md`). Prove the required check with doctor.
2. **Specs and proof:** `spec-first` for Lite and Standard changes, and `verify-and-evals` red-to-green evidence in the PR trace.
3. **Review and trace:** `review-by-intent` and `decision-trace`. These are where reasoning is kept or lost.
4. **Context and shipping:** `context-pack` when history matters, `ship-and-observe` for Critical changes.
5. **Agents with boundaries:** `autonomy-policy` once agents act on their own. Start at Tier 1.
6. **Measure:** baseline for four weeks with `ai-readiness-and-metrics` before setting any target.
7. **`learning-mode`** is available from day one for anyone who wants it. It is opt-in and never an assessment.

## Honest status

Tested with unit and integration tests and a hand-picked mutation check (see `PATCH-NOTES.md`). Not yet calibrated on real teams: lane caps, freshness windows and size limits are starting points. Not verified: Windows, macOS, Python 3.8, shellcheck, fork PRs. Survey figures cited in the skills are self-reported perception from one study, not measured outcomes.
