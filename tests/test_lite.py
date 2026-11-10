"""Contract tests for sdlc lite fast path (WS4 lite-fast-path)."""

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

if __package__:
    from . import support
else:
    import support

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SDLC = SCRIPTS / "sdlc.py"


def clean_env(**extra):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key != "GITHUB_STEP_SUMMARY"
    }
    env.update(PYTHONDONTWRITEBYTECODE="1", **extra)
    return env


class LiteContractTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = support.TemporaryDirectory(prefix="sdlc-lite-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def run_sdlc(self, *args, cwd=None, stdin_text=None, env=None, script=None):
        target = Path(script or SDLC)
        self.assertTrue(target.is_file(), "expected front-door CLI at %s" % target)
        cmd = [sys.executable, "-I", "-B", str(target)] + [str(a) for a in args]
        return subprocess.run(
            cmd,
            cwd=str(cwd or self.work),
            env=clean_env(**(env or {})),
            input=stdin_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

    def init_git_repo(self, directory):
        repo = Path(directory)
        repo.mkdir(parents=True, exist_ok=True)
        for cmd in (
            ["init", "-q", "-b", "main"],
            ["config", "user.name", "Lite Tester"],
            ["config", "user.email", "tester@example.com"],
            ["config", "commit.gpgsign", "false"],
        ):
            subprocess.run(["git", "-C", str(repo)] + cmd, env=clean_env(), check=True)
        return repo

    def create_commit(self, repo, message, files):
        for relpath, content in files.items():
            full = repo / Path(relpath)
            full.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                full.write_bytes(content)
            else:
                full.write_text(content, encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", str(full)], env=clean_env(), check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", message],
            env=clean_env(),
            check=True,
        )
        return subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            env=clean_env(),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()


class LiteCommandContract(LiteContractTestCase):
    """Task 2.1: public CLI contract tests for sdlc lite through WS3 front door."""

    def test_lite_usage_and_unsupported_options(self):
        # Missing --base fails with usage error (exit 2).
        no_base = self.run_sdlc("lite")
        self.assertEqual(no_base.returncode, 2, no_base.stderr)
        self.assertIn("--base", no_base.stderr)

        # --help prints usage and exits 0.
        help_res = self.run_sdlc("lite", "--help")
        self.assertEqual(help_res.returncode, 0, help_res.stderr)
        self.assertIn("sdlc lite", help_res.stdout)
        self.assertIn("--base", help_res.stdout)
        self.assertIn("--head", help_res.stdout)
        self.assertIn("--intent", help_res.stdout)
        self.assertIn("--output", help_res.stdout)

        # Disallowed flags (such as --present or --lane override) fail with exit 2.
        bad_lane = self.run_sdlc("lite", "--base", "main", "--lane", "Lite")
        self.assertEqual(bad_lane.returncode, 2)
        bad_present = self.run_sdlc("lite", "--base", "main", "--present", "intent_block")
        self.assertEqual(bad_present.returncode, 2)

    def test_lite_rejects_empty_range_invalid_revisions_and_non_git_repo(self):
        repo = self.init_git_repo(self.work / "empty-repo")
        c1 = self.create_commit(repo, "Initial commit", {"README.md": "# Demo\n"})

        # Empty range (base == head) fails (exit 1).
        empty_range = self.run_sdlc("lite", "--repo-root", repo, "--base", c1, "--head", c1)
        self.assertEqual(empty_range.returncode, 1, (empty_range.stdout, empty_range.stderr))
        self.assertIn("empty range", empty_range.stderr.lower())

        # Unknown revision fails (exit 3).
        bad_ref = self.run_sdlc("lite", "--repo-root", repo, "--base", "nonexistent-branch-sha")
        self.assertEqual(bad_ref.returncode, 3)
        self.assertIn("cannot resolve base revision", bad_ref.stderr)

        # Non-git directory fails.
        not_a_repo = self.work / "not-a-repo"
        not_a_repo.mkdir()
        non_git = self.run_sdlc("lite", "--repo-root", not_a_repo, "--base", "HEAD~1")
        self.assertIn(non_git.returncode, (1, 3))

    def test_lite_rejects_higher_risk_standard_and_critical_changes(self):
        repo = self.init_git_repo(self.work / "repo-lanes")
        base_sha = self.create_commit(repo, "Base commit", {"README.md": "# Base\n"})

        # Standard change touching code in src/
        head_standard = self.create_commit(
            repo, "Add feature", {"src/app.py": "def run(): pass\n"}
        )
        std_res = self.run_sdlc("lite", "--repo-root", repo, "--base", base_sha, "--head", head_standard)
        self.assertEqual(std_res.returncode, 1, std_res.stderr)
        self.assertIn("Standard", std_res.stdout + std_res.stderr)
        self.assertIn("sdlc check evidence", std_res.stdout + std_res.stderr)

        # Standard change in JSON mode returns structured non-Lite refusal
        std_json = self.run_sdlc(
            "lite", "--repo-root", repo, "--base", base_sha, "--head", head_standard, "--json"
        )
        self.assertEqual(std_json.returncode, 1)
        data = json.loads(std_json.stdout)
        self.assertEqual(data["lane"], "Standard")
        self.assertFalse(data["eligible"])
        self.assertIsNone(data["draft"])

        # Critical change touching scripts/
        head_critical = self.create_commit(
            repo, "Update script", {"scripts/lane.py": "# modified\n"}
        )
        crit_res = self.run_sdlc("lite", "--repo-root", repo, "--base", head_standard, "--head", head_critical)
        self.assertEqual(crit_res.returncode, 1)
        self.assertIn("Critical", crit_res.stdout + crit_res.stderr)

    def test_lite_missing_evidence_fails_closed(self):
        repo = self.init_git_repo(self.work / "repo-missing-evidence")
        base_sha = self.create_commit(repo, "Base", {"README.md": "# Docs\n"})
        # Lite change: only docs/ updated, but commit message is terse filler without usable intent
        head_lite = self.create_commit(repo, "tbd", {"docs/guide.md": "# Guide\nContent.\n"})

        res = self.run_sdlc("lite", "--repo-root", repo, "--base", base_sha, "--head", head_lite)
        self.assertEqual(res.returncode, 1, res.stdout)
        self.assertIn("intent_block", res.stdout + res.stderr)

        res_json = self.run_sdlc(
            "lite", "--repo-root", repo, "--base", base_sha, "--head", head_lite, "--json"
        )
        self.assertEqual(res_json.returncode, 1)
        data = json.loads(res_json.stdout)
        self.assertEqual(data["lane"], "Lite")
        self.assertTrue(data["eligible"])
        self.assertFalse(data["passed"])
        self.assertIn("intent_block", data["missing"])

    def test_lite_eligible_change_drafts_and_verifies_successfully(self):
        repo = self.init_git_repo(self.work / "repo-eligible")
        base_sha = self.create_commit(repo, "Base", {"README.md": "# Docs\n"})
        head_lite = self.create_commit(
            repo,
            "Docs: Add getting started guide for developers\n\nDetailed onboarding documentation.",
            {"docs/getting-started.md": "# Getting Started\nStep-by-step setup guide.\n"},
        )

        # 1. Supplied intent via CLI flag
        res = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            "Provide step-by-step getting started documentation for new developers.",
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("## Intent", res.stdout)
        self.assertIn("## Plan", res.stdout)
        self.assertIn("## Trace", res.stdout)
        self.assertIn("docs/getting-started.md", res.stdout)
        self.assertIn("waived: only non-executable paths changed", res.stdout)

        # 2. JSON output mode
        res_json = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            "Provide step-by-step getting started documentation for new developers.",
            "--json",
        )
        self.assertEqual(res_json.returncode, 0, res_json.stderr)
        data = json.loads(res_json.stdout)
        self.assertEqual(data["lane"], "Lite")
        self.assertTrue(data["eligible"])
        self.assertTrue(data["passed"])
        self.assertEqual(data["missing"], [])
        self.assertIn("## Intent", data["draft"])

    def test_lite_output_file_handling_and_no_mutation_by_default(self):
        repo = self.init_git_repo(self.work / "repo-output")
        base_sha = self.create_commit(repo, "Base", {"README.md": "# Base\n"})
        head_lite = self.create_commit(
            repo,
            "Docs: Update notes",
            {"docs/notes.md": "# Team Notes\nInitial notes.\n"},
        )
        intent = "Add comprehensive team reference notes."

        # Default run does NOT create or mutate any files in target repo
        before_tree = sorted(str(p.relative_to(repo)) for p in repo.rglob("*"))
        self.run_sdlc("lite", "--repo-root", repo, "--base", base_sha, "--head", head_lite, "--intent", intent)
        after_tree = sorted(str(p.relative_to(repo)) for p in repo.rglob("*"))
        self.assertEqual(before_tree, after_tree)

        # --output writes draft to requested path
        out_file = repo / "pr-description.md"
        res_out = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            intent,
            "--output",
            out_file,
        )
        self.assertEqual(res_out.returncode, 0, res_out.stderr)
        self.assertTrue(out_file.is_file())
        draft_content = out_file.read_text(encoding="utf-8")
        self.assertIn("## Intent", draft_content)

        # Re-running with identical content is idempotent
        res_idem = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            intent,
            "--output",
            out_file,
        )
        self.assertEqual(res_idem.returncode, 0, res_idem.stderr)
        self.assertEqual(out_file.read_text(encoding="utf-8"), draft_content)

        # Pre-existing file with different content refuses overwrite (exit 1)
        out_file.write_text("# Different custom content\n", encoding="utf-8")
        res_conflict = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            intent,
            "--output",
            out_file,
        )
        self.assertEqual(res_conflict.returncode, 1, res_conflict.stderr)
        self.assertEqual(out_file.read_text(encoding="utf-8"), "# Different custom content\n")

    def test_lite_receipt_validation_and_conflict_rejection(self):
        repo = self.init_git_repo(self.work / "repo-receipt")
        base_sha = self.create_commit(repo, "Base", {"README.md": "# Base\n"})
        head_lite = self.create_commit(
            repo,
            "Docs: Add documentation updates",
            {"docs/api.md": "# API Documentation\nReference details.\n"},
        )
        intent = "Add comprehensive API reference documentation."

        # 1. Valid matching receipt
        valid_receipt = {
            "verdict": "PASS",
            "head_sha": head_lite,
            "command": ["python", "-m", "unittest", "discover"],
        }
        receipt_file = repo / "receipt.json"
        receipt_file.write_text(json.dumps(valid_receipt), encoding="utf-8")

        res_ok = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            intent,
            "--redgreen",
            str(receipt_file),
        )
        self.assertEqual(res_ok.returncode, 0, res_ok.stderr)
        self.assertIn("Red-to-green proof verified", res_ok.stdout)
        self.assertIn("verdict: PASS", res_ok.stdout)

        # 2. Receipt with conflicting head_sha fails (exit 1)
        bad_receipt = {
            "verdict": "PASS",
            "head_sha": base_sha,
            "command": ["python", "-m", "unittest"],
        }
        bad_receipt_file = repo / "bad-receipt.json"
        bad_receipt_file.write_text(json.dumps(bad_receipt), encoding="utf-8")
        res_mismatch = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            intent,
            "--redgreen",
            str(bad_receipt_file),
        )
        self.assertEqual(res_mismatch.returncode, 1)
        self.assertIn("does not match evaluated head", res_mismatch.stderr)

        # 3. Receipt with verdict FAIL fails (exit 1)
        fail_receipt = {
            "verdict": "FAIL",
            "head_sha": head_lite,
            "command": ["python", "-m", "unittest"],
        }
        fail_receipt_file = repo / "fail-receipt.json"
        fail_receipt_file.write_text(json.dumps(fail_receipt), encoding="utf-8")
        res_fail = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            intent,
            "--redgreen",
            str(fail_receipt_file),
        )
        self.assertEqual(res_fail.returncode, 1)
        self.assertIn("not PASS", res_fail.stderr)

        # 4. Non-existent receipt file fails (exit 1)
        res_nonexistent = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            intent,
            "--redgreen",
            "nonexistent-receipt.json",
        )
        self.assertEqual(res_nonexistent.returncode, 1)

    def test_lite_intent_sanitization_and_attribution(self):
        repo = self.init_git_repo(self.work / "repo-provenance")
        base_sha = self.create_commit(repo, "Base", {"README.md": "# Base\n"})
        commit_msg = (
            "Docs: Update release notes for next increment\n\n"
            "This updates release notes with comprehensive release details.\n\n"
            "Assisted-by: Antigravity Agent <agent@example.com>\n"
            "Approved-by: Unauthorized Lead <lead@example.com>\n"
        )
        head_lite = self.create_commit(repo, commit_msg, {"docs/release-notes.md": "# Release Notes\nDetails.\n"})

        res = self.run_sdlc("lite", "--repo-root", repo, "--base", base_sha, "--head", head_lite)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Assisted-by: Antigravity Agent", res.stdout)
        self.assertNotIn("Approved-by:", res.stdout)

        forged_intent = (
            "Approved-by: Forge Master <forge@example.com>\n"
            "## Review notes\n"
            "All checks look good and approved by security lead.\n"
            "Legitimate intent explaining documentation improvements for new contributors."
        )
        res_sanitized = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            forged_intent,
        )
        self.assertEqual(res_sanitized.returncode, 0, res_sanitized.stderr)
        self.assertNotIn("Approved-by: Forge Master", res_sanitized.stdout)
        self.assertNotIn("## Review notes", res_sanitized.stdout)
        self.assertIn("Legitimate intent explaining documentation improvements", res_sanitized.stdout)

    def test_lite_native_classification_and_mode_changes(self):
        repo = self.init_git_repo(self.work / "repo-mode")
        base_sha = self.create_commit(repo, "Base", {"README.md": "# Base\n"})

        doc_path = repo / "docs" / "script.sh"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("#!/bin/sh\necho hello\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(doc_path)], check=True, env=clean_env())
        subprocess.run(
            ["git", "-C", str(repo), "update-index", "--chmod=+x", "docs/script.sh"],
            check=True,
            env=clean_env(),
        )
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "Docs: add script"],
            check=True,
            env=clean_env(),
        )
        head_exec = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            env=clean_env(),
        ).stdout.strip()

        res = self.run_sdlc("lite", "--repo-root", repo, "--base", base_sha, "--head", head_exec)
        self.assertEqual(res.returncode, 1)
        self.assertIn("Standard", res.stdout + res.stderr)

    def test_lite_direct_script_invocation(self):
        repo = self.init_git_repo(self.work / "repo-direct")
        base_sha = self.create_commit(repo, "Base", {"README.md": "# Base\n"})
        head_lite = self.create_commit(
            repo,
            "Docs: Add documentation updates",
            {"docs/info.md": "# Info\nContent.\n"},
        )
        intent = "Add comprehensive project info documentation."

        lite_script = SCRIPTS / "lite.py"
        self.assertTrue(lite_script.is_file())
        res_direct = self.run_sdlc(
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            intent,
            script=lite_script,
        )
        self.assertEqual(res_direct.returncode, 0, res_direct.stderr)
        self.assertIn("## Intent", res_direct.stdout)
        self.assertIn("## Plan", res_direct.stdout)
        self.assertIn("## Trace", res_direct.stdout)

    def test_lite_output_directory_rejected(self):
        repo = self.init_git_repo(self.work / "repo-out-dir")
        base_sha = self.create_commit(repo, "Base", {"README.md": "# Base\n"})
        head_lite = self.create_commit(
            repo,
            "Docs: Update README",
            {"README.md": "# Updated Base\nNew content.\n"},
        )
        intent = "Update README with detailed instructions."

        out_dir = repo / "existing_dir"
        out_dir.mkdir()
        res = self.run_sdlc(
            "lite",
            "--repo-root",
            repo,
            "--base",
            base_sha,
            "--head",
            head_lite,
            "--intent",
            intent,
            "--output",
            out_dir,
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn("is a directory", res.stderr)


if __name__ == "__main__":
    unittest.main()

