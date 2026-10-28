#!/usr/bin/env python3
"""lane_backtest.py - replay lane.py over recent history to calibrate lane rules.

LIMITATIONS.md lists "Lane-config Critical defaults need first-repo
calibration". This script answers the practical question before you adopt the
gates: "if lane.py had been running, what lane would my last N changes have
landed in, and which rules would have fired?"

It does not import lane.py. It calls it exactly as a user would
(`python3 scripts/lane.py --paths <files>`) and parses the leading lane name
from the first matching output line (for example
`Lite: matched Lite rule docs/**`). Lines it cannot understand are counted as
"unclassified" so a mismatch is visible instead of silently skewing results.

By default each first-parent commit on the chosen revision is treated as one
change (a merge commit or a squash commit == one PR). Standard library only,
read-only, no network.

Usage:
  python3 scripts/lane_backtest.py --limit 50
  python3 scripts/lane_backtest.py --rev origin/main --limit 200 --json
  python3 scripts/lane_backtest.py --paths-style comma   # if lane.py wants a,b,c

Exit status: 0 = report printed, 2 = git or lane script problem.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

LANES = ("Lite", "Standard", "Critical")
LANE_RE = re.compile(r"^\s*(Lite|Standard|Critical)\b[:\s-]*(.*)$", re.I)


class BacktestError(RuntimeError):
    pass


def parse_lane(output: str) -> Tuple[Optional[str], str]:
    """Return (lane, reason) from lane.py output, or (None, "") if not understood."""
    for line in output.splitlines():
        m = LANE_RE.match(line)
        if m:
            return m.group(1).capitalize(), m.group(2).strip()
    return None, ""


def _git(root: str, *args: str) -> str:
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise BacktestError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout


def list_commits(root: str, rev: str, limit: int, first_parent: bool = True) -> List[str]:
    args = ["rev-list", f"--max-count={limit}"]
    if first_parent:
        args.append("--first-parent")
    args.append(rev)
    return [s for s in _git(root, *args).split() if s]


def changed_files(root: str, sha: str) -> List[str]:
    """Files changed by `sha` relative to its first parent (or the empty tree)."""
    has_parent = (
        subprocess.run(
            ["git", "-C", root, "rev-parse", "--verify", "--quiet", f"{sha}^1"],
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )
    if has_parent:
        out = _git(root, "diff", "--name-only", "-z", f"{sha}^1", sha)
    else:
        out = _git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", sha)
    return [p for p in out.split("\0") if p]


def build_command(lane_script: str, files: Sequence[str], style: str) -> List[str]:
    base = [sys.executable, lane_script]
    if style == "args":
        return base + ["--paths", *files]
    if style == "comma":
        return base + ["--paths", ",".join(files)]
    if style == "repeat":
        cmd = list(base)
        for f in files:
            cmd += ["--paths", f]
        return cmd
    raise BacktestError(f"unknown --paths-style {style!r}")


Runner = Callable[[str, Sequence[str], str, str], Tuple[int, str]]


def run_lane(lane_script: str, files: Sequence[str], style: str, root: str) -> Tuple[int, str]:
    p = subprocess.run(build_command(lane_script, files, style), capture_output=True, text=True, cwd=root)
    return p.returncode, (p.stdout + ("\n" + p.stderr if p.stderr else ""))


def backtest(
    root: str,
    rev: str,
    limit: int,
    lane_script: str,
    style: str = "args",
    max_files: int = 400,
    first_parent: bool = True,
    runner: Runner = run_lane,
) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    for sha in list_commits(root, rev, limit, first_parent):
        files = changed_files(root, sha)
        entry: Dict[str, object] = {"sha": sha[:12], "files": len(files), "lane": None, "reason": "", "status": ""}
        if not files:
            entry["status"] = "skipped: no files"
        elif len(files) > max_files:
            # Truncating could hide a Critical path, so skip instead of guessing.
            entry["status"] = f"skipped: more than {max_files} files"
        else:
            rc, output = runner(lane_script, files, style, root)
            lane, reason = parse_lane(output)
            if lane is None:
                first = next((ln.strip() for ln in output.splitlines() if ln.strip()), "")
                entry["status"] = f"unclassified (rc={rc}): {first[:100]}"
            else:
                entry["lane"], entry["reason"], entry["status"] = lane, reason, "ok"
        results.append(entry)
    return results


def summarize(results: Sequence[Dict[str, object]]) -> Dict[str, object]:
    lanes = collections.Counter(r["lane"] for r in results if r["lane"])
    unclassified = sum(1 for r in results if str(r["status"]).startswith("unclassified"))
    skipped = sum(1 for r in results if str(r["status"]).startswith("skipped"))
    considered = sum(lanes.values()) + unclassified
    reasons = collections.Counter(f"{r['lane']}: {r['reason']}" for r in results if r["lane"])
    return {
        "commits": len(results),
        "considered": considered,
        "lanes": {lane: lanes.get(lane, 0) for lane in LANES},
        "unclassified": unclassified,
        "skipped": skipped,
        "top_rules": reasons.most_common(5),
    }


def format_report(summary: Dict[str, object], rev: str) -> str:
    considered = int(summary["considered"]) or 1
    lanes: Dict[str, int] = summary["lanes"]  # type: ignore[assignment]
    lines = [f"lane_backtest: {summary['commits']} commit(s) on {rev} (first-parent)"]
    for lane in LANES:
        n = lanes[lane]
        lines.append(f"  {lane:<13}{n:>4}  {100.0 * n / considered:5.1f}%")
    lines.append(f"  {'unclassified':<13}{summary['unclassified']:>4}  (lane.py output not understood)")
    lines.append(f"  {'skipped':<13}{summary['skipped']:>4}  (no files, or too many files)")
    top = summary["top_rules"]
    if top:
        lines.append("Most frequent rules:")
        for text, n in top:  # type: ignore[misc]
            lines.append(f"  {n:>4}  {text}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Replay lane.py over recent history (see module docstring).")
    ap.add_argument("--root", default=".", help="repository root (default: .)")
    ap.add_argument("--rev", default="HEAD", help="revision to walk back from (default: HEAD)")
    ap.add_argument("--limit", type=int, default=50, help="number of commits to replay (default: 50)")
    ap.add_argument("--lane-script", default="scripts/lane.py", help="path to lane.py, relative to --root")
    ap.add_argument(
        "--paths-style",
        choices=("args", "comma", "repeat"),
        default="args",
        help="how files are passed: --paths a b | --paths a,b | --paths a --paths b",
    )
    ap.add_argument("--max-files", type=int, default=400, help="skip commits touching more files than this")
    ap.add_argument("--all-commits", action="store_true", help="walk all parents, not only first-parent history")
    ap.add_argument("--json", action="store_true", help="print per-commit results and summary as JSON")
    args = ap.parse_args(argv)

    lane_script = Path(args.lane_script)
    if not lane_script.is_absolute():
        lane_script = Path(args.root) / lane_script
    if not lane_script.is_file():
        print(f"lane_backtest: lane script not found: {lane_script}", file=sys.stderr)
        return 2
    if args.limit < 1:
        print("lane_backtest: --limit must be >= 1", file=sys.stderr)
        return 2

    try:
        results = backtest(
            args.root,
            args.rev,
            args.limit,
            str(lane_script),
            args.paths_style,
            args.max_files,
            first_parent=not args.all_commits,
        )
    except BacktestError as exc:
        print(f"lane_backtest: {exc}", file=sys.stderr)
        return 2

    summary = summarize(results)
    if args.json:
        print(json.dumps({"summary": summary, "commits": results}, indent=2))
    else:
        print(format_report(summary, args.rev))
    return 0


if __name__ == "__main__":
    sys.exit(main())
