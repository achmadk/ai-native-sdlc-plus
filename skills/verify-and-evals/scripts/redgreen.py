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
import xml.etree.ElementTree as ET

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


def split_command(text):
    """Split a command line with the host shell's quoting rules.

    Windows paths contain backslashes, so POSIX shlex would eat them; there quotes
    only group whitespace and everything else is literal.
    """
    return shlex.split(text) if os.name != "nt" else _split_windows(text)


def _split_windows(text):
    tokens, current, quote, started = [], [], None, False
    for char in text:
        if quote:
            if char == quote:
                quote = None
            else:
                current.append(char)
        elif char in "\"'":
            quote, started = char, True
        elif char.isspace():
            if started:
                tokens.append("".join(current))
                current, started = [], False
        else:
            current.append(char)
            started = True
    if quote:
        raise ValueError("No closing quotation")
    if started:
        tokens.append("".join(current))
    return tokens


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


def parse_junit(path):
    """Read a JUnit XML report and count executed cases, failures and errors."""
    try:
        tree = ET.parse(path)
    except OSError as exc:
        raise ToolError("cannot read JUnit report %s: %s" % (path, exc))
    except ET.ParseError as exc:
        raise ToolError("cannot parse JUnit report %s: %s" % (path, exc))
    cases = []
    for node in tree.getroot().iter("testcase"):
        cases.append({"name": node.get("name") or "",
                      "classname": node.get("classname") or "",
                      "failed": node.find("failure") is not None,
                      "errored": node.find("error") is not None})
    return {"path": path, "tests": len(cases),
            "failures": sum(1 for case in cases if case["failed"]),
            "errors": sum(1 for case in cases if case["errored"]),
            "cases": cases}


def _canonical_test(identifier):
    text = identifier.strip().strip("`'\"").lower().replace("\\", "/")
    text = re.sub(r"\.(?:py|js|jsx|ts|tsx|go|rb|java|cs|php|rs)\b", "", text)
    text = text.replace("::", "/").replace(".", "/")
    return re.sub(r"/+", "/", text).strip("/")


def _test_id_matches(mapped, case_canonical):
    if not mapped or not case_canonical:
        return False
    if mapped == case_canonical or case_canonical.endswith("/" + mapped):
        return True
    mapped_parts, case_parts = mapped.split("/"), case_canonical.split("/")
    if mapped_parts[-1] != case_parts[-1]:
        return False
    if len(mapped_parts) == 1:
        return True
    return case_parts[:len(mapped_parts) - 1] == mapped_parts[:-1]


def parse_ac_map(path):
    """Extract mapped test identifiers (file.py::Class::test or test-only ids) from a markdown file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read(1000000)
    except OSError as exc:
        raise ToolError("cannot read acceptance-criteria mapping %s: %s" % (path, exc))
    identifiers = []
    for line in text.splitlines():
        if "->" not in line or "|" not in line:
            continue
        target = line.split("->", 1)[1].split("|", 1)[0]
        for match in re.findall(r"[A-Za-z0-9_./\\-]+::[A-Za-z0-9_.:\\-]+", target):
            if match not in identifiers:
                identifiers.append(match)
    return identifiers


def missing_ac_tests(identifiers, report):
    """Return mapped test identifiers that did not appear in the executed report."""
    canonical = [_canonical_test(case["classname"] + "::" + case["name"]) for case in report["cases"]]
    missing = []
    for identifier in identifiers:
        mapped = _canonical_test(identifier)
        if not any(_test_id_matches(mapped, case) for case in canonical):
            missing.append(identifier)
    return missing


def prove(root, base, head, command, globs, setup, repeat, timeout, junit=None, ac_map=None):
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
    identifiers = None
    if ac_map:
        map_path = ac_map if os.path.isabs(ac_map) else os.path.join(root, ac_map)
        identifiers = parse_ac_map(map_path)
        result["ac_map"] = {"path": ac_map, "identifiers": identifiers, "missing": []}
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
        if junit:
            reports = {}
            for label, directory in (("red", red_dir), ("green", green_dir)):
                report_path = junit if os.path.isabs(junit) else os.path.join(directory, junit)
                reports[label] = parse_junit(report_path)
            result["junit"] = reports
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
    if "junit" in result:
        red_report, green_report = result["junit"]["red"], result["junit"]["green"]
        if red_report["tests"] == 0 or green_report["tests"] == 0:
            verdict = "NO_TESTS"
        elif red_report["errors"] and not red_report["failures"]:
            verdict = "COLLECTION_ERROR"
        elif green_report["errors"] and not green_report["failures"]:
            verdict = "COLLECTION_ERROR"
        elif green_report["failures"] or green_report["errors"]:
            verdict = "NOT_GREEN"
    if verdict == "PASS" and identifiers is not None:
        missing = missing_ac_tests(identifiers, result["junit"]["green"])
        result["ac_map"]["missing"] = missing
        if missing:
            verdict = "AC_MISMATCH"
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
    if "junit" in result:
        red_report, green_report = result["junit"]["red"], result["junit"]["green"]
        lines.append("- junit: red tests=%d failures=%d errors=%d; green tests=%d failures=%d errors=%d" % (
            red_report["tests"], red_report["failures"], red_report["errors"],
            green_report["tests"], green_report["failures"], green_report["errors"]))
    if "ac_map" in result:
        mapped = result["ac_map"]
        if mapped["missing"]:
            lines.append("- AC mapping: %d of %d mapped test(s) did not execute: %s" % (
                len(mapped["missing"]), len(mapped["identifiers"]), ", ".join(mapped["missing"])))
        else:
            lines.append("- AC mapping: all %d mapped test(s) executed" % len(mapped["identifiers"]))
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
    parser.add_argument("--junit", help="JUnit XML report produced inside each worktree (relative path or absolute)")
    parser.add_argument("--ac-map", help="markdown file mapping acceptance criteria to test ids (e.g. tasks.md); requires --junit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        command = split_command(args.cmd)
        setup = split_command(args.setup) if args.setup else None
    except ValueError as exc:
        sys.stderr.write("redgreen.py: cannot parse the command: %s\n" % exc)
        return 2
    if not command:
        sys.stderr.write("redgreen.py: --cmd is empty\n")
        return 2
    if not 1 <= args.repeat <= MAX_REPEAT or args.timeout < 1:
        sys.stderr.write("redgreen.py: --repeat must be 1-%d and --timeout >= 1\n" % MAX_REPEAT)
        return 2
    if args.ac_map and not args.junit:
        sys.stderr.write("redgreen.py: --ac-map requires --junit (there is no executed report to cross-check)\n")
        return 2

    try:
        result = prove(args.repo_root, args.base, args.head, command, tuple(args.test_glob or DEFAULT_TEST_GLOBS),
                       setup, args.repeat, args.timeout, args.junit, args.ac_map)
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
