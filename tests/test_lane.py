import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import lane  # noqa: E402

CONFIG = """\
version: 1
critical:
  - "auth/**"
  - "**/migrations/**"
standard:
  - "src/**"
lite:
  - "docs/**"
  - "*.lock"   # any depth
"""


def rules():
    return lane.parse_config(CONFIG)


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = lane.main(argv)
    return code, out.getvalue(), err.getvalue()


class Classification(unittest.TestCase):
    def test_backward_compatible_single_path_reason(self):
        self.assertEqual(lane.classify(["docs/guide.md"], rules()), ("Lite", "matched Lite rule docs/**"))

    def test_lite_requires_every_path_to_be_lite(self):
        # Regression: one Lite match used to hide an unmatched code file.
        got, _ = lane.classify(["docs/a.md", "lib/payments.py"], rules())
        self.assertEqual(got, "Standard")

    def test_all_lite_stays_lite(self):
        self.assertEqual(lane.classify(["docs/a.md", "yarn.lock"], rules())[0], "Lite")

    def test_highest_lane_wins(self):
        self.assertEqual(lane.classify(["docs/a.md", "src/x.py", "auth/login.py"], rules())[0], "Critical")

    def test_unmatched_is_standard_never_lite(self):
        self.assertEqual(lane.classify(["tools/x.sh"], rules())[0], "Standard")

    def test_no_paths_escalates(self):
        self.assertEqual(lane.classify([], rules())[0], "Standard")

    def test_malformed_entry_does_not_mask_critical(self):
        # Regression: one bad entry used to return Standard for the whole change.
        for bad in ("", "   ", None, 7, "a\x00b", "/etc/passwd", "../x", "a/../../b", "C:\\x", "x" * 5000):
            got, _ = lane.classify(["auth/login.py", bad], rules())
            self.assertEqual(got, "Critical", repr(bad))

    def test_malformed_entry_alone_is_standard(self):
        for bad in ("", "/etc/passwd", "../x", "a\x00b"):
            self.assertEqual(lane.classify([bad], rules())[0], "Standard", repr(bad))

    def test_unsafe_paths_are_never_lite_even_under_a_catch_all_lite_rule(self):
        # With a "**" Lite rule, only explicit validation keeps these out of Lite.
        lite_all = lane.parse_config('version: 1\nlite:\n  - "**"\n')
        for bad in ("/etc/passwd", "C:\\Windows\\x", "a\x00b", "a\nb", "../x"):
            self.assertEqual(lane.classify([bad], lite_all)[0], "Standard", repr(bad))

    def test_backslash_traversal_caught(self):
        self.assertEqual(lane.classify(["docs\\..\\auth\\x"], rules())[0], "Standard")

    def test_dot_slash_prefix_and_double_slash_normalised(self):
        self.assertEqual(lane.classify(["./auth//login.py"], rules())[0], "Critical")

    def test_builtin_control_paths_are_critical_even_if_config_says_lite(self):
        lite_all = lane.parse_config('version: 1\nlite:\n  - "**"\n')
        for path in ("scripts/lane.py", "scripts/lane-config.yaml", "scripts/evidence_check.py",
                     ".github/workflows/sdlc-gate.yml", "CODEOWNERS", ".github/CODEOWNERS", "hooks/pre-push.sh"):
            self.assertEqual(lane.classify([path], lite_all)[0], "Critical", path)

    def test_critical_rules_are_case_insensitive(self):
        self.assertEqual(lane.classify(["AUTH/Login.py"], rules())[0], "Critical")
        self.assertEqual(lane.classify([".GitHub/Workflows/x.yml"], rules())[0], "Critical")

    def test_lite_rules_are_case_sensitive(self):
        self.assertEqual(lane.classify(["DOCS/evil.py"], rules())[0], "Standard")

    def test_unicode_normalisation(self):
        cfg = lane.parse_config('version: 1\ncritical:\n  - "caf\u00e9/**"\n')  # precomposed
        self.assertEqual(lane.classify(["cafe\u0301/x.py"], cfg)[0], "Critical")  # decomposed

    def test_per_path_detail(self):
        _, _, per = lane.classify_detailed(["docs/a.md", "src/b.py"], rules())
        self.assertEqual([p["lane"] for p in per], ["Lite", "Standard"])

    def test_reason_never_contains_workflow_command(self):
        _, reason, _ = lane.classify_detailed(["docs/a.md", "::error::pwn"], rules())
        self.assertNotIn("::", reason)


