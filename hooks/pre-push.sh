#!/bin/sh
# Local pre-push hook: advisory only, fail-open. Warns, never blocks.
# Install: cp hooks/pre-push.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
set -u
if command -v python3 >/dev/null 2>&1; then
  if [ -f scripts/evidence_check.py ]; then
    python3 scripts/evidence_check.py --lane Standard 2>/dev/null || echo "sdlc hook: evidence warning (non-blocking)"
  fi
fi
exit 0
