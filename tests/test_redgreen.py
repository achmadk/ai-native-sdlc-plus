import contextlib
import glob
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "skills", "verify-and-evals", "scripts"))
import redgreen as rg  # noqa: E402

PY = shlex.quote(sys.executable)
CMD = "%s -m unittest discover -s tests -t ." % sys.executable
BUGGY = "def add(a, b):\n    return a - b\n"
FIXED = "def add(a, b):\n    return a + b\n"
TEST_ADD = ("import unittest\nfrom src.calc import add\n\n\nclass T(unittest.TestCase):\n"
            "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n")


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = rg.main(argv)
    return code, out.getvalue(), err.getvalue()


class Repo(unittest.TestCase):
    """main = buggy add(); branch 'fix' = the fix plus a test, ready for variations."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.g("init", "-q", "-b", "main")
        self.put("src/__init__.py", "")
        self.put("tests/__init__.py", "")
        self.put("src/calc.py", BUGGY)
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "base")
        self.g("checkout", "-q", "-b", "fix")
        self.before_dirs = set(glob.glob(os.path.join(tempfile.gettempdir(), "redgreen-*")))

    def g(self, *args):
        return subprocess.run(["git", "-C", self.repo, "-c", "user.email=t@t", "-c", "user.name=t"] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.decode()

    def put(self, rel, text):
        full = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as handle:
            handle.write(text)

    def commit(self, message="change"):
        self.g("add", "-A")
        self.g("commit", "-q", "-m", message)

    def fix_with_test(self):
        self.put("src/calc.py", FIXED)
        self.put("tests/test_calc.py", TEST_ADD)
        self.commit("fix + test")

    def prove(self, *extra, **kw):
        argv = ["--repo-root", self.repo, "--base", kw.get("base", "main"), "--cmd", kw.get("cmd", CMD)] + list(extra)
        return run_main(argv)

    def assertCleanedUp(self):
        self.assertEqual(len(self.g("worktree", "list").strip().splitlines()), 1)
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), "redgreen-*")))
        self.assertEqual(after - self.before_dirs, set())


class Verdicts(Repo):
    def test_an_honest_fix_is_red_then_green(self):
        self.fix_with_test()
        code, out, _ = self.prove("--repeat", "2")
        self.assertEqual(code, 0, out)
        self.assertIn("verdict: PASS", out)
        self.assertIn("RED (base code + head's tests): exit 1, 1", out)
        self.assertIn("GREEN (head): exit 0, 0", out)
        self.assertIn("-1 != 5", out)                  # it failed for the right reason, and the tool shows it
        self.assertIn("tests/test_calc.py", out)
        self.assertCleanedUp()

    def test_a_test_that_passes_without_the_change_proves_nothing(self):
        self.put("src/calc.py", FIXED)
        self.put("tests/test_other.py", "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_true(self):\n        self.assertTrue(True)\n")
        self.commit()
        code, out, _ = self.prove()
        self.assertEqual(code, 1)
        self.assertIn("verdict: NOT_RED", out)

    def test_a_test_that_fails_on_head_is_not_green(self):
        self.put("tests/test_calc.py", TEST_ADD)  # the fix itself is missing
        self.commit()
        code, out, _ = self.prove()
        self.assertEqual(code, 1)
        self.assertIn("verdict: NOT_GREEN", out)

    def test_no_test_change_is_reported_plainly(self):
        self.put("src/calc.py", FIXED)
        self.commit()
        code, out, _ = self.prove()
        self.assertEqual(code, 1)
        self.assertIn("NO_TESTS", out)
        self.assertIn("Tests: none - <reason>", out)

    def test_the_no_tests_verdict_is_decided_before_anything_is_run(self):
        self.put("src/calc.py", FIXED)
        self.commit()
        code, out, _ = self.prove("--json")
        data = json.loads(out)
        self.assertEqual((code, data["verdict"], data["red"], data["green"]), (1, "NO_TESTS", [], []))
        self.assertEqual(self.g("worktree", "list").count("\n"), 1)

    def test_nothing_changed_at_all(self):
        code, out, _ = self.prove()
        self.assertEqual(code, 1)
        self.assertIn("NO_TESTS", out)

    def test_deleted_tests_are_not_overlaid(self):
        self.put("tests/test_calc.py", TEST_ADD)
        self.commit("add test on the fix branch's base")
        self.g("checkout", "-q", "-b", "cleanup")
        os.remove(os.path.join(self.repo, "tests/test_calc.py"))
        self.commit("delete the test")
        code, out, _ = self.prove(base="fix")
        self.assertEqual(code, 1)
        self.assertIn("NO_TESTS", out)

    def test_flaky_results_are_not_a_pass(self):
        counter = os.path.join(self.repo, "..", "counter-%d" % os.getpid())
        if os.path.exists(counter):
            os.remove(counter)
        self.put("src/calc.py", FIXED)
        self.put("tests/test_flaky.py", (
            "import os, unittest\n\n\nclass T(unittest.TestCase):\n    def test_toggle(self):\n"
            "        path = os.environ['SDLC_COUNTER']\n"
            "        n = int(open(path).read()) + 1 if os.path.exists(path) else 1\n"
            "        open(path, 'w').write(str(n))\n        self.assertEqual(n % 2, 0)\n"))
        self.commit()
        with mock.patch.dict(os.environ, {"SDLC_COUNTER": counter}):
            code, out, _ = self.prove("--repeat", "2")
        self.assertEqual(code, 1)
        self.assertIn("verdict: FLAKY", out)

    def test_head_can_be_a_different_commit(self):
        self.fix_with_test()
        self.put("src/calc.py", BUGGY)  # a later commit breaks it again
        self.commit("regress")
        head = self.g("rev-parse", "HEAD~1").strip()
        code, out, _ = run_main(["--repo-root", self.repo, "--base", "main", "--head", head, "--cmd", CMD])
        self.assertEqual(code, 0, out)

    def test_the_merge_base_is_used_when_the_base_branch_moved_on(self):
        self.fix_with_test()
        self.g("checkout", "-q", "main")
        self.put("README.md", "unrelated work on main\n")
        self.commit("main moves on")
        self.g("checkout", "-q", "fix")
        code, out, _ = self.prove()
        self.assertEqual(code, 0, out)
        start = self.g("merge-base", "main", "fix").strip()[:12]
        self.assertIn("change started at %s" % start, out)


class Hygiene(Repo):
    def test_the_working_copy_is_never_touched(self):
        self.fix_with_test()
        self.put("src/calc.py", FIXED + "# uncommitted edit\n")
        self.put("scratch.txt", "untracked\n")
        before_status = self.g("status", "--porcelain")
        before_head = self.g("rev-parse", "HEAD")
        code, _, _ = self.prove()
        self.assertEqual(code, 0)
        self.assertEqual(self.g("status", "--porcelain"), before_status)
        self.assertEqual(self.g("rev-parse", "HEAD"), before_head)
        with open(os.path.join(self.repo, "scratch.txt")) as handle:
            self.assertEqual(handle.read(), "untracked\n")

    def test_worktrees_are_removed_even_when_the_run_fails(self):
        self.fix_with_test()
        self.prove(cmd="definitely-not-a-real-command-xyz")
        self.assertCleanedUp()

    def test_git_environment_variables_do_not_leak_in(self):
        # Inside a git hook GIT_DIR points at the hooked repo; the worktrees must not inherit it.
        self.fix_with_test()
        with mock.patch.dict(os.environ, {"GIT_DIR": "/nonexistent/.git", "GIT_INDEX_FILE": "/nonexistent/index"}):
            code, out, _ = self.prove()
        self.assertEqual(code, 0, out)

    def test_output_is_scrubbed_before_it_can_reach_a_pr(self):
        secret = "hunter2hunter2xx"
        self.put("src/calc.py", FIXED)
        self.put("tests/test_calc.py", TEST_ADD.replace("self.assertEqual(add(2, 3), 5)",
                 "print('password = %s')\n        print('bell\\x07 and escape\\x1b[31m')\n        self.assertEqual(add(2, 3), 5)" % secret))
        self.commit()
        # make the RED run print it: on the buggy base the assertion fails after the prints
        code, out, _ = self.prove()
        self.assertNotIn(secret, out)
        self.assertIn("[line redacted: possible secret]", out)
        self.assertNotIn("\x07", out)
        self.assertNotIn("\x1b", out)

    def test_sanitize_bounds_line_length_and_count(self):
        text = "\n".join(["x" * 500] * 40)
        cleaned = rg.sanitize(text).splitlines()
        self.assertEqual(len(cleaned), rg.TAIL_LINES)
        self.assertTrue(all(len(line) <= rg.MAX_LINE for line in cleaned))


class Pathspecs(Repo):
    def test_test_files_with_glob_characters_in_their_names_are_overlaid_literally(self):
        # Without --literal-pathspecs git would read "[1]" as a character class and silently match nothing.
        self.put("src/calc.py", FIXED)
        self.put("tests/test_[1].py", "# a test file whose name contains glob characters\n")
        self.commit()
        probe = ("import os, sys; ok = os.path.exists('tests/test_[1].py') and 'a + b' in open('src/calc.py').read(); "
                 "sys.exit(0 if ok else 1)")
        code, out, _ = self.prove(cmd="%s -c \"%s\"" % (sys.executable, probe))
        self.assertEqual(code, 0, out)
        self.assertIn("tests/test_[1].py", out)


class Magic(Repo):
    def test_a_filename_that_looks_like_pathspec_magic_is_taken_literally(self):
        # Interpreted as magic, ":(exclude)tests/x_test.py" would overlay head's WHOLE tree onto the base and
        # turn the red run green. Taken literally it overlays one file.
        self.put("src/calc.py", FIXED)
        self.put(":(exclude)tests/x_test.py", "# a test file with a hostile name\n")
        self.commit()
        probe = ("import os, sys; ok = os.path.exists(':(exclude)tests/x_test.py') and 'a + b' in open('src/calc.py').read(); "
                 "sys.exit(0 if ok else 1)")
        code, out, _ = self.prove(cmd="%s -c \"%s\"" % (sys.executable, probe))
        self.assertEqual(code, 0, out)
        self.assertIn("verdict: PASS", out)


class Failures(Repo):
    def test_a_missing_command_is_an_error_not_a_red(self):
        self.fix_with_test()
        code, out, _ = self.prove(cmd="definitely-not-a-real-command-xyz --flag")
        self.assertEqual(code, 3)
        self.assertIn("ERROR: cannot run", out)

    def test_a_timeout_is_an_error_not_a_red(self):
        self.put("tests/test_slow.py", "import time, unittest\n\n\nclass T(unittest.TestCase):\n    def test_slow(self):\n        time.sleep(30)\n")
        self.commit()
        code, out, _ = self.prove("--timeout", "1")
        self.assertEqual(code, 3)
        self.assertIn("timed out after 1s", out)
        self.assertCleanedUp()

    def test_unsafe_and_unknown_refs(self):
        self.fix_with_test()
        for ref in ("--output=/tmp/redgreen-pwned", "-p", "a b", "no-such-branch", ""):
            code, out, _ = run_main(["--repo-root", self.repo, "--base=" + ref, "--cmd", CMD])
            self.assertEqual(code, 3, ref)
        self.assertFalse(os.path.exists("/tmp/redgreen-pwned"))

    def test_not_a_git_repo(self):
        code, out, _ = run_main(["--repo-root", tempfile.mkdtemp(), "--base", "main", "--cmd", CMD])
        self.assertEqual(code, 3)

    def test_usage_errors(self):
        for argv in (["--base", "main", "--cmd", ""], ["--base", "main", "--cmd", "a 'unterminated"],
                     ["--base", "main", "--cmd", "x", "--repeat", "0"], ["--base", "main", "--cmd", "x", "--repeat", "11"],
                     ["--base", "main", "--cmd", "x", "--timeout", "0"]):
            code, _, err = run_main(["--repo-root", self.repo] + argv)
            self.assertEqual(code, 2, argv)
            self.assertTrue(err, argv)

    def test_setup_runs_in_each_worktree_and_its_failure_is_an_error(self):
        self.put("src/calc.py", FIXED)
        self.put("tests/test_calc.py", (
            "import os, unittest\nfrom src.calc import add\n\n\nclass T(unittest.TestCase):\n    def test_add(self):\n"
            "        self.assertTrue(os.path.exists('marker'))\n        self.assertEqual(add(2, 3), 5)\n"))
        self.commit()
        code, out, _ = self.prove()
        self.assertEqual(code, 1)          # no marker: red AND green fail, so NOT_GREEN
        self.assertIn("NOT_GREEN", out)
        setup = "%s -c \"open('marker', 'w').write('x')\"" % sys.executable
        # with the marker only the missing fix keeps the base red
        code, out, _ = self.prove("--setup", setup)
        self.assertEqual(code, 0, out)
        code, out, _ = self.prove("--setup", "%s -c \"raise SystemExit(5)\"" % sys.executable)
        self.assertEqual(code, 3)
        self.assertIn("--setup failed", out)


class Options(Repo):
    def test_json_output_is_pure(self):
        self.fix_with_test()
        code, out, _ = self.prove("--json")
        data = json.loads(out)
        self.assertEqual((code, data["verdict"], data["tests"]), (0, "PASS", ["tests/test_calc.py"]))

    def test_json_reports_errors_too(self):
        code, out, _ = run_main(["--repo-root", self.repo, "--base", "no-such", "--cmd", CMD, "--json"])
        self.assertEqual((code, json.loads(out)["verdict"]), (3, "ERROR"))

    def test_custom_test_globs(self):
        self.put("src/calc.py", FIXED)
        self.put("checks/__init__.py", "")
        self.put("checks/check_calc.py", TEST_ADD)
        self.commit()
        code, out, _ = self.prove("--test-glob", "checks", cmd="%s -m unittest discover -s checks -t . -p 'check_*.py'" % sys.executable)
        self.assertEqual(code, 0, out)
        code, out, _ = self.prove()            # default globs do not know about "checks"
        self.assertEqual(code, 1)
        self.assertIn("NO_TESTS", out)

    def test_is_test_path(self):
        for path, expected in (("tests/test_x.py", True), ("src/tests/helpers.py", True), ("a/b_test.go", True),
                               ("web/button.spec.ts", True), ("pkg/test_util.py", True), ("evals/regressions/1.md", True),
                               ("src/app.py", False), ("docs/testing-guide.md", False), ("src/contest.py", False)):
            self.assertEqual(rg.is_test_path(path, rg.DEFAULT_TEST_GLOBS), expected, path)

    def test_classify(self):
        run = lambda rc, error=None: {"rc": rc, "tail": "", "error": error}  # noqa: E731
        self.assertEqual(rg.classify([run(1), run(2)]), "RED")
        self.assertEqual(rg.classify([run(0), run(0)]), "GREEN")
        self.assertEqual(rg.classify([run(1), run(0)]), "FLAKY")
        self.assertEqual(rg.classify([run(None, "timed out")]), "ERROR")


if __name__ == "__main__":
    unittest.main()