class Glob(unittest.TestCase):
    CASES = [
        # pattern, path, expected
        ("docs/**", "docs/a.md", True),
        ("docs/**", "docs/x/y/z.md", True),
        ("docs/**", "docs", False),
        ("docs/**", "adocs/a.md", False),
        ("docs/", "docs/a.md", True),
        ("**/*.md", "README.md", True),          # regression: fnmatch missed the root file
        ("**/*.md", "a/b/c.md", True),
        ("src/*.py", "src/a.py", True),
        ("src/*.py", "src/sub/a.py", False),     # * does not cross /
        ("*.lock", "a/b/yarn.lock", True),       # no slash: any depth
        ("Dockerfile", "svc/api/Dockerfile", True),
        ("node_modules", "a/node_modules/x.js", True),
        ("a/**/b", "a/b", True),
        ("a/**/b", "a/x/y/b", True),
        ("a/**/b", "ab", False),
        ("skills/*/SKILL.md", "skills/x/SKILL.md", True),
        ("skills/*/SKILL.md", "skills/x/y/SKILL.md", False),
        ("file?.txt", "file1.txt", True),
        ("file?.txt", "file/.txt", False),
        ("[ab].txt", "[ab].txt", True),          # brackets are literal
        ("[ab].txt", "a.txt", False),
        ("a.b", "aXb", False),                   # dot is literal
    ]

    def test_table(self):
        for pattern, path, expected in self.CASES:
            self.assertEqual(lane.compile_pattern(pattern)(path), expected, "%s vs %s" % (pattern, path))

    def test_too_many_double_stars_rejected(self):
        with self.assertRaises(lane.ConfigError):
            lane.compile_pattern("**/**/**/**/**/x")

    def test_empty_pattern_rejected(self):
        with self.assertRaises(lane.ConfigError):
            lane.compile_pattern("  ")


