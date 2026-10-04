# Patch notes (cumulative; newest round first)

# Round 5: learning-mode (the last skill) and the suite overview

## What was wrong in the upload
- **No tie to the toolkit.** Nothing fed the gate's `### Explain-back` field, and `review-by-intent` said "use guided questions" without pointing here.
- **No consent or privacy rule.** A skill that quizzes people about their understanding can quietly become surveillance. It now says it is opt-in, is not a
  performance evaluation, and that answers are never reported or turned into metrics. A test pins those sentences so they cannot be edited away unnoticed.
- **"Never hand the final explanation before the learner attempts it" was rigid.** It stranded stuck learners. Replaced by a four-level hint ladder that always
  ends in the answer (followed by the learner re-explaining it), plus "just do it" as a standing opt-out.
- **No way to know what the AI got wrong.** Added predict-then-run verification, questions that teach learners to doubt invented names and assumptions, and the
  rule that the learner writes the note, not the assistant.
- **Everything was a quiz.** Added a diagnostic first, depth chosen by lane and risk, session limits, honesty about not remembering between chats, and a clear line
  between this skill and a human mentor.

## New and changed files
`skills/learning-mode/{SKILL.md, assets/understanding-note-template.md, references/question-bank.md, references/example-session.md}`,
`docs/OVERVIEW.md` (the map of all ten skills, enforcement layers, and an adoption order), a pointer from `review-by-intent` and `ai-sdlc`.
No validator for the understanding note, on purpose: a checker would turn a private learning aid into an assessment.

## Correction to an earlier file of mine
`ai-readiness-and-metrics/references/metrics.md` said time to 10th PR was "more than half the Q1 2024 figure". The report says it dropped by more than half
since Q1 2024. Fixed.

## Verification
374 tests plus 2 overview tests (ResourceWarning as error). No script changed this round, and I confirmed every mutated script is byte-identical to the version
verified last round, so the mutation result stands: 175 of 175 non-equivalent mutants killed, 3 equivalent survivors documented.

---

# Round 4: spec-first, ship-and-observe, review-by-intent, verify-and-evals, decision-trace, and the ai-sdlc references

## What I audited, and what was wrong
I ran the uploaded templates through the real gate before touching them.
1. **`trace-block.md`, completely blank, passed the gate** (117 "meaningful" characters). Two causes: boilerplate prose outside HTML comments, and
   **a flaw in my own `evidence_check.py`**: sub-heading titles (`### Why`) were counted as content of their parent section. Gate fixed (heading lines are
   structure, not content); the template now keeps all guidance inside comments.
2. **`### Threat / rollout` could never satisfy the gate**, which needs `## Threat note` and `## Rollout plan` as separate sections, so a Critical PR
   built from that template failed. They are now separate templates.
3. **Dangling references:** `spec-first` pointed at `references/examples.md` and at "Critical templates" that did not exist; `init.md` pointed at
   `assets/ci-generic.sh`. All now exist, and a test fails if any skill document mentions a file that is missing.
4. `doctor.md` described doctor v0.1; `init.md` omitted the hook-filename pitfall, CODEOWNERS and the required check. Rewritten.
5. The two uploaded `verify-and-evals/SKILL.md` files were identical. (Only the last upload of each filename survives on disk, so I worked from the text in
   the conversation. Uploading a zip, or distinct names, avoids this.)

## Per skill
- **spec-first:** where each lane keeps its spec (what the gate reads); out-of-scope, assumptions, approval record; amendment instead of silent edits; five
  templates (Lite/Standard, Critical intent, Critical spec, threat note) and worked examples. New `scripts/check_spec.py`: criteria in the form
  `AC1: behavior | pass: condition`, every criterion mapped to a test with a `fails-before` reason, vague-word tripwire, approval, size caps, secrets.
- **verify-and-evals:** the red-to-green rule now has a tool. New `scripts/redgreen.py` proves a test fails on the starting commit (with head's tests overlaid
  in a throwaway worktree) and passes on head; verdicts PASS / NOT_RED / NOT_GREEN / FLAKY / NO_TESTS; output scrubbed of secrets; never touches your working
  copy. Adds what does not count as a test, exemptions (refactor, docs, untestable), a pre-registration template, and judge bias and calibration guidance.
