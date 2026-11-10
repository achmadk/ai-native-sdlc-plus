"""Public CLI contract tests for scripts/sdlc.py (WS3 one-front-door)."""

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


class FrontDoorContractTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = support.TemporaryDirectory(prefix="sdlc-cli-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def run_python_script(self, script_path, *args, cwd=None, stdin_text=None, env=None):
        return subprocess.run(
            [sys.executable, "-I", "-B", str(script_path)] + [str(a) for a in args],
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

    def run_sdlc(self, *args, cwd=None, stdin_text=None, env=None, script=None):
        target = Path(script or SDLC)
        self.assertTrue(target.is_file(), "expected front-door CLI at %s" % target)
        return self.run_python_script(target, *args, cwd=cwd, stdin_text=stdin_text, env=env)

    def init_git_repo(self, directory):
        repo = Path(directory)
        repo.mkdir(parents=True, exist_ok=True)
        for cmd in (
            ["init", "-q", "-b", "main"],
            ["config", "user.name", "Fixture"],
            ["config", "user.email", "fixture@example.invalid"],
            ["config", "core.autocrlf", "false"],
        ):
            subprocess.run(["git", "-C", str(repo)] + cmd, env=clean_env(), check=True, capture_output=True)
        return repo


class PublicCLIContract(FrontDoorContractTestCase):
    def test_top_level_and_subcommand_help_list_supported_operations_without_mutation(self):
        empty = self.work / "untouched"
        empty.mkdir()
        top = self.run_sdlc("--help", cwd=empty)
        self.assertEqual(top.returncode, 0, top.stderr)
        for name in ("init", "lane", "check", "doctor", "update", "uninstall", "status", "explain"):
            self.assertIn(name, top.stdout)
        self.assertNotRegex(top.stdout, r"(?m)^\s*(?:gate|lite)\b")

        check_help = self.run_sdlc("check", "--help", cwd=empty)
        self.assertEqual(check_help.returncode, 0, check_help.stderr)
        for sub in ("spec", "brief", "evidence"):
            self.assertIn(sub, check_help.stdout)

        for argv in (
            ("lane", "--help"),
            ("check", "spec", "--help"),
            ("check", "brief", "--help"),
            ("check", "evidence", "--help"),
            ("doctor", "--help"),
            ("init", "--help"),
            ("status", "--help"),
            ("update", "--help"),
            ("uninstall", "--help"),
            ("explain", "--help"),
        ):
            with self.subTest(argv=argv):
                res = self.run_sdlc(*argv, cwd=empty)
                self.assertEqual(res.returncode, 0, res.stderr)
                self.assertTrue(res.stdout.strip())
        self.assertEqual(os.listdir(empty), [], "help requests must not modify the working directory")

    def test_unknown_commands_and_unimplemented_aliases_fail_with_usage_error(self):
        empty = self.work / "untouched-errors"
        empty.mkdir()
        for argv in (
            (),
            ("gate",),
            ("lite",),
            ("arbitrary_module",),
            ("../lane",),
            ("check",),
            ("check", "gate"),
            ("check", "lite"),
            ("check", "unknown"),
        ):
            with self.subTest(argv=argv):
                res = self.run_sdlc(*argv, cwd=empty)
                self.assertEqual(res.returncode, 2, (argv, res.stdout, res.stderr))
                self.assertNotIn("Traceback", res.stderr)
                self.assertNotIn("can't open file", res.stderr)
                self.assertEqual(res.stdout.strip(), "")
                self.assertTrue(
                    "usage:" in res.stderr.lower() or "unknown" in res.stderr.lower() or "supported" in res.stderr.lower(),
                    res.stderr,
                )
        self.assertEqual(os.listdir(empty), [])

    def test_lane_delegation_preserves_flags_json_and_strict_errors(self):
        cfg = SCRIPTS / "lane-config.yaml"
        direct_json = self.run_python_script(SCRIPTS / "lane.py", "--config", cfg, "--paths", "README.md", "--json")
        self.assertEqual(direct_json.returncode, 0, direct_json.stderr)

        via_sdlc = self.run_sdlc("lane", "--config", cfg, "--paths", "README.md", "--json")
        self.assertEqual(via_sdlc.returncode, direct_json.returncode, via_sdlc.stderr)
        self.assertEqual(json.loads(via_sdlc.stdout), json.loads(direct_json.stdout))

        direct_crit = self.run_python_script(SCRIPTS / "lane.py", "--config", cfg, "--paths", "scripts/lane.py")
        via_crit = self.run_sdlc("lane", "--config", cfg, "--paths", "scripts/lane.py")
        self.assertEqual(via_crit.returncode, direct_crit.returncode)
        self.assertEqual(via_crit.stdout, direct_crit.stdout)

        missing_cfg = self.work / "missing-config.yaml"
        direct_strict = self.run_python_script(
            SCRIPTS / "lane.py", "--config", missing_cfg, "--paths", "README.md", "--strict"
        )
        self.assertEqual(direct_strict.returncode, 3)
        via_strict = self.run_sdlc("lane", "--config", missing_cfg, "--paths", "README.md", "--strict")
        self.assertEqual(via_strict.returncode, 3)
        self.assertIn("cannot read config", via_strict.stderr)

        via_bad_flag = self.run_sdlc("lane", "--not-a-valid-lane-flag")
        self.assertEqual(via_bad_flag.returncode, 2)

    def test_check_spec_and_check_brief_delegate_json_and_native_errors(self):
        valid_spec_file = self.work / "valid-spec.md"
        valid_spec_file.write_text(
            "# Spec: sample\n"
            "Lane: Standard\n"
            "Author: Dev One\n"
            "Status: approved\n"
            "Approved-by: Reviewer Two (2026-10-01)\n\n"
            "## Intent\nAdd deterministic status output.\n\n"
            "## Out of scope\n- Remote telemetry\n\n"
            "## Acceptance criteria\n"
            "- AC1: status prints JSON summary | pass: exit code 0 and valid JSON object\n\n"
            "## Constraints\n- Python >= 3.8 stdlib only\n\n"
            "## Test expectations\n"
            "- AC1 -> manual: CLI contract fixture | fails-before: command absent\n\n"
            "## Plan\nAdd status subcommand.\n",
            encoding="utf-8",
        )
        direct_spec_ok = self.run_python_script(
            SCRIPTS / "check_spec.py", valid_spec_file, "--lane", "Standard", "--repo-root", ROOT, "--json"
        )
        self.assertEqual(direct_spec_ok.returncode, 0, direct_spec_ok.stderr)
        sdlc_spec_ok = self.run_sdlc(
            "check", "spec", valid_spec_file, "--lane", "Standard", "--repo-root", ROOT, "--json"
        )
        self.assertEqual(sdlc_spec_ok.returncode, 0, sdlc_spec_ok.stderr)
        self.assertEqual(json.loads(sdlc_spec_ok.stdout), json.loads(direct_spec_ok.stdout))

        invalid_spec_file = self.work / "invalid-spec.md"
        invalid_spec_file.write_text("# Empty\n", encoding="utf-8")
        direct_spec_bad = self.run_python_script(
            SCRIPTS / "check_spec.py", invalid_spec_file, "--lane", "Standard", "--repo-root", ROOT, "--json"
        )
        self.assertEqual(direct_spec_bad.returncode, 1)
        sdlc_spec_bad = self.run_sdlc(
            "check", "spec", invalid_spec_file, "--lane", "Standard", "--repo-root", ROOT, "--json"
        )
        self.assertEqual(sdlc_spec_bad.returncode, 1)
        self.assertEqual(json.loads(sdlc_spec_bad.stdout), json.loads(direct_spec_bad.stdout))

        direct_spec_missing = self.run_python_script(SCRIPTS / "check_spec.py", self.work / "nope.md")
        self.assertEqual(direct_spec_missing.returncode, 2)
        sdlc_spec_missing = self.run_sdlc("check", "spec", self.work / "nope.md")
        self.assertEqual(sdlc_spec_missing.returncode, 2)

        valid_brief_file = self.work / "valid-brief.md"
        valid_brief_file.write_text(
            "# Context brief: sample\n\n"
            "## Decisions\n"
            "- [Spec](README.md) | deterministic CLI summary | 2026-11-01 | window 90d | trust: authoritative\n\n"
            "## Ticket criteria\n"
            "> status prints deterministic JSON summary\n"
            "source: [Spec](README.md) | 2026-11-01\n",
            encoding="utf-8",
        )
        direct_brief_ok = self.run_python_script(
            SCRIPTS / "check_brief.py",
            valid_brief_file,
            "--lane",
            "Standard",
            "--repo-root",
            ROOT,
            "--today",
            "2026-11-10",
            "--json",
        )
        self.assertEqual(direct_brief_ok.returncode, 0, direct_brief_ok.stdout + direct_brief_ok.stderr)
        sdlc_brief_ok = self.run_sdlc(
            "check",
            "brief",
            valid_brief_file,
            "--lane",
            "Standard",
            "--repo-root",
            ROOT,
            "--today",
            "2026-11-10",
            "--json",
        )
        self.assertEqual(sdlc_brief_ok.returncode, 0, sdlc_brief_ok.stdout + sdlc_brief_ok.stderr)
        self.assertEqual(json.loads(sdlc_brief_ok.stdout), json.loads(direct_brief_ok.stdout))

        invalid_brief_file = self.work / "invalid-brief.md"
        invalid_brief_file.write_text(
            "# Context brief: invalid\n\n"
            "## Ticket criteria\n"
            "- [Spec](README.md) | list item instead of quote block | 2026-11-01 | window 90d | trust: authoritative\n",
            encoding="utf-8",
        )
        direct_brief_bad = self.run_python_script(
            SCRIPTS / "check_brief.py", invalid_brief_file, "--lane", "Standard", "--repo-root", ROOT, "--json"
        )
        self.assertEqual(direct_brief_bad.returncode, 1)
        sdlc_brief_bad = self.run_sdlc(
            "check", "brief", invalid_brief_file, "--lane", "Standard", "--repo-root", ROOT, "--json"
        )
        self.assertEqual(sdlc_brief_bad.returncode, 1)
        self.assertEqual(json.loads(sdlc_brief_bad.stdout), json.loads(direct_brief_bad.stdout))

        sdlc_brief_usage = self.run_sdlc("check", "brief", valid_brief_file, "--lane", "InvalidLane")
        self.assertEqual(sdlc_brief_usage.returncode, 2)

    def test_check_evidence_delegates_ci_stdin_missing_evidence_and_manual_attestation(self):
        repo = self.init_git_repo(self.work / "repo")
        (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], env=clean_env(), check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], env=clean_env(), check=True)
        base = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], env=clean_env(), check=True, capture_output=True, text=True
        ).stdout.strip()

        (repo / "docs").mkdir()
        (repo / "docs" / "spec.md").write_text("# Spec\nReal tracked spec.\n", encoding="utf-8")
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        (repo / "tests").mkdir()
        (repo / "tests" / "test_app.py").write_text("def test_v(): assert True\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "docs/spec.md", "src/app.py", "tests/test_app.py"], env=clean_env(), check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "head"], env=clean_env(), check=True)
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], env=clean_env(), check=True, capture_output=True, text=True
        ).stdout.strip()

        cfg = SCRIPTS / "lane-config.yaml"
        common = ["--ci", "--config", cfg, "--repo-root", repo, "--base=" + base, "--head=" + head, "--pr-body-file", "-"]
        direct_ci = self.run_python_script(SCRIPTS / "evidence_check.py", *common, stdin_text="")
        self.assertEqual(direct_ci.returncode, 1)

        passing_body = (
            "Spec: docs/spec.md\n\n"
            "## Trace\nUsed deterministic test fixtures and verified behavior.\n\n"
            "## Review notes\nReviewed spec alignment and edge cases carefully.\n"
        )
        direct_ci_ok = self.run_python_script(SCRIPTS / "evidence_check.py", *common, stdin_text=passing_body)
        self.assertEqual(direct_ci_ok.returncode, 0, direct_ci_ok.stdout + direct_ci_ok.stderr)

        sdlc_ci = self.run_sdlc("check", "evidence", *common, stdin_text="")
        self.assertEqual(sdlc_ci.returncode, 1)
        self.assertEqual(sdlc_ci.stdout, direct_ci.stdout)
        self.assertIn("FAIL: missing evidence for Standard", sdlc_ci.stdout)

        sdlc_ci_ok = self.run_sdlc("check", "evidence", *common, stdin_text=passing_body)
        self.assertEqual(sdlc_ci_ok.returncode, 0, sdlc_ci_ok.stdout + sdlc_ci_ok.stderr)
        self.assertEqual(sdlc_ci_ok.stdout, direct_ci_ok.stdout)

        sdlc_attested = self.run_sdlc(
            "check", "evidence", "--lane", "Lite", "--present", "intent_block", "test_changes", "trace_block"
        )
        self.assertEqual(sdlc_attested.returncode, 0, sdlc_attested.stderr)
        self.assertIn("attested by --present, not verified", sdlc_attested.stdout)

        sdlc_ci_present = self.run_sdlc("check", "evidence", "--ci", "--present", "intent_block")
        self.assertEqual(sdlc_ci_present.returncode, 2)


