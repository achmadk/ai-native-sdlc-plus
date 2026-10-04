# Action catalog

Starting points, not rules. For each action your team uses, decide the minimum tier, whether it may run unattended, and which control enforces it. "Norm" means nothing stops a violation. Say so in the policy.

| Action | Suggested minimum tier | Unattended? | What typically enforces it |
|---|---|---|---|
| Read the repo, docs, tickets (with the requesting user's access) | 0 | Yes | Token and file-access scopes |
| Run tests and linters in a sandbox | 1 | Yes | Sandbox, no production credentials |
| Edit files in a working copy | 1 | Yes | Local only; reviewed before it leaves |
| Push to a feature branch | 2 | Lite and Standard | Branch permissions |
| Open or update a pull request | 2 | Lite and Standard | PR template and the sdlc-gate check |
| Comment on a PR or ticket | 2 | Yes | Norm (comments cannot be un-sent) |
| Merge to the default branch | 3 | Named Lite flows, gate green | Branch protection: required check, restricted merge rights |
| Edit CI workflows, gate scripts, lane config, CODEOWNERS, hooks | Human only | Never | CODEOWNERS plus required code-owner review |
| Add or upgrade a dependency | 2 | Patch bumps may be a Tier 3 flow | Lockfile review, dependency scanner |
| Run a migration or change a schema | Human only | Never | Critical lane, two-person review |
| Change auth, permissions, secrets, IAM | Human only | Never | Critical lane, secrets manager access |
| Deploy to production | 3 | Only named routine flows with tested rollback | Deploy permissions, staged rollout |
| Delete data, branches, releases, infrastructure | Human only | Never | Permissions, backups |
| Provision cloud resources or spend money | Human only | Only within a hard quota | Cloud quotas and budgets |
| Send external messages (customers, public, partners) | Human only | Never | Norm unless the channel is permissioned |
| Call a new external service with company or user data | Human only | Never | Network egress rules, data policy |
| Install or run a third-party tool, MCP server, or skill | Human only | Never | Allow-list, supply-chain review |
| Read production data or personal data | Human only | Never | Data access controls, masking |
| Disable a check, skip a hook (`--no-verify`), force-push, rewrite shared history | Never | Never | Branch protection (force-push blocked), review of bypass events |

Notes:
- "Human only" means a person performs the action or explicitly approves each instance. The agent may draft it.
- Anything not in the table is Tier 1 until someone decides otherwise. Unlisted does not mean permitted.
- Prefer a control that fails closed (a permission the agent lacks) over a norm the agent is asked to follow.
