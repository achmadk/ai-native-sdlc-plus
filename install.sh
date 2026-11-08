#!/bin/sh
# Source-relative launcher; the shared installer owns all filesystem changes.
set -u
ROOT="${1:-.}"
if [ "$#" -gt 1 ]; then printf '%s\n' 'usage: sh install.sh [root]' >&2; exit 2; fi
SOURCE=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P) || exit 1
for python in python3 python; do
  if command -v "$python" >/dev/null 2>&1 &&
     "$python" -I -B -c 'import sys; sys.exit(sys.version_info < (3, 8))' </dev/null >/dev/null 2>&1; then
    exec "$python" -I -B "$SOURCE/scripts/install.py" "$ROOT"
  fi
done
printf '%s\n' 'installation failed: Python >= 3.8 required (tried python3 and python); no files changed' >&2
exit 1
