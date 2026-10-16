# GitHub Copilot Instructions for AI-native SDLC

When working on this repository, follow the risk-proportional SDLC guidelines:

1. **Check Lane:** Run `python3 scripts/lane.py --paths <files>` before planning edits.
2. **Intent Before Code:** Write clear acceptance criteria (`AC1: ... | pass: ...`) before generating implementation logic.
3. **Trace Decisions:** Always explain *why* an approach was chosen and document any rejected alternatives for the PR trace.
4. **Never Weaken Tests:** When fixing a bug, prove the test fails first, then implement the fix (`skills/verify-and-evals/scripts/redgreen.py`).
5. **Security & Secrets:** Never commit tokens, credentials, or personal data. Keep all secrets scrubbed.
