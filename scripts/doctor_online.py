#!/usr/bin/env python3
"""doctor_online.py - opt-in check that the gate is a *required* check on GitHub.

scripts/doctor.py deliberately has no network access, so it cannot tell whether
the CI gate is actually marked required (LIMITATIONS.md: "Doctor cannot verify
required-check status"). This companion script closes that gap for people who
choose to run it. It shells out to the GitHub CLI (`gh`), which must be
installed and authenticated with read access to branch protection / rulesets.

It looks in two places:
  1. classic branch protection  (required_status_checks)
  2. repository rulesets        (rules that apply to the branch)

and, for classic protection, whether admins are subject to the rules
(enforce_admins), since an admin bypass is the documented weak point.

Usage:
  python3 scripts/doctor_online.py --check gate
  python3 scripts/doctor_online.py --check gate --repo owner/name --branch main

`--check` is the status-check context name exactly as GitHub shows it in
Settings -> Branches / Rules (usually the job name, not the workflow name).

Exit status: 0 = check is required, 1 = not required, 2 = could not verify
(gh missing, not authenticated, API error).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Callable, List, Optional, Sequence, Set, Tuple

Runner = Callable[[Sequence[str]], Tuple[int, str, str]]


class GhError(RuntimeError):
    pass


def make_runner(gh: str = "gh") -> Runner:
    def run(args: Sequence[str]) -> Tuple[int, str, str]:
        try:
            p = subprocess.run([gh, *args], capture_output=True, text=True)
        except FileNotFoundError:
            raise GhError(f"GitHub CLI not found: {gh!r} (install from https://cli.github.com)")
        return p.returncode, p.stdout, p.stderr

    return run


def _api_json(run: Runner, path: str):
    rc, out, err = run(["api", path])
    if rc != 0:
        if "404" in err or "Not Found" in err:
            return None
        raise GhError(f"gh api {path} failed: {err.strip() or out.strip()}")
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise GhError(f"gh api {path} returned invalid JSON: {exc}")


def resolve_repo(run: Runner, repo: Optional[str]) -> str:
    if repo:
        return repo
    rc, out, err = run(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    if rc != 0 or not out.strip():
        raise GhError(f"could not determine repository (use --repo owner/name): {err.strip()}")
    return out.strip()


def resolve_branch(run: Runner, repo: str, branch: Optional[str]) -> str:
    if branch:
        return branch
    rc, out, err = run(["repo", "view", repo, "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"])
    if rc != 0 or not out.strip():
        raise GhError(f"could not determine default branch (use --branch): {err.strip()}")
    return out.strip()


def classic_contexts(run: Runner, repo: str, branch: str) -> Optional[Set[str]]:
    """Required contexts from branch protection, or None if the branch is not protected."""
    data = _api_json(run, f"repos/{repo}/branches/{branch}/protection/required_status_checks")
    if data is None:
        return None
    names = set(data.get("contexts") or [])
    for item in data.get("checks") or []:
        if isinstance(item, dict) and item.get("context"):
            names.add(item["context"])
    return names


def ruleset_contexts(run: Runner, repo: str, branch: str) -> Set[str]:
    """Required contexts from rulesets that apply to the branch."""
    data = _api_json(run, f"repos/{repo}/rules/branches/{branch}") or []
    names: Set[str] = set()
    for rule in data:
        if isinstance(rule, dict) and rule.get("type") == "required_status_checks":
            params = rule.get("parameters") or {}
            for item in params.get("required_status_checks") or []:
                if isinstance(item, dict) and item.get("context"):
                    names.add(item["context"])
    return names


def admins_enforced(run: Runner, repo: str, branch: str) -> Optional[bool]:
    data = _api_json(run, f"repos/{repo}/branches/{branch}/protection/enforce_admins")
    if data is None:
        return None
    return bool(data.get("enabled"))


def verify(run: Runner, repo: str, branch: str, check: str) -> Tuple[int, List[str]]:
    lines: List[str] = []
    classic = classic_contexts(run, repo, branch)
    rules = ruleset_contexts(run, repo, branch)

    sources = []
    if classic is not None and check in classic:
        sources.append("branch protection")
    if check in rules:
        sources.append("ruleset")

    if sources:
        lines.append(f"OK: check {check!r} is required on {repo}@{branch} via {' and '.join(sources)}")
        code = 0
    else:
        known = sorted((classic or set()) | rules)
        listing = ", ".join(repr(n) for n in known) if known else "none"
        lines.append(f"FAIL: check {check!r} is NOT required on {repo}@{branch} (required checks found: {listing})")
        if classic is None and not rules:
            lines.append("      no branch protection or ruleset applies to this branch")
        code = 1

    if classic is not None:
        enforced = admins_enforced(run, repo, branch)
        if enforced is False:
            lines.append("WARNING: enforce_admins is off, so repository admins can bypass the required check")
    if rules and classic is None:
        lines.append("NOTE: ruleset bypass actors are configured separately; review them in Settings -> Rules")
    return code, lines


def main(argv: Optional[Sequence[str]] = None, runner: Optional[Runner] = None) -> int:
    ap = argparse.ArgumentParser(description="Verify the gate is a required check (see module docstring).")
    ap.add_argument("--check", required=True, help="status check context name, as shown by GitHub")
    ap.add_argument("--repo", help="owner/name (default: from the current directory via gh)")
    ap.add_argument("--branch", help="branch to inspect (default: the repository default branch)")
    ap.add_argument("--gh", default="gh", help="path to the gh executable")
    args = ap.parse_args(argv)

    run = runner or make_runner(args.gh)
    try:
        repo = resolve_repo(run, args.repo)
        branch = resolve_branch(run, repo, args.branch)
        code, lines = verify(run, repo, branch, args.check)
    except GhError as exc:
        print(f"doctor_online: {exc}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
