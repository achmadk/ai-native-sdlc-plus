import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

if __package__:
    from . import support
else:
    import support

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


class ShippedPolicy(unittest.TestCase):
    def setUp(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.rules, error = lane.load_rules(os.path.join(root, "scripts", "lane-config.yaml"))
        self.assertEqual(error, "")

    def test_platform_bound_names_are_classified_without_creating_files(self):
        for raw, expected in (("docs/source\n.py", "Standard"), ("docs/ literal[1]*.md", "Lite"),
                              ("docs/::error::x.md", "Lite")):
            with self.subTest(raw=raw):
                got, _, details = lane.classify_detailed([raw], self.rules)
                self.assertEqual(got, expected)
                self.assertEqual(details[0]["raw_path"], raw)
                self.assertFalse(details[0]["metadata_available"])

    def test_nul_delimited_git_records_preserve_platform_bound_names(self):
        raw_paths = ["docs/source\n.py", "docs/ literal[1]*.md", "docs/::error::x.md"]
        data = b"".join(b":000000 100644 0000000 abcdef0 A\0" + path.encode() + b"\0" for path in raw_paths)
        with patch.object(lane.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, data, b"")):
            changes = lane.git_changed_files("main")
        self.assertEqual([entry["raw_path"] for entry in changes], raw_paths)
        got, _, details = lane.classify_detailed(raw_paths, self.rules, changes)
        self.assertEqual(got, "Standard")
        self.assertIn("malformed", details[0]["note"])
        self.assertTrue(all(entry["metadata_available"] for entry in details))

    def test_nested_security_directories_are_critical(self):
        for path in ("src/auth/login.py", "src/authentication/token.py",
                     "src/payments/charge.py", "services/payment/refund.py",
                     "services/api/migrations/001.sql", "services/infra/main.tf",
                     "src/infrastructure/network.tf", "src/security/policy.py"):
            with self.subTest(path=path):
                self.assertEqual(lane.classify([path], self.rules)[0], "Critical")

    def test_entire_execution_boundary_overrides_permissive_config(self):
        permissive = lane.parse_config('version: 1\nlite:\n  - "**"\n')
        for path in ("scripts/json.py", "scripts/new/dependency.py", "install.sh",
                     "install.ps1", "scripts/install-manifest.json", ".sdlc-install.json",
                     ".gitattributes", "hooks/.gitattributes",
                     "skills/spec-first/scripts/check_spec.py", "skills/ai-sdlc/SKILL.md",
                     "skills/ai-sdlc/assets/ci-generic.sh", "adapters/ci/gitlab-ci.yml",
                     "AGENTS.md", "src/AGENTS.md", "CLAUDE.md", "GEMINI.md",
                     ".github/copilot-instructions.md", ".cursor/rules/security.mdc",
                     ".kilo/agent/reviewer.md", ".kilo/command/deploy.md", "kilo.json"):
            with self.subTest(path=path):
                self.assertEqual(lane.classify([path], permissive)[0], "Critical")

    def test_non_prose_documentation_is_not_lite(self):
        for path in ("docs/deploy.sh", "docs/example.py", "docs/widget.js",
                     "docs/page.mdx", "docs/notebook.ipynb", "docs/unknown.data"):
            with self.subTest(path=path):
                self.assertEqual(lane.classify([path], self.rules)[0], "Standard")

    def test_shipped_lockfile_rules_are_at_least_standard(self):
        for path in ("yarn.lock", "services/api/poetry.lock", "package-lock.json"):
            with self.subTest(path=path):
                self.assertEqual(lane.classify([path], self.rules)[0], "Standard")

    def test_recognized_prose_remains_lite(self):
        for path in ("README.md", "docs/guide.md", "docs/notes.txt"):
            with self.subTest(path=path):
                self.assertEqual(lane.classify([path], self.rules)[0], "Lite")

    def test_absolute_prose_paths_are_rejected_not_classified_lite(self):
        for path in ("/tmp/readme.md", "//server/share/readme.md", "C:/notes.md"):
            with self.subTest(path=path):
                self.assertIsNone(lane.clean_path(path)[0])
                self.assertEqual(lane.classify([path], self.rules)[0], "Standard")


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
        self.addCleanup(support.remove_tree, self.tmp)
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
        self.addCleanup(support.remove_tree, self.repo)
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

    def change_details(self, strict=False):
        cfg = os.path.join(os.path.dirname(lane.__file__), "lane-config.yaml")
        args = ["--config", cfg, "--base", self.base, "--repo-root", self.repo, "--json"]
        if strict:
            args.append("--strict")
        code, out, _ = run_main(args)
        return code, json.loads(out)

    def test_change_facts_executable_mode_is_not_lite(self):
        self.g("update-index", "--chmod=+x", "docs/a.md")
        self.g("commit", "-q", "-m", "make executable")
        code, report = self.change_details()
        self.assertEqual((code, report["lane"]), (0, "Standard"))
        entry = report["paths"][0]
        self.assertEqual(entry.get("old_mode"), "100644")
        self.assertEqual(entry.get("new_mode"), "100755")
        self.assertEqual(entry.get("status"), "M")

    def test_change_facts_symlink_type_is_not_lite(self):
        self.write("docs/a.md", "../auth/login.py")
        blob = self.g("hash-object", "-w", "docs/a.md").strip()
        self.g("update-index", "--cacheinfo", "120000", blob, "docs/a.md")
        self.g("commit", "-q", "-m", "replace prose with symlink")
        code, report = self.change_details()
        self.assertEqual((code, report["lane"]), (0, "Standard"))
        self.assertEqual(report["paths"][0].get("new_mode"), "120000")
        self.assertEqual(report["paths"][0].get("status"), "T")

    def test_change_facts_keep_deleted_file_mode(self):
        self.g("rm", "docs/a.md")
        self.g("commit", "-q", "-m", "delete prose")
        code, report = self.change_details()
        self.assertEqual((code, report["lane"]), (0, "Lite"))
        entry = report["paths"][0]
        self.assertEqual(entry.get("old_mode"), "100644")
        self.assertEqual(entry.get("new_mode"), "000000")
        self.assertEqual(entry.get("status"), "D")

    def test_change_facts_preserve_malformed_raw_path(self):
        raw = "docs/source\n.py"
        support.require_filename(os.path.basename(raw))
        self.write(raw, "print('source')\n")
        self.commit()
        code, report = self.change_details()
        self.assertEqual((code, report["lane"]), (0, "Standard"))
        self.assertEqual(report["paths"][0].get("raw_path"), raw)
        self.assertIn("malformed", report["paths"][0]["note"])

    def test_change_facts_missing_metadata_fails_closed(self):
        response = subprocess.CompletedProcess([], 0, b"docs/a.md\0", b"")
        with patch.object(lane.subprocess, "run", return_value=response):
            code, report = self.change_details(strict=True)
        self.assertEqual(code, 3)
        self.assertTrue(report["error"])

    def test_change_facts_raw_paths_are_not_normalized_for_git(self):
        raw = "docs/ literal[1]*.md"
        support.require_filename(os.path.basename(raw))
        self.write(raw, "text\n")
        self.commit()
        code, report = self.change_details()
        self.assertEqual(code, 0)
        self.assertEqual(report["paths"][0].get("raw_path"), raw)
        self.assertEqual(lane.git_changed_paths(self.base, "HEAD", self.repo), [raw])

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