class DoctorAndExplainContract(FrontDoorContractTestCase):
    def test_doctor_groups_findings_retains_raw_counts_and_respects_strict_mode(self):
        repo = self.init_git_repo(self.work / "fresh-installed")
        (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], env=clean_env(), check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "initial"], env=clean_env(), check=True)

        install_res = self.run_python_script(SCRIPTS / "install.py", repo)
        self.assertEqual(install_res.returncode, 0, install_res.stderr)

        direct = self.run_python_script(SCRIPTS / "doctor.py", "--root", repo, "--json")
        self.assertEqual(direct.returncode, 0, direct.stderr)
        direct_doc = json.loads(direct.stdout)

        grouped_json = self.run_sdlc("doctor", "--root", repo, "--json")
        self.assertEqual(grouped_json.returncode, 0, grouped_json.stderr)
        doc = json.loads(grouped_json.stdout)

        self.assertEqual(doc["version"], direct_doc["version"])
        self.assertEqual(doc["summary"], direct_doc["summary"])
        self.assertEqual(doc["failed"], direct_doc["failed"])
        self.assertEqual(doc["results"], direct_doc["results"])

        groups = doc["groups"]
        self.assertEqual(set(groups), {"blocking", "needs_human", "informational"})
        self.assertEqual(groups["blocking"], [])
        self.assertLessEqual(len(groups["needs_human"]), 3)
        self.assertEqual(
            doc["action_counts"],
            {
                "blocking": 0,
                "needs_human": len(groups["needs_human"]),
                "informational": len(groups["informational"]),
            },
        )

        # Every non-verified finding in raw results must appear verbatim in exactly one action group.
        expected_non_ok = [item for item in direct_doc["results"] if item["status"] != "verified"]
        observed_grouped = [
            finding
            for bucket in ("blocking", "needs_human", "informational")
            for group in groups[bucket]
            for finding in group["findings"]
        ]
        self.assertCountEqual(observed_grouped, expected_non_ok)

        for group in groups["informational"]:
            for finding in group["findings"]:
                if finding["status"] != "info":
                    self.assertTrue(group["optional"], group)

        grouped_text = self.run_sdlc("doctor", "--root", repo)
        self.assertEqual(grouped_text.returncode, 0, grouped_text.stderr)
        self.assertIn("needs_human", grouped_text.stdout)
        self.assertIn("informational", grouped_text.stdout)
        for item in direct_doc["results"]:
            self.assertIn(item["name"], grouped_text.stdout)
            self.assertIn(item["status"], grouped_text.stdout)

        strict_res = self.run_sdlc("doctor", "--root", repo, "--strict", "--json")
        self.assertEqual(strict_res.returncode, 1)
        strict_doc = json.loads(strict_res.stdout)
        self.assertTrue(strict_doc["failed"])
        strict_blocking_names = {
            finding["name"]
            for group in strict_doc["groups"]["blocking"]
            for finding in group["findings"]
        }
        expected_warns = {item["name"] for item in direct_doc["results"] if item["status"] == "WARN"}
        self.assertTrue(expected_warns.issubset(strict_blocking_names))
        for bucket in ("needs_human", "informational"):
            for group in strict_doc["groups"][bucket]:
                for finding in group["findings"]:
                    self.assertNotEqual(finding["status"], "WARN")

    def test_doctor_real_failure_unknown_checks_and_argument_validation(self):
        repo = self.init_git_repo(self.work / "broken-repo")
        install_res = self.run_python_script(SCRIPTS / "install.py", repo)
        self.assertEqual(install_res.returncode, 0, install_res.stderr)
        os.remove(repo / "scripts" / "lane-config.yaml")

        broken = self.run_sdlc("doctor", "--root", repo, "--json")
        self.assertEqual(broken.returncode, 1)
        broken_doc = json.loads(broken.stdout)
        self.assertTrue(broken_doc["failed"])
        blocking_findings = [
            finding
            for group in broken_doc["groups"]["blocking"]
            for finding in group["findings"]
        ]
        self.assertTrue(any(f["name"] == "config" and f["status"] == "FAIL" for f in blocking_findings))

        bad_enf = self.run_sdlc("doctor", "--root", repo, "--require-enforcement")
        self.assertEqual(bad_enf.returncode, 2)
        bad_root = self.run_sdlc("doctor", "--root", self.work / "does-not-exist")
        self.assertEqual(bad_root.returncode, 2)

        import importlib.util

        spec = importlib.util.spec_from_file_location("_test_sdlc_mod", SDLC)
        sdlc_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sdlc_mod)

        hostile_root = str(self.work / "space dir; $(whoami) & echo pwned")
        synthetic = [
            ("custom-alpha", "WARN", "first unknown warning"),
            ("custom-beta", "unverified", "second unknown check"),
            ("mystery-blocker", "FAIL", "unexpected failure"),
        ]
        grouped = sdlc_mod.group_doctor_results(synthetic, root_arg=hostile_root, strict=False)
        self.assertEqual(len(grouped["blocking"]), 1)
        self.assertEqual(grouped["blocking"][0]["findings"][0]["name"], "mystery-blocker")
        nh_ids = [g["group_id"] for g in grouped["needs_human"]]
        self.assertEqual(nh_ids, ["unknown:custom-alpha", "unknown:custom-beta"])
        for g in grouped["needs_human"] + grouped["blocking"]:
            self.assertIn(hostile_root, g["next_command_argv"])
            # Hostile root must be shell-quoted as a single token in the display string.
            self.assertTrue(
                "'" in g["next_command"] or '"' in g["next_command"],
                g["next_command"],
            )

    def test_explain_describes_evidence_limitation_and_safe_next_step_without_mutation(self):
        absent_root = self.work / "never-created"
        for check_id in (
            "codeowners",
            "gate-files-committed",
            "hook-active",
            "rule-dead-critical",
            "ci-invokes-gate",
            "scanner-invokes-gate",
            "enforcement-readiness",
            "enforcement-bypass",
        ):
            with self.subTest(check_id=check_id):
                res = self.run_sdlc("explain", check_id, "--root", absent_root, "--json")
                self.assertEqual(res.returncode, 0, res.stderr)
                payload = json.loads(res.stdout)
                self.assertEqual(payload["check_id"], check_id)
                self.assertTrue(payload["evidence"].strip())
                self.assertTrue(payload["limitation"].strip())
                self.assertIn(payload["command_kind"], ("remediation", "inspection", "discovery"))
                self.assertIsInstance(payload["next_command_argv"], list)
                self.assertTrue(payload["next_command"].strip())
                self.assertFalse(absent_root.exists(), "explain must never create or mutate files")
                if check_id == "codeowners":
                    self.assertEqual(payload["command_kind"], "discovery")

        text_res = self.run_sdlc("explain", "enforcement-readiness", "--root", absent_root)
        self.assertEqual(text_res.returncode, 0, text_res.stderr)
        self.assertIn("Evidence:", text_res.stdout)
        self.assertIn("Limitation:", text_res.stdout)
        self.assertIn("Next step", text_res.stdout)
        self.assertFalse(absent_root.exists())

        for unknown in ("not-a-check", "ci-nonexistent", "scanner-fake", "enforcement-fake"):
            with self.subTest(unknown=unknown):
                bad = self.run_sdlc("explain", unknown, "--root", absent_root)
                self.assertEqual(bad.returncode, 2)
                self.assertFalse(absent_root.exists())


