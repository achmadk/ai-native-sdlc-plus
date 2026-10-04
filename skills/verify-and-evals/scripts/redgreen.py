"""Prove red-to-green: the new tests must FAIL before the change and PASS after it.

Method. Find the commit the change started from (merge-base of --base and --head). Check it out in a
throwaway git worktree, overlay the test files that --head added or changed, and run --cmd there. It
must fail (RED): a test that never failed proves nothing. Then run --cmd on --head in a second
throwaway worktree. It must pass (GREEN). Your working copy is never touched.

What this does NOT prove: that the test fails for the RIGHT reason (read the RED output it prints),
or that the test is any good. It also cannot run a test that needs files outside git (installed
dependencies, build output, secrets): use --setup to prepare each worktree.

SECURITY: --cmd and --setup run as given, with your environment and network. Run this only on code you
would run anyway, or inside a sandbox. Never on untrusted fork code in a privileged CI job.

Verdicts: PASS | NOT_RED (passes before the change: proves nothing) | NOT_GREEN (fails after) |
          FLAKY (results differ between repeats) | NO_TESTS (no test file changed) | ERROR (could not run).
Exit codes: 0 PASS | 1 NOT_RED, NOT_GREEN, FLAKY, NO_TESTS | 2 usage | 3 ERROR. Stdlib only. Python >= 3.8.
"""

import argparse
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

DEFAULT_TEST_GLOBS = ("test", "tests", "__tests__", "*_test.*", "test_*.*", "*.test.*", "*.spec.*", "evals")
TAIL_LINES = 15
MAX_LINE = 200
MAX_REPEAT = 10
_REF_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@^~{}:-]*$")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

# Keep in sync with context-pack/scripts/check_brief.py (a test asserts the lists match).
SECRETS = (
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("URL with embedded credentials", re.compile(r"://[^/\s:@]+:[^/\s@]+@")),
    ("credential assignment", re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*[\"']?[^\s\"']{8,}")),
)


class ToolError(Exception):
    """The proof could not be attempted or completed (distinct from a failed verdict)."""