class NativeAgentControlBoundary(unittest.TestCase):
    """Task 4.4: all generated native agent instruction/command/skill paths and nested locations stay Critical."""

    def test_generated_and_nested_agent_control_paths_override_permissive_lite_and_non_executable_config(self):
        import evidence_check
        import agent_profiles

        permissive = lane.parse_config(
            'version: 1\n'
            'lite:\n'
            '  - "**"\n'
            'non_executable:\n'
            '  - "**"\n'
        )
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        generated_paths = sorted(agent_profiles.recognized_profile_paths(root))
        self.assertGreater(len(generated_paths), 200)

        nested_and_surface_paths = [
            "AGENTS.md",
            "nested/AGENTS.md",
            "AGENTS.override.md",
            "packages/web/AGENTS.override.md",
            "CLAUDE.md",
            "packages/web/CLAUDE.md",
            "CLAUDE.local.md",
            "packages/web/CLAUDE.local.md",
            "GEMINI.md",
            "packages/web/GEMINI.md",
            "opencode.json",
            "packages/web/opencode.json",
            "opencode.jsonc",
            "kilo.json",
            "packages/web/kilo.json",
            "kilo.jsonc",
            ".cursor/skills/ai-sdlc/SKILL.md",
            ".cursor/skills/sdlc-check/SKILL.md",
            ".cursor/commands/sdlc.md",
            ".github/copilot-instructions.md",
            ".github/skills/ai-sdlc/SKILL.md",
            ".github/prompts/sdlc-check.prompt.md",
            ".github/agents/reviewer.agent.md",
            ".agents/skills/ai-sdlc/SKILL.md",
            "services/api/.agents/skills/ai-sdlc/SKILL.md",
            ".gemini/skills/ai-sdlc/SKILL.md",
            ".gemini/commands/sdlc/check.toml",
            "services/api/.gemini/commands/sdlc/check.toml",
            ".opencode/skills/ai-sdlc/SKILL.md",
            ".opencode/commands/sdlc/check.md",
            "services/api/.opencode/commands/sdlc/check.md",
            ".kilo/skills/ai-sdlc/SKILL.md",
            ".kilo/command/sdlc-check.md",
        ]

        for path in generated_paths + nested_and_surface_paths:
            with self.subTest(path=path):
                got_lane, reason = lane.classify([path], permissive)
                self.assertEqual(got_lane, "Critical", "%s classified as %s (%s)" % (path, got_lane, reason))
                self.assertIn("(built-in)", reason)
                changes = [{"raw_path": path, "old_mode": "100644", "new_mode": "100644", "status": "M"}]
                detected = evidence_check.detect(
                    body="## Intent\nAttempting to exempt an agent control file as prose.\n",
                    paths=[path],
                    repo_root=root,
                    rules=permissive,
                    lane=got_lane,
                    changes=changes,
                )
                self.assertFalse(
                    detected["test_changes"][0],
                    "%s must not obtain a non-executable test exemption: %r" % (path, detected["test_changes"]),
                )


if __name__ == "__main__":
    unittest.main()