class RuntimeIsolationContract(FrontDoorContractTestCase):
    def _create_installed_runtime(self, directory):
        dest = Path(directory)
        res = self.run_python_script(SCRIPTS / "install.py", dest)
        self.assertEqual(res.returncode, 0, res.stderr)
        # Copy scripts/sdlc.py into the installed tree (manifest integration lands in Task 4.5).
        import shutil

        shutil.copy2(SDLC, dest / "scripts" / "sdlc.py")
        return dest

    def test_unrelated_cwd_and_hostile_target_never_execute_target_or_cwd_code(self):
        installed_rt = self._create_installed_runtime(self.work / "installed-runtime")
        hostile_cwd = self.work / "hostile-cwd"
        hostile_cwd.mkdir()
        marker = self.work / "poison_triggered.txt"
        poison_py = (
            "import pathlib, sys\n"
            "pathlib.Path(%r).write_text('triggered', encoding='utf-8')\n"
            "raise SystemExit('POISON_CODE_EXECUTED')\n" % str(marker)
        )
        for name in ("lane.py", "doctor.py", "evidence_check.py", "check_spec.py", "check_brief.py"):
            (hostile_cwd / name).write_text(poison_py, encoding="utf-8")
            (hostile_cwd / "scripts").mkdir(exist_ok=True)
            (hostile_cwd / "scripts" / name).write_text(poison_py, encoding="utf-8")
        (hostile_cwd / "scanner-profiles.json").write_text("{broken", encoding="utf-8")
        (hostile_cwd / "scripts" / "scanner-profiles.json").write_text("{broken", encoding="utf-8")

        hostile_repo = self.init_git_repo(self.work / "hostile-repo")
        install_base = self.run_python_script(SCRIPTS / "install.py", hostile_repo)
        self.assertEqual(install_base.returncode, 0, install_base.stderr)
        (hostile_repo / "README.md").write_text("# Base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(hostile_repo), "add", "."], env=clean_env(), check=True)
        subprocess.run(["git", "-C", str(hostile_repo), "commit", "-q", "-m", "base"], env=clean_env(), check=True)
        base_sha = subprocess.run(
            ["git", "-C", str(hostile_repo), "rev-parse", "HEAD"],
            env=clean_env(),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Poison both root and scripts/ in the candidate revision of hostile_repo.
        for name in ("lane.py", "doctor.py", "evidence_check.py", "check_spec.py", "check_brief.py"):
            (hostile_repo / name).write_text(poison_py, encoding="utf-8")
            (hostile_repo / "scripts" / name).write_text(poison_py, encoding="utf-8")
        (hostile_repo / "scripts" / "scanner-profiles.json").write_text("{broken", encoding="utf-8")
        subprocess.run(["git", "-C", str(hostile_repo), "add", "."], env=clean_env(), check=True)
        subprocess.run(["git", "-C", str(hostile_repo), "commit", "-q", "-m", "poison-head"], env=clean_env(), check=True)
        head_sha = subprocess.run(
            ["git", "-C", str(hostile_repo), "rev-parse", "HEAD"],
            env=clean_env(),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        for label, rt_root in (("source", ROOT), ("installed", installed_rt)):
            sdlc_entry = rt_root / "scripts" / "sdlc.py"
            trusted_cfg = rt_root / "scripts" / "lane-config.yaml"
            with self.subTest(runtime=label):
                lane_res = self.run_sdlc(
                    "lane",
                    "--config",
                    trusted_cfg,
                    "--repo-root",
                    hostile_repo,
                    "--base=" + base_sha,
                    "--head=" + head_sha,
                    "--json",
                    cwd=hostile_cwd,
                    env={"PYTHONPATH": str(hostile_cwd) + os.pathsep + str(hostile_repo / "scripts")},
                    script=sdlc_entry,
                )
                self.assertEqual(lane_res.returncode, 0, lane_res.stderr)
                self.assertEqual(json.loads(lane_res.stdout)["lane"], "Critical")

                ev_res = self.run_sdlc(
                    "check",
                    "evidence",
                    "--ci",
                    "--config",
                    trusted_cfg,
                    "--repo-root",
                    hostile_repo,
                    "--base=" + base_sha,
                    "--head=" + head_sha,
                    "--pr-body-file",
                    "-",
                    cwd=hostile_cwd,
                    stdin_text="",
                    env={"PYTHONPATH": str(hostile_cwd) + os.pathsep + str(hostile_repo)},
                    script=sdlc_entry,
                )
                self.assertEqual(ev_res.returncode, 1)
                self.assertIn("FAIL: missing evidence for Critical", ev_res.stdout)

                doc_res = self.run_sdlc(
                    "doctor",
                    "--root",
                    hostile_repo,
                    "--json",
                    cwd=hostile_cwd,
                    env={"PYTHONPATH": str(hostile_cwd) + os.pathsep + str(hostile_repo / "scripts")},
                    script=sdlc_entry,
                )
                self.assertEqual(doc_res.returncode, 0, doc_res.stderr)
                doc_payload = json.loads(doc_res.stdout)
                drift = [r for r in doc_payload["results"] if r["name"] == "script-drift"]
                self.assertEqual(len(drift), 1)
                self.assertEqual(drift[0]["status"], "WARN")

                exp_res = self.run_sdlc(
                    "explain",
                    "script-drift",
                    "--root",
                    hostile_repo,
                    "--json",
                    cwd=hostile_cwd,
                    script=sdlc_entry,
                )
                self.assertEqual(exp_res.returncode, 0, exp_res.stderr)

                non_isolated = subprocess.run(
                    [sys.executable, "-B", str(sdlc_entry), "doctor", "--root", str(hostile_repo), "--json"],
                    cwd=str(hostile_cwd),
                    env=clean_env(PYTHONPATH=str(hostile_cwd) + os.pathsep + str(hostile_repo / "scripts")),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(non_isolated.returncode, 0, non_isolated.stderr)
                self.assertFalse(marker.exists(), "poison code must never be imported or executed")

    def test_missing_owned_runtime_components_fail_nonzero_without_fallback(self):
        hostile_cwd = self.work / "fallback-trap"
        hostile_cwd.mkdir()
        import shutil

        # Even if valid-looking helpers exist in CWD/target, an incomplete runtime must fail closed (exit 3).
        shutil.copytree(SCRIPTS, hostile_cwd / "scripts")

        cases = (
            ("scripts/lane.py", ("lane", "--paths", "README.md")),
            ("scripts/lane.py", ("check", "evidence", "--lane", "Lite", "--present", "intent_block")),
            ("scripts/scanner-profiles.json", ("doctor", "--root", str(hostile_cwd))),
            ("skills/spec-first/scripts/check_spec.py", ("check", "spec", str(hostile_cwd / "nope.md"))),
            ("skills/context-pack/scripts/check_brief.py", ("check", "brief", str(hostile_cwd / "nope.md"))),
        )
        for index, (missing_rel, argv) in enumerate(cases):
            with self.subTest(missing=missing_rel, argv=argv):
                broken_rt = self._create_installed_runtime(self.work / ("broken-rt-%d" % index))
                os.remove(broken_rt / Path(missing_rel))
                res = self.run_sdlc(*argv, cwd=hostile_cwd, script=broken_rt / "scripts" / "sdlc.py")
                self.assertEqual(res.returncode, 3, (res.stdout, res.stderr))
                self.assertIn("missing required runtime component: " + missing_rel, res.stderr)

    def test_legacy_installer_and_checker_entrypoints_retain_contracts(self):
        target_py = self.init_git_repo(self.work / "legacy-py")
        py_res = self.run_python_script(SCRIPTS / "install.py", target_py)
        self.assertEqual(py_res.returncode, 0, py_res.stderr)
        self.assertTrue((target_py / ".sdlc-install.json").is_file())

        sh_bin = support.find_shell()
        if sh_bin:
            target_sh = self.init_git_repo(self.work / "legacy-sh")
            sh_env = clean_env()
            if os.name == "nt":
                sh_env["PATH"] = os.path.dirname(sh_bin) + os.pathsep + sh_env.get("PATH", "")
            sh_res = subprocess.run(
                [sh_bin, str(ROOT / "install.sh"), str(target_sh)],
                cwd=str(self.work),
                env=sh_env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(sh_res.returncode, 0, sh_res.stdout + sh_res.stderr)
            self.assertTrue((target_sh / ".sdlc-install.json").is_file())

        import shutil

        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if pwsh:
            target_ps = self.init_git_repo(self.work / "legacy-ps")
            ps_res = subprocess.run(
                [pwsh, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install.ps1"), "-Root", str(target_ps)],
                cwd=str(self.work),
                env=clean_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(ps_res.returncode, 0, ps_res.stdout + ps_res.stderr)
            self.assertTrue((target_ps / ".sdlc-install.json").is_file())

        doc_legacy = self.run_python_script(SCRIPTS / "doctor.py", "--root", target_py, "--json")
        self.assertEqual(doc_legacy.returncode, 0, doc_legacy.stderr)
        doc_json = json.loads(doc_legacy.stdout)
        self.assertEqual(set(doc_json), {"version", "summary", "failed", "results"})


class EmptyRepoSetupAndSubsequentLiteGateContract(FrontDoorContractTestCase):
    """Task 6.1: fresh empty-repo setup -> doctor (0 FAIL, <=3 needs_human) -> Critical bootstrap -> subsequent Lite gate."""

    def test_fresh_empty_repo_reaches_passing_local_lite_gate_after_bootstrap(self):
        repo = self.init_git_repo(self.work / "fresh-empty-repo")
        (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True, env=clean_env())
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "Initial README"], check=True, env=clean_env())

        # 1. Initialize via front door.
        init_res = self.run_sdlc("init", "--root", repo, "--json")
        self.assertEqual(init_res.returncode, 0, init_res.stderr)
        init_json = json.loads(init_res.stdout)
        self.assertEqual(init_json["setup_mode"], "core-only")
        self.assertEqual(init_json["policy"]["action"], "create-starter")

        # 2. Run grouped doctor via front door: 0 FAIL, 0 blocking, <= 3 needs_human groups.
        doc_res = self.run_sdlc("doctor", "--root", repo, "--json")
        self.assertEqual(doc_res.returncode, 0, doc_res.stderr)
        doc_json = json.loads(doc_res.stdout)
        self.assertEqual(doc_json["summary"]["FAIL"], 0)
        self.assertEqual(doc_json["action_counts"]["blocking"], 0)
        self.assertLessEqual(doc_json["action_counts"]["needs_human"], 3)
        nh_ids = [g["group_id"] for g in doc_json["groups"]["needs_human"]]
        self.assertEqual(
            nh_ids,
            ["define-codeowners", "bootstrap-default-branch", "activate-hosted-enforcement"],
        )

        # 3. Bootstrap commit is Critical setup, never labeled Lite.
        installed_sdlc = repo / "scripts" / "sdlc.py"
        boot_lane = self.run_sdlc(
            "lane",
            "--repo-root",
            repo,
            "--config",
            repo / "scripts" / "lane-config.yaml",
            "--paths",
            "scripts/sdlc.py",
            "AGENTS.md",
            ".sdlc-install.json",
            script=installed_sdlc,
        )
        self.assertEqual(boot_lane.returncode, 0, boot_lane.stderr)
        self.assertTrue(boot_lane.stdout.startswith("Critical:"), boot_lane.stdout)

        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=clean_env())
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "Bootstrap SDLC runtime (Critical setup)"],
            check=True,
            env=clean_env(),
        )
        base_sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            env=clean_env(),
        ).stdout.strip()

        # 4. Subsequent genuine Lite change on a branch touching only docs/onboarding-note.md.
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "docs/lite-note"], check=True, env=clean_env())
        note_path = repo / "docs" / "onboarding-note.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text("# Team Onboarding Note\n\nDocumenting local SDLC front-door workflow.\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "docs/onboarding-note.md"], check=True, env=clean_env())
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "Add team onboarding note"],
            check=True,
            env=clean_env(),
        )
        head_sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            env=clean_env(),
        ).stdout.strip()

        lite_lane = self.run_sdlc(
            "lane",
            "--repo-root",
            repo,
            "--config",
            repo / "scripts" / "lane-config.yaml",
            "--base",
            base_sha,
            "--head",
            head_sha,
            "--strict",
            script=installed_sdlc,
        )
        self.assertEqual(lite_lane.returncode, 0, lite_lane.stderr)
        self.assertEqual(lite_lane.stdout.strip(), "Lite: matched Lite rule docs/**")

        lite_pr_body = (
            "## Intent\n"
            "Add a concise team onboarding note under docs/ explaining how to run the local SDLC front door.\n\n"
            "## Trace\n"
            "### Change\n"
            "Added docs/onboarding-note.md.\n\n"
            "### Why\n"
            "Give contributors a quick reference for local verification commands.\n\n"
            "### Alternatives rejected\n"
            "Modifying README.md directly when a dedicated docs/ note keeps root docs focused.\n\n"
            "### Test evidence\n"
            "Non-executable documentation change under docs/** verified via sdlc check evidence --ci.\n\n"
            "### Risk accepted\n"
            "Documentation-only prose update; no runtime behavior changed.\n\n"
            "### Provenance\n"
            "Assisted-by: fixture-author (human-reviewed)\n"
        )
        gate_res = self.run_sdlc(
            "check",
            "evidence",
            "--ci",
            "--repo-root",
            repo,
            "--config",
            repo / "scripts" / "lane-config.yaml",
            "--base",
            base_sha,
            "--head",
            head_sha,
            "--pr-body-file",
            "-",
            stdin_text=lite_pr_body,
            script=installed_sdlc,
        )
        self.assertEqual(gate_res.returncode, 0, gate_res.stdout + gate_res.stderr)
        self.assertIn("evidence ok for Lite", gate_res.stdout)
        self.assertIn("waived: only non-executable paths changed", gate_res.stdout)


if __name__ == "__main__":
    unittest.main()
