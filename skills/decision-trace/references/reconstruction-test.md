# Reconstruction test

Does the trace let someone who was not there explain the change months later? This is the check behind the "trace durability" level in the readiness rubric.

## Setup
- Sample 3 merged PRs that are at least six months old. If the repo is younger, simulate: set aside PRs, wait two weeks, and use a reader who did not work on them.
- The reader was not involved and gets only the PR description and linked records. No session history, no author.
- Time-box: 15 minutes per PR.

## Four questions (score each 1 or 0)
1. What changed?
2. Why was it changed? (the intent, not a restatement of the diff)
3. What alternatives were rejected, and why?
4. What risk was accepted, and by whom?

Score an answer 1 only if the reader can point to the words in the trace that support it. An answer that is plausible but inferred from the diff scores 0 and is marked "inferred".

## Result
- Pass: at least 3 of 4 on every sampled PR.
- Record: PR numbers, scores, the reader, the date, and which question failed most often. A repeated failure on question 3 usually means "Alternatives rejected" is being skipped.

## Using a fresh agent as the reader
Give it only the trace and the diff. Compare its answers with the author's ground truth. Treat any answer it could have produced from the diff alone as "inferred". A fluent but unsupported explanation is the failure mode this test exists to catch.

## Limits
Six months of real elapsed time cannot be simulated. A simulated pass is weaker evidence than a real one.
