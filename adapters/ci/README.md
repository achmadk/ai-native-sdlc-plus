# Enterprise CI Adapters

Pipeline templates for teams not using GitHub Actions. The foundation installer includes these files and their generic runner; selecting and activating a provider pipeline remains an explicit operator action, not proof of hosted compatibility.

## Supported Platforms

| Platform | Pipeline Template | Merge Base Detection | PR/MR Body Extraction |
|---|---|---|---|
| **GitLab CI** | `adapters/ci/gitlab-ci.yml` | `$CI_MERGE_REQUEST_DIFF_BASE_SHA` | `$CI_MERGE_REQUEST_DESCRIPTION` |
| **Azure DevOps** | `adapters/ci/azure-pipelines.yml` | `$(System.PullRequest.TargetBranchCommitId)` | `$(System.PullRequest.PullRequestBody)` |
| **Bitbucket** | `adapters/ci/bitbucket-pipelines.yml` | `$BITBUCKET_PR_DESTINATION_COMMIT` | `$BITBUCKET_PR_DESCRIPTION` |
| **Other** | `skills/ai-sdlc/assets/ci-generic.sh` | Manual `$SDLC_BASE` export | File via `$SDLC_PR_BODY_FILE` |

## Enforcement Essentials (Across All Platforms)

1. **Bootstrap First:** Commit `scripts/` and `skills/` to your default branch before opening your first PR. The gate script checks out tooling from the base commit to prevent PR authors from weakening the gate.
2. **Require the Check:** Mark the gate job as a required status check in your branch policy / merge request approval rules.
3. **Full Clone Depth:** Ensure your pipeline runner is configured with full depth (`GIT_DEPTH: 0`, `fetchDepth: 0`, `clone: { depth: full }`) so `git merge-base` can resolve the starting diff.

4. **Use complete change facts:** the generic runner invokes base-revision tooling with isolated Python and explicit base/head SHAs. Do not replace this with a manually supplied filename list or execute candidate checker code.
5. **Preserve failure and freshness:** missing evidence, malformed Git metadata, or tooling/setup errors must fail the job. Retrieve a complete current description, and rerun on description edits using the new event rather than an old snapshot.
6. **Verify the real provider:** local runner and template tests do not prove authentication, branch policy, description extraction, or event behavior on GitLab, Azure, or Bitbucket. Record actual run identifiers and unsupported cases. GitHub doctor's strict profile does not attest other providers.
