# Adapters — use alongside incumbents, not instead of them

## spec-kit

Keep `.specify/` flow; add lane classification before `/speckit-plan` and evidence check after `/speckit-implement`. Map: spec-kit spec -> spec-first Standard; bug-fix extension -> ship-and-observe unplanned loop. Smoke test: classify three spec-kit artifact paths, expect lanes without touching `.specify/`.

## Superpowers

Keep existing commands; invoke ai-sdlc routing first, then the matching Superpowers workflow for build depth. Evidence gate runs unchanged at PR. Details unverified against current Superpowers internals — adapter is a thin shim, issues welcome.

## OpenSpec

This repo's own planning used OpenSpec changes. Map: OpenSpec proposal -> spec-first intent; specs -> acceptance criteria; `evidence_check.py --lane` reads artifact presence from the change directory. Smoke test: `openspec status` green plus evidence check on the change's tasks.

## Agent Adapters

Pre-configured instruction files for popular AI coding assistants:
- **Claude Code:** `.claude/CLAUDE.md`, `.claude/commands/`, `.claude/skills/`
- **Cursor:** `.cursorrules`, `.cursor/rules/sdlc.mdc`
- **GitHub Copilot:** `.github/copilot-instructions.md`
- **OpenAI Codex / OpenCode / Aider / Devin:** `AGENTS.md`
- **Google Gemini CLI / Antigravity:** `GEMINI.md`

## CI Adapters

Enterprise pipeline configurations:
- **GitLab CI:** `adapters/ci/gitlab-ci.yml`
- **Azure DevOps:** `adapters/ci/azure-pipelines.yml`
- **Bitbucket Pipelines:** `adapters/ci/bitbucket-pipelines.yml`
- Full documentation in [adapters/ci/README.md](file:///home/achmadkurnianto/PROJECTS/OPEN_SOURCES/ai-native-sdlc-plus/adapters/ci/README.md)