- **review-by-intent:** you recommend, a human decides; scope check before content; verdicts met / violated / uncovered / unverified; a concrete AI failure
  checklist (invented packages, fake or weakened tests, swallowed errors); explain-back protocol; independence; size heuristic; review-notes template aligned to
  the gate.
- **decision-trace:** gate-aligned trace template; provenance via commit trailers (checkable) instead of per-hunk claims; when to promote to a decision record;
  "rotate, do not just edit" for leaked secrets; a reconstruction-test protocol that backs the readiness rubric.
- **ship-and-observe:** rollout plan template (stages, signals and abort criteria, rollback, owner); attributable changes; agent visibility; loop runbooks for
  incident, security finding, test failure, flaky build and agent misbehavior; an incident-intent template; and an explicit "mitigate first" emergency path that
  says plainly the gate has no bypass and that admin merges must be logged.
- **ai-sdlc references and assets:** `doctor.md`, `init.md`, `onboarding.md` rewritten; new `assets/ci-generic.sh` for non-GitHub CI. It runs the gate with
  scripts AND config taken from the base commit.

## A finding worth knowing
The lane math is protected by the built-in Critical rule for the config file. The `tests:` and `non_executable:` sections are not lane math, so a PR that
widens them could declare any file "a test". The workflow and `ci-generic.sh` read the config from the base commit, and a test now proves a PR cannot do this.
The local hook reads the working-tree copy and is advisory only.

## Verification (Linux sandbox, Python 3.12)
368 tests (ResourceWarning as error). Mutation check: 175 of 175 non-equivalent hand-picked mutants killed across all scripts; 3 equivalent survivors are
documented in `tests/mutate.py`. New cross-cutting tests assert that every shipped template works with the real gate (blank never passes, filled passes, a PR built
from the templates passes per lane), that every file a skill mentions exists, that frontmatter is valid, and that the secret patterns are identical in every
script that carries a copy. I confirmed those tests fail on the original defective files.

## Not verified
`redgreen.py` runs the command you give it with your environment and network: use a sandbox for untrusted code. It cannot tell whether a failure is for the right
reason (it prints the RED output for you to read) or whether a test is any good. Submodules are not initialised in its worktrees. Windows, macOS, Python 3.8 and
shellcheck were not run. The `check_*` validators check shape, not truth. The `ci-generic.sh` examples for specific CI vendors are not tested on those vendors.
Lane caps, freshness windows and size caps remain uncalibrated starting points.

---

# Round 3: hook, autonomy-policy, context-pack

Cumulative: this zip contains everything from rounds 1 and 2 as well. Unzip over the repo.

## Replaces
`hooks/pre-push.sh`, `skills/autonomy-policy/{SKILL.md,assets/policy-template.md}`, `skills/context-pack/{SKILL.md,assets/brief-template.md}`,
plus the earlier files (`scripts/*.py`, `.github/workflows/sdlc-gate.yml`, `install.sh`, `skills/ai-sdlc`, `skills/ai-readiness-and-metrics`).
## New
`hooks/pre-push` (dispatcher), `skills/autonomy-policy/references/action-catalog.md`, `skills/context-pack/scripts/check_brief.py`,
`tests/test_hook.py`, `tests/test_check_brief.py`.
Not seen: `skills/ai-sdlc/references/*.md`, and any other skills you have (`spec-first`, `review-by-intent`, ...). Bring them next.

## Correction: my earlier advice was wrong, and so was doctor
Git only runs a hook named exactly `pre-push` (no extension). `hooks/pre-push.sh` is therefore **never run** under
`git config core.hooksPath hooks`, which is what my installer message and my doctor recommended. Doctor even reported `hook-active: verified`
for that setup. Fixed three ways:
1. `hooks/pre-push` (new) is a small dispatcher that calls `pre-push.sh`, so `core.hooksPath hooks` now works.
   `cp hooks/pre-push.sh .git/hooks/pre-push` still works standalone.
2. doctor asks git where it will look (`git rev-parse --git-path hooks/pre-push`), then requires an executable file there that carries the
   `sdlc-pre-push` marker. A foreign hook is reported as "not the sdlc hook". A regression test encodes the exact mistake.
3. The installer copies both files and sets the executable bit (unzipping can drop it).