class Config(unittest.TestCase):
    def bad(self, text, fragment):
        with self.assertRaises(lane.ConfigError) as ctx:
            lane.parse_config(text)
        self.assertIn(fragment, str(ctx.exception))

    def test_typo_in_section_is_an_error(self):
        # Regression: 'critcal:' used to be ignored, leaving auth/** unprotected.
        self.bad('version: 1\ncritcal:\n  - "auth/**"\nlite:\n  - "**"\n', "unknown key 'critcal'")

    def test_missing_or_wrong_version(self):
        self.bad('lite:\n  - "docs/**"\n', "version")
        self.bad('version: 2\nlite:\n  - "docs/**"\n', "version")

    def test_quoted_version_accepted(self):
        lane.parse_config('version: "1"\nlite:\n  - "docs/**"\n')

    def test_item_outside_section(self):
        self.bad('version: 1\n- "x"\n', "outside a section")

    def test_no_rules(self):
        self.bad("version: 1\ncritical:\nlite:\n", "no lane rules")

    def test_unterminated_quote(self):
        self.bad('version: 1\nlite:\n  - "docs/**\n', "unterminated")

    def test_inline_values_rejected(self):
        self.bad('version: 1\nlite: docs/**\n', "'- ' lines")

    def test_comments_and_quoted_hash(self):
        cfg = lane.parse_config('version: 1  # schema\nlite:   # low risk\n  - "docs/#notes/**"  # keep\n  - README.md # root\n')
        self.assertEqual(cfg["lite"], ["docs/#notes/**", "README.md"])

    def test_load_rules_reports_errors_instead_of_raising(self):
        rules_, error = lane.load_rules("/nonexistent/lane-config.yaml")
        self.assertIsNone(rules_)
        self.assertIn("cannot read config", error)


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.good = os.path.join(self.tmp, "good.yaml")
        self.badcfg = os.path.join(self.tmp, "bad.yaml")
        with open(self.good, "w") as handle:
            handle.write(CONFIG)
        with open(self.badcfg, "w") as handle:
            handle.write("version: 1\ncritcal:\n  - x\n")

    def test_plain_output_matches_documented_demo(self):
        code, out, _ = run_main(["--config", self.good, "--paths", "docs/guide.md"])
        self.assertEqual((code, out.strip()), (0, "Lite: matched Lite rule docs/**"))

    def test_config_error_escalates_locally_and_fails_closed_in_strict(self):
        code, out, err = run_main(["--config", self.badcfg, "--paths", "auth/x.py"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("Standard:"))
        self.assertIn("unknown key", err)
        code, _, _ = run_main(["--config", self.badcfg, "--strict", "--paths", "auth/x.py"])
        self.assertEqual(code, 3)

    def test_json_output(self):
        code, out, _ = run_main(["--config", self.good, "--json", "--paths", "docs/a.md", "src/b.py"])
        data = json.loads(out)
        self.assertEqual((code, data["lane"], len(data["paths"])), (0, "Standard", 2))

    def test_paths_and_base_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            run_main(["--config", self.good, "--paths", "a", "--base", "HEAD"])


class GitInput(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.g("init", "-q", "-b", "main")
        self.write("auth/login.py", "x = 1\n")
        self.write("docs/a.md", "hello\n")
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "base")
        self.base = self.g("rev-parse", "HEAD").strip()

    def g(self, *args):
        proc = subprocess.run(["git", "-C", self.repo, "-c", "user.email=t@t", "-c", "user.name=t", *args],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return proc.stdout.decode()

    def write(self, rel, text):
        full = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as handle:
            handle.write(text)

    def commit(self):
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "change")

    def test_rename_out_of_critical_dir_lists_both_sides(self):
        self.g("mv", "auth/login.py", "docs/login.py")
        self.commit()
        paths = lane.git_changed_paths(self.base, "HEAD", self.repo)
        self.assertEqual(sorted(paths), ["auth/login.py", "docs/login.py"])
        self.assertEqual(lane.classify(paths, rules())[0], "Critical")

    def test_deleted_file_is_listed(self):
        self.g("rm", "-q", "auth/login.py")
        self.commit()
        self.assertEqual(lane.git_changed_paths(self.base, "HEAD", self.repo), ["auth/login.py"])

    def test_odd_filenames_survive(self):
        self.write("docs/we ird\u00e9 name.md", "x\n")
        self.commit()
        self.assertEqual(lane.git_changed_paths(self.base, "HEAD", self.repo), ["docs/we ird\u00e9 name.md"])

    def test_unsafe_refs_rejected(self):
        for ref in ("--output=/tmp/x", "-p", "", "a b", "a;b"):
            with self.assertRaises(lane.GitError):
                lane.git_changed_paths(ref, "HEAD", self.repo)

    def test_unknown_ref_is_a_git_error(self):
        with self.assertRaises(lane.GitError):
            lane.git_changed_paths("deadbeef" * 5, "HEAD", self.repo)

    def test_cli_base_mode_and_empty_diff(self):
        cfg = os.path.join(self.repo, "cfg.yaml")
        with open(cfg, "w") as handle:
            handle.write(CONFIG)
        code, out, _ = run_main(["--config", cfg, "--base", self.base, "--repo-root", self.repo])
        self.assertEqual((code, out.strip()), (0, "Standard: no changed files, escalated"))


if __name__ == "__main__":
    unittest.main()
