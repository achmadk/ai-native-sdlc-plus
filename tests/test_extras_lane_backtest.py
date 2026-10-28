import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import lane_backtest as lb  # noqa: E402

GIT = shutil.which("git")

FAKE_LANE = """\
import sys
paths = sys.argv[sys.argv.index("--paths") + 1:]
if all(p.startswith("docs/") for p in paths):
    print("Lite: matched Lite rule docs/**")
elif any(p.startswith("auth/") for p in paths):
    print("Critical: matched Critical rule auth/**")
else:
    print("Standard: default")
"""


def git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def commit_file(repo, rel, text="x\n"):
    path = Path(repo) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"change {rel}")


class ParseTests(unittest.TestCase):
    def test_parse_documented_output(self):
        self.assertEqual(lb.parse_lane("Lite: matched Lite rule docs/**\n"), ("Lite", "matched Lite rule docs/**"))

    def test_parse_skips_noise_lines(self):
        out = "WARNING: something\nstandard - default rule\n"
        self.assertEqual(lb.parse_lane(out), ("Standard", "default rule"))

    def test_unrecognised_output(self):
        self.assertEqual(lb.parse_lane("usage: lane.py\n"), (None, ""))

    def test_build_command_styles(self):
        files = ["a", "b"]
        self.assertEqual(lb.build_command("l.py", files, "args")[2:], ["--paths", "a", "b"])
        self.assertEqual(lb.build_command("l.py", files, "comma")[2:], ["--paths", "a,b"])
        self.assertEqual(lb.build_command("l.py", files, "repeat")[2:], ["--paths", "a", "--paths", "b"])
        with self.assertRaises(lb.BacktestError):
            lb.build_command("l.py", files, "nope")


@unittest.skipUnless(GIT, "git is not installed")
class BacktestTests(unittest.TestCase):
    def make_repo(self, tmp):
        git(tmp, "init", "-q")
        (Path(tmp) / "scripts").mkdir()
        (Path(tmp) / "scripts" / "lane.py").write_text(FAKE_LANE, encoding="utf-8")
        git(tmp, "add", "-A")
        git(tmp, "commit", "-q", "-m", "add lane")
        commit_file(tmp, "docs/a.md")
        commit_file(tmp, "src/x.py")
        commit_file(tmp, "auth/login.py")
        commit_file(tmp, "docs/b.md")

    def test_end_to_end_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_repo(tmp)
            results = lb.backtest(tmp, "HEAD", 10, str(Path(tmp) / "scripts" / "lane.py"))
            summary = lb.summarize(results)
            # root commit adds scripts/lane.py -> Standard; then Lite, Standard, Critical, Lite
            self.assertEqual(summary["commits"], 5)
            self.assertEqual(summary["lanes"], {"Lite": 2, "Standard": 2, "Critical": 1})
            self.assertEqual(summary["unclassified"], 0)
            self.assertEqual(summary["top_rules"][0], ("Lite: matched Lite rule docs/**", 2))

    def test_limit_applies(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_repo(tmp)
            results = lb.backtest(tmp, "HEAD", 2, str(Path(tmp) / "scripts" / "lane.py"))
            self.assertEqual(len(results), 2)

    def test_too_many_files_is_skipped_not_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_repo(tmp)
            for i in range(3):
                (Path(tmp) / "bulk").mkdir(exist_ok=True)
                (Path(tmp) / "bulk" / f"f{i}.txt").write_text("x", encoding="utf-8")
            git(tmp, "add", "-A")
            git(tmp, "commit", "-q", "-m", "bulk")
            results = lb.backtest(tmp, "HEAD", 1, str(Path(tmp) / "scripts" / "lane.py"), max_files=2)
            self.assertTrue(results[0]["status"].startswith("skipped"))
            self.assertIsNone(results[0]["lane"])

    def test_unclassified_is_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_repo(tmp)
            runner = lambda script, files, style, root: (2, "usage: lane.py [-h]\n")  # noqa: E731
            results = lb.backtest(tmp, "HEAD", 3, "ignored.py", runner=runner)
            summary = lb.summarize(results)
            self.assertEqual(summary["unclassified"], 3)
            self.assertEqual(sum(summary["lanes"].values()), 0)

    def test_bad_revision_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_repo(tmp)
            with self.assertRaises(lb.BacktestError):
                lb.backtest(tmp, "no-such-rev", 3, "x.py")


@unittest.skipUnless(GIT, "git is not installed")
class CliTests(unittest.TestCase):
    def test_report_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            BacktestTests().make_repo(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = lb.main(["--root", tmp, "--limit", "10"])
            self.assertEqual(rc, 0)
            text = buf.getvalue()
            self.assertIn("Critical", text)
            self.assertIn("Most frequent rules:", text)

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = lb.main(["--root", tmp, "--limit", "10", "--json"])
            data = json.loads(buf.getvalue())
            self.assertEqual(data["summary"]["lanes"]["Critical"], 1)

    def test_missing_lane_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            git(tmp, "init", "-q")
            old, sys.stderr = sys.stderr, io.StringIO()
            try:
                rc = lb.main(["--root", tmp])
            finally:
                sys.stderr = old
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
