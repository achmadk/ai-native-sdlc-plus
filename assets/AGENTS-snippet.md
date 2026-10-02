# AGENTS.md snippet (for agents without native skills)

Add to your repo's AGENTS.md:

```md
## AI SDLC lanes
- Classify every change with `python3 scripts/lane.py --paths <files>`.
- Lite: short intent+plan in PR, tests + trace required, no pre-approval.
- Standard: combined spec, one human approval before build, evals required.
- Critical: split intent + spec, threat note, two-person review, staged rollout + rollback.
- Check evidence with `python3 scripts/evidence_check.py --lane <Lane>`; CI uses `--ci` to fail closed.
```