def clean_env():
    """Drop git's own variables: inside a hook GIT_DIR would point the worktrees at the wrong repo."""
    return {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX")}


def git(root, *args):
    try:
        proc = subprocess.run(["git", "--literal-pathspecs", "-C", root] + list(args), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=clean_env(), timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ToolError("cannot run git: %s" % exc)
    return proc.returncode, proc.stdout, proc.stderr.decode("utf-8", "replace").strip()


def resolve(root, ref):
    if not _REF_OK.match(ref or ""):
        raise ToolError("refusing unsafe ref: %r" % ref)
    code, out, err = git(root, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
    if code != 0:
        raise ToolError("cannot resolve %r to a commit (shallow clone? fetch more history)" % ref)
    return out.decode().strip()


def is_test_path(path, globs):
    parts = path.split("/")
    return any(fnmatch.fnmatchcase(part, glob) for glob in globs for part in parts) or \
        any(fnmatch.fnmatchcase(path, glob) for glob in globs)


def changed_test_files(root, start, head, globs):
    """Test files added, modified or type-changed between start and head."""
    code, out, err = git(root, "diff", "--name-only", "--no-renames", "--diff-filter=AMT", "-z", "%s..%s" % (start, head), "--")
    if code != 0:
        raise ToolError("git diff failed: %s" % err[-120:])
    paths = [p.decode("utf-8", "replace") for p in out.split(b"\0") if p]
    return [p for p in paths if is_test_path(p, globs)]


def sanitize(text):
    """Make command output safe to paste into a PR: no control characters, no secrets, bounded lines."""
    kept = []
    for line in text.splitlines():
        line = _CONTROL.sub("", line)
        if any(pattern.search(line) for _, pattern in SECRETS):
            line = "[line redacted: possible secret]"
        kept.append(line if len(line) <= MAX_LINE else line[:MAX_LINE - 3] + "...")
    return "\n".join(kept[-TAIL_LINES:])


def run_command(argv, cwd, timeout):
    """Return {"rc", "tail", "error"}; error is set when the command could not be run to completion."""
    try:
        proc = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=clean_env(), timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return {"rc": None, "tail": sanitize((exc.stdout or b"").decode("utf-8", "replace")), "error": "timed out after %ds" % timeout}
    except OSError as exc:
        return {"rc": None, "tail": "", "error": "cannot run %s: %s" % (argv[0], exc)}
    return {"rc": proc.returncode, "tail": sanitize(proc.stdout.decode("utf-8", "replace")), "error": None}


def classify(runs):
    """'RED' (all failed), 'GREEN' (all passed), 'FLAKY' (mixed) or 'ERROR'."""
    if any(run["error"] for run in runs):
        return "ERROR"
    failed = [run["rc"] != 0 for run in runs]
    if all(failed):
        return "RED"
    if not any(failed):
        return "GREEN"
    return "FLAKY"


def prove(root, base, head, command, globs, setup, repeat, timeout):
    """Run the proof. Returns a result dict. Raises ToolError for tooling failures."""
    head_sha = resolve(root, head)
    base_sha = resolve(root, base)
    code, out, err = git(root, "merge-base", base_sha, head_sha)
    if code != 0 or not out.strip():
        raise ToolError("no merge-base between %s and %s" % (base, head))
    start = out.decode().strip()
    tests = changed_test_files(root, start, head_sha, globs)
    result = {"command": command, "base": base, "head": head, "start": start, "head_sha": head_sha, "tests": tests,
              "repeat": repeat, "red": [], "green": [], "verdict": None}
    if not tests:
        result["verdict"] = "NO_TESTS"
        return result

    scratch = tempfile.mkdtemp(prefix="redgreen-")
    made = []
    try:
        for name, commit in (("red", start), ("green", head_sha)):
            path = os.path.join(scratch, name)
            code, _, err = git(root, "worktree", "add", "--detach", "--quiet", path, commit)
            if code != 0:
                raise ToolError("git worktree add failed: %s" % err[-120:])
            made.append(path)
        red_dir, green_dir = made
        for chunk in range(0, len(tests), 200):
            code, _, err = git(red_dir, "checkout", head_sha, "--", *tests[chunk:chunk + 200])
            if code != 0:
                raise ToolError("could not overlay head's tests onto the base: %s" % err[-120:])
        if setup:
            for label, directory in (("base", red_dir), ("head", green_dir)):
                done = run_command(setup, directory, timeout)
                if done["error"] or done["rc"] != 0:
                    raise ToolError("--setup failed in the %s worktree: %s" % (label, done["error"] or ("exit %s: %s" % (done["rc"], done["tail"][-120:]))))
        result["red"] = [run_command(command, red_dir, timeout) for _ in range(repeat)]
        result["green"] = [run_command(command, green_dir, timeout) for _ in range(repeat)]
    finally:
        for path in made:
            git(root, "worktree", "remove", "--force", path)
        shutil.rmtree(scratch, ignore_errors=True)
        git(root, "worktree", "prune")

    red, green = classify(result["red"]), classify(result["green"])
    if "ERROR" in (red, green):
        problems = [run["error"] for run in result["red"] + result["green"] if run["error"]]
        raise ToolError(problems[0])
    if red == "GREEN":
        verdict = "NOT_RED"
    elif "FLAKY" in (red, green):
        verdict = "FLAKY"
    elif green == "RED":
        verdict = "NOT_GREEN"
    else:
        verdict = "PASS"
    result["verdict"] = verdict
    return result


def evidence(result):
    """Markdown block to paste into the PR."""
    cmd = " ".join(shlex.quote(a) for a in result["command"])
    lines = ["### Red-to-green evidence",
             "- command: `%s` (repeat %d)" % (cmd, result["repeat"]),
             "- change started at %s; head is %s" % (result["start"][:12], result["head_sha"][:12]),
             "- tests overlaid from head: %s" % (", ".join(result["tests"][:5]) + (" +%d more" % (len(result["tests"]) - 5) if len(result["tests"]) > 5 else ""))]
    if result["red"]:
        codes = [str(run["rc"]) for run in result["red"]]
        lines += ["- RED (base code + head's tests): exit %s" % ", ".join(codes), "```", result["red"][-1]["tail"], "```"]
        codes = [str(run["rc"]) for run in result["green"]]
        lines += ["- GREEN (head): exit %s" % ", ".join(codes), "```", result["green"][-1]["tail"], "```"]
    lines.append("- verdict: %s%s" % (result["verdict"], ". Read the RED output: it must fail for the stated reason, not a typo or a missing dependency."
                                      if result["verdict"] == "PASS" else ""))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prove tests fail before the change and pass after it")
    parser.add_argument("--cmd", required=True, help="test command, e.g. \"pytest tests/test_x.py -q\" (run as argv, not through a shell)")
    parser.add_argument("--base", required=True, help="branch or commit the change started from, e.g. origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--test-glob", action="append", help="what counts as a test file (repeatable; default: common test names)")
    parser.add_argument("--setup", help="command to run in each worktree first, e.g. \"npm ci\"")
    parser.add_argument("--repeat", type=int, default=1, help="runs per phase; use 3 for anything flaky (max %d)" % MAX_REPEAT)
    parser.add_argument("--timeout", type=int, default=300, help="seconds per run")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        command = shlex.split(args.cmd)
        setup = shlex.split(args.setup) if args.setup else None
    except ValueError as exc:
        sys.stderr.write("redgreen.py: cannot parse the command: %s\n" % exc)
        return 2
    if not command:
        sys.stderr.write("redgreen.py: --cmd is empty\n")
        return 2
    if not 1 <= args.repeat <= MAX_REPEAT or args.timeout < 1:
        sys.stderr.write("redgreen.py: --repeat must be 1-%d and --timeout >= 1\n" % MAX_REPEAT)
        return 2

    try:
        result = prove(args.repo_root, args.base, args.head, command, tuple(args.test_glob or DEFAULT_TEST_GLOBS),
                       setup, args.repeat, args.timeout)
    except ToolError as exc:
        if args.json:
            print(json.dumps({"verdict": "ERROR", "error": str(exc)}, sort_keys=True))
        else:
            print("ERROR: %s" % exc)
        return 3
    if args.json:
        slim = dict(result, command=" ".join(shlex.quote(a) for a in result["command"]))
        print(json.dumps(slim, sort_keys=True))
    else:
        print(evidence(result) if result["tests"] else "NO_TESTS: no test file was added or changed between %s and %s, so nothing "
              "proves the new behaviour. Add a test, or state why none applies in the PR (`Tests: none - <reason>`)."
              % (result["start"][:12], result["head_sha"][:12]))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