## hooks/pre-push.sh: what was wrong with the uploaded version
- Never ran under `core.hooksPath` (above).
- It called `evidence_check.py --lane Standard` with no evidence and no diff, so every push printed the same generic "missing evidence"
  warning regardless of the change: noise that teaches people to ignore it. It never looked at what was being pushed.
- `|| echo` never fired (the script exits 0 on warnings) and `2>/dev/null` hid real errors.
- It could not tell a docs typo from an auth change, or warn about a direct push to the default branch.

## hooks/pre-push.sh: what it does now
Reads git's ref list from stdin; for each pushed branch classifies the **whole branch against the default branch** (the diff the PR gate will
see), prints the lane, lists what the PR description must carry, and warns when the diff has no test changes. Warns on direct pushes to the default
branch. Skips deletions and tags. Silence with `SDLC_HOOK=off` or `git config sdlc.hook off`.
It can never block: every path exits 0; missing python/scripts/merge-base are reported in one line. Children run with `</dev/null` so nothing eats
the ref list; branch names are only ever printed as data. Needs `evidence_check.py --diff-only` (new): checks only what the diff proves and says
so, and is rejected with `--ci`.

## autonomy-policy
Original gaps: tiers were not tied to lanes; "production", "scoped writes" undefined; no action list; no way to tell a rule from a norm; escalation
had no content or default; no demotion; rollout entry evidence was "naming" only.
Now: lane caps the tier (Lite 3 for named flows else 2, Standard 2, Critical 1: defaults, change with a written reason); an action catalog with
"enforced by" per row; escalation with a fail-closed default and a ban on routing around a denial; demotion triggers; rollout tied to the readiness rubric
and to `doctor --check-branch-protection`; gate files are always human-owned. Template is fill-in with suggested defaults marked as suggestions.

## context-pack
Original gaps: sources (tickets, wikis, chat) are untrusted text fed to an agent, with no mention of prompt injection or secret leakage; "freshness window"
undefined; "never reproduce" contradicted the template's "quoted minimum"; no size cap; no conflict handling; no way to record "searched, found nothing".
Now: sources-are-data rule; default windows with git-based staleness (`until-paths-change` + `governs:`); acceptance criteria are the one verbatim exception
(max 600 chars, with source and date); size caps by lane; Conflicts and Gaps sections; and `scripts/check_brief.py`, which validates format, dates, freshness,
repo links, required sections, caps, secrets (never echoed), hidden Unicode, and injection phrasings (a tripwire, not a defence).

## Suggested LIMITATIONS.md additions
- The pre-push hook is advisory and skippable (`--no-verify`). It cannot see the PR description, so it verifies only the test-change evidence.
- The hook's lane is computed from the local working-tree copy of the gate scripts; CI uses the base-branch copy.
- `check_brief.py` checks structure, not truth. Its injection check matches common phrasings only and is not a defence. Its secret patterns cover common token
  formats and credential assignments, not personal data. `http(s)` links are not verified (no network). Staleness by `governs:` needs a git work tree.
- Lane caps and default freshness windows are starting points that nobody has calibrated on real teams.
- Not verified: Windows (the hook is POSIX sh), fork PRs, Python 3.8 (tests ran on 3.12 only), `shellcheck` (not available here; `ci.yml` runs it).

## Verification (all on Python 3.12 in a Linux sandbox)
- 255 unit/integration tests, run with ResourceWarning treated as an error.
- Mutation check: 112 of 112 non-equivalent hand-picked mutants killed across lane.py, evidence_check.py, doctor.py, the hook, the dispatcher and
  check_brief.py. Two equivalent survivors are documented in `tests/mutate.py` (a defence-in-depth path check; `trap 'exit 0'`, which is redundant with the
  explicit `exit 0` on every path). The first full run had 3 survivors; each was a real test gap and is now closed. One was clock-dependent: git reads a bare
  `--since=DATE` as DATE at the *current time of day*, so that test now uses a 23:59 commit.
- Real `git push` runs through `core.hooksPath` (dispatcher), through `.git/hooks/pre-push` (standalone), and with only the `.sh` file (documented as inert).
- Hook run under every POSIX shell present (dash, bash, sh).
- Not run: shellcheck (not installed here), Windows, macOS, Python 3.8.
