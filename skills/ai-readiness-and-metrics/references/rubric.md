# Readiness rubric (0-3 per dimension)

Score from artifacts, not from opinions. Write the artifact next to the score. Anything you cannot see is "not scored".

## 1. Context availability: can an agent or a new engineer get organizational context without asking a human?
- 0: Standards, acceptance criteria, and past decisions live in heads and chat threads. Agents see only the code.
- 1: Some docs exist but are not linked from where work starts. Agents do not read them.
- 2: Acceptance criteria and standards are in the repo or linked from the ticket/PR. Context is supplied to agents by hand.
- 3: Context packs (or equivalent) have owners and staleness dates, load by default in agent sessions, and a spot check of three recent PRs shows they were current.
Spot check: for three recent PRs, could an agent have known the acceptance criteria, the relevant past incident, and the applicable security rule?

## 2. Trace durability: after six months, can someone reconstruct why a change was made?
- 0: No record of prompts or decisions. PR descriptions are one line.
- 1: PR descriptions sometimes explain why. Agent use is not recorded.
- 2: A PR template with a trace section is used in most sampled PRs and records tools used and options rejected.
- 3: Reconstruction test passed: for three PRs older than six months (or simulated), a person not involved explains the reasoning in 15 minutes from the record alone.
Context: only 15% of ICs (25% of leaders) report being very confident they can reconstruct AI-assisted reasoning after six months [report-stated].

## 3. Gate honesty: do the controls do what they claim, and are their limits stated?
- 0: No gate, or a gate that is routinely red, ignored, or bypassed.
- 1: Manual review of an unmodified PR process only.
- 2: Automated checks block merges (marked required), and the docs say what a green result does and does not mean.
- 3: Gate is tamper-resistant (config read from the base branch, code-owner review on gate files), has its own tests, publishes known limitations, and bypass events are reviewed.

## 4. Policy coverage: is it clear what agents may do unattended?
- 0: No policy. Individuals decide.
- 1: Informal norms.
- 2: Written trust tiers by risk, including what agents may do without a human and when to escalate.
- 3: Tiers are enforced by tooling (lanes, gates), reviewed on a cadence, and exceptions are logged.

## Reading the result
0-1 = foundation work first. 2 = working. 3 = durable. Do not add the four scores into one number. A single 0 in gate honesty outweighs three 3s elsewhere, because it makes the other scores unverifiable.
