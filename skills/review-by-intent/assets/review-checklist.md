# AI failure checklist

Run it against the diff after you have checked the change against its intent. Each item says how to check it, so the answer is evidence rather than a feeling.

## 1. Intent and scope
- Files changed that the intent does not explain. Compare the changed paths with the spec's scope.
- Criteria with no test, or tests with no criterion.
- Edits to gate files (`scripts/`, `.github/workflows/`, CODEOWNERS, `hooks/`) mixed into a feature change.
- A large refactor hiding inside a small fix.

## 2. Invented things
- Functions, flags, config keys, or API fields that do not exist. Build, type-check, or grep the definition. Do not trust a plausible name.
- New dependencies. Does the package exist, is the name exactly the intended one (look for typosquats), is it maintained, is the license acceptable, is the version pinned? Read the lockfile diff.

## 3. Tests
- Assertions that cannot fail, or that assert only that code ran.
- Mocks of the thing under test.
- Weakened or removed assertions; new `skip` or `xfail`; deleted failing tests.
- Existing tests edited to fit new behavior without a spec change.
- Snapshots regenerated blindly.
- Nondeterminism: time, randomness, ordering, network.
- Missing red-to-green evidence. Ask for `redgreen.py` output.

## 4. Errors and edge cases
- Swallowed or overly broad exception handling.
- Retries without backoff, or on non-idempotent calls.
- Empty, null, very large, and malformed input; time zones; concurrency; resource leaks.

## 5. Security
- Input validation on every new entry point; authentication and authorization on every new path.
- Injection (SQL, shell, template, path); unsafe deserialization.
- Secrets hardcoded or logged; personal data in logs.
- Permissions broadened; crypto written by hand.

## 6. Data and migrations
- Reversible? Locking behavior? Destructive steps?
- Compatibility while old and new code both run (expand, then contract).

## 7. Operability
- Logs, metrics, and alerts for the new behavior.
- New behavior behind a flag, off by default, where the lane calls for it.
- Config or environment changes; rollout and rollback described.

## 8. Maintainability
- Reimplements an existing utility.
- Dead code; placeholder stubs ("implement later"); comments that no longer match the code.

## 9. Hygiene
- Generated or binary files committed; copied code with license implications; secrets in history.

## Finding format
`severity | file:line | what is wrong | evidence`. Severities: blocker, major, minor, nit.
