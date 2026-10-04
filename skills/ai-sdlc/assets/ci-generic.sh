#!/bin/sh
# sdlc-gate for any CI system (GitLab, Jenkins, Buildkite, CircleCI, ...).
# Runs the evidence gate with its scripts and lane config taken from the BASE commit, so a change
# cannot weaken the gate that judges it. The GitHub workflow does the same with two checkouts.
#
# Inputs, as environment variables:
#   SDLC_BASE           commit SHA the change will merge into              (required)
#   SDLC_HEAD           commit SHA of the change under review              (required)
#   SDLC_PR_BODY_FILE   path to a file holding the PR/MR description text  (required)
# Run it from a checkout of the change with FULL history: the diff needs the merge base.
# Some CI systems truncate a long description held in a variable; fetch it through the API if yours does.
# The base commit must already contain scripts/ (bootstrap: commit the tooling to the default branch first).
#
# Exit codes: 0 evidence ok | 1 evidence missing | 2 setup error | 3 tooling error
set -u

die() { printf 'sdlc-gate: %s\n' "$2" >&2; exit "$1"; }

: "${SDLC_BASE:=}" "${SDLC_HEAD:=}" "${SDLC_PR_BODY_FILE:=}"
[ -n "$SDLC_BASE" ] && [ -n "$SDLC_HEAD" ] && [ -n "$SDLC_PR_BODY_FILE" ] ||
  die 2 "set SDLC_BASE, SDLC_HEAD and SDLC_PR_BODY_FILE"
for sha in "$SDLC_BASE" "$SDLC_HEAD"; do
  case "$sha" in *[!0-9a-f]*) die 2 "not a commit SHA: $sha" ;; esac
  [ "${#sha}" -ge 40 ] || die 2 "need a full commit SHA, got: $sha"
done
[ -f "$SDLC_PR_BODY_FILE" ] || die 2 "PR description file not found: $SDLC_PR_BODY_FILE"
command -v python3 >/dev/null 2>&1 || die 2 "python3 not found (need >= 3.8)"
git rev-parse -q --verify "$SDLC_BASE^{commit}" >/dev/null 2>&1 || die 2 "base commit not in this checkout (shallow clone? fetch full history)"

tmp=$(mktemp -d) || die 3 "cannot create a temp directory"
trap 'rm -rf "$tmp"' EXIT

git archive "$SDLC_BASE" scripts 2>/dev/null | tar -x -C "$tmp" 2>/dev/null
[ -f "$tmp/scripts/evidence_check.py" ] && [ -f "$tmp/scripts/lane.py" ] && [ -f "$tmp/scripts/lane-config.yaml" ] ||
  die 3 "the base commit has no usable scripts/ (commit the gate tooling to the default branch first)"

python3 "$tmp/scripts/evidence_check.py" --ci \
  --config "$tmp/scripts/lane-config.yaml" \
  --repo-root . \
  --base="$SDLC_BASE" --head="$SDLC_HEAD" \
  --pr-body-file "$SDLC_PR_BODY_FILE"
