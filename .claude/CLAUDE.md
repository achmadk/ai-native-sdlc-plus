# Claude Code Guidelines for AI-native SDLC

## Commands
- **Classify Lane:** `python3 scripts/lane.py --paths <files>`
- **Run Doctor:** `python3 scripts/doctor.py --root .`
- **Unit Tests:** `python3 -m unittest discover -s tests -v`
- **Mutation Check:** `python3 tests/mutate.py`
- **ShellCheck:** `shellcheck install.sh hooks/pre-push hooks/pre-push.sh`

## Workflow
- Check the lane before editing code.
- Write intent or spec criteria before drafting logic.
- Supply complete `## Intent`, `## Trace`, and `## Review notes` in PR bodies.
