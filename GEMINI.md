# Gemini & Antigravity Agent Guidelines

This repository implements risk-proportional AI SDLC enforcement.

## Instructions
1. Run `python3 scripts/lane.py --paths <files>` to classify proposed modifications.
2. For bugfixes or behavioral changes, use `skills/verify-and-evals/scripts/redgreen.py` to establish red-to-green proof.
3. Generate pull request descriptions matching the template in `.github/pull_request_template.md`.
4. Keep all Python scripts stdlib-only; never introduce unpinned dependencies.
