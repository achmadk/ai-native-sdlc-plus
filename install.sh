#!/bin/sh
# One-command install. Copies config, templates, CI workflow, hook. Idempotent.
set -u
ROOT="${1:-.}"
mkdir -p "$ROOT/scripts" "$ROOT/.github/workflows" "$ROOT/hooks"
cp scripts/lane-config.yaml "$ROOT/scripts/" 2>/dev/null || true
cp scripts/lane.py scripts/evidence_check.py scripts/doctor.py "$ROOT/scripts/" 2>/dev/null || true
cp .github/workflows/sdlc-gate.yml "$ROOT/.github/workflows/" 2>/dev/null || true
cp .github/pull_request_template.md "$ROOT/.github/" 2>/dev/null || true
cp hooks/pre-push hooks/pre-push.sh hooks/pre-push.ps1 "$ROOT/hooks/" 2>/dev/null || true
chmod +x "$ROOT/hooks/pre-push" "$ROOT/hooks/pre-push.sh" 2>/dev/null || true
python3 "$ROOT/scripts/doctor.py" --root "$ROOT"
