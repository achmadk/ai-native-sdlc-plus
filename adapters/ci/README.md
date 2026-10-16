# Enterprise CI Adapters

Ready-to-use pipeline templates for teams not using GitHub Actions.

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
