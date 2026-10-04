#!/bin/sh
# sdlc-pre-push
# Advisory pre-push hook. It can inform and it never blocks: every path ends in exit 0.
# The CI gate is the control; this is the early warning. `git push --no-verify` skips it.
#
# Enable (recommended):  git config core.hooksPath hooks     (git runs hooks/pre-push, which calls this file)
# Or standalone:         cp hooks/pre-push.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
# Silence:               SDLC_HOOK=off git push      or      git config sdlc.hook off
#
# Per pushed branch it classifies the WHOLE branch against the default branch (the diff the PR gate
# will see), prints the lane, lists what the PR description must carry, and warns when the diff
# has no test changes. It cannot check the PR description: no PR exists yet at push time.

trap 'exit 0' EXIT   # whatever goes wrong below, never block the push

say() { printf 'sdlc: %s\n' "$1" >&2; }
zeros() { case "$1" in *[!0]*) return 1 ;; *) return 0 ;; esac; }
run_gate() { if command -v timeout >/dev/null 2>&1; then timeout 20 python3 "$@"; else python3 "$@"; fi; }

[ "${SDLC_HOOK:-}" = "off" ] && exit 0
command -v git >/dev/null 2>&1 || exit 0
[ "$(git config --get sdlc.hook 2>/dev/null)" = "off" ] && exit 0
if [ -t 0 ]; then say "run this through 'git push'; it reads the ref list from stdin"; exit 0; fi

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
if ! command -v python3 >/dev/null 2>&1; then say "python3 not found; lane check skipped"; exit 0; fi
tool="$root/scripts/evidence_check.py"
cfg="$root/scripts/lane-config.yaml"
if [ ! -f "$tool" ] || [ ! -f "$cfg" ]; then say "gate scripts not found under scripts/; lane check skipped"; exit 0; fi

default_ref=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null)
if [ -z "$default_ref" ]; then
  for candidate in origin/main origin/master; do
    if git rev-parse -q --verify "$candidate" >/dev/null 2>&1; then default_ref=$candidate; break; fi
  done
fi
default_branch=${default_ref#origin/}

# Children get </dev/null: anything that reads stdin inside this loop would eat the remaining refs.
while read -r local_ref local_sha remote_ref remote_sha; do
  case "$local_ref" in refs/heads/*) ;; *) continue ;; esac   # branches only; skip tags and the rest
  zeros "$local_sha" && continue                                # branch deletion
  branch=${remote_ref#refs/heads/}
  if [ -n "$default_branch" ] && [ "$branch" = "$default_branch" ]; then
    say "pushing straight to $branch: the PR gate does not run on direct pushes"
    continue
  fi
  base=""
  [ -n "$default_ref" ] && base=$(git merge-base "$default_ref" "$local_sha" 2>/dev/null </dev/null)
  if [ -z "$base" ]; then
    say "no merge-base with the default branch for $branch (run 'git fetch', or 'git remote set-head origin -a'); lane check skipped"
    continue
  fi
  out=$(run_gate "$tool" --diff-only --base="$base" --head="$local_sha" --repo-root "$root" --config "$cfg" </dev/null 2>&1)
  printf '%s\n' "$out" | sed 's/^/sdlc: /' >&2
done

exit 0
