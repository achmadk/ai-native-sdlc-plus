import base64
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import quote

if __package__:
    from . import support
else:
    import support

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import doctor  # noqa: E402

COPIED = ("scripts/lane.py", "scripts/evidence_check.py", "scripts/lane-config.yaml",
          ".github/workflows/sdlc-gate.yml", ".github/pull_request_template.md")
PINNED = "0123456789abcdef0123456789abcdef01234567"


def slurp(path):
    with open(path) as handle:
        return handle.read()


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = doctor.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class Install(unittest.TestCase):
    """A committed, correct install in a temp git repo."""

    workspace_parent = None

    def setUp(self):
        self.workspace = tempfile.mkdtemp(dir=self.workspace_parent)
        self.addCleanup(support.remove_tree, self.workspace)
        self.repo = os.path.join(self.workspace, "repo")
        for rel in COPIED:
            self.put(rel, Path(ROOT, rel).read_bytes())
        self.put("hooks/pre-push.sh", slurp(os.path.join(ROOT, "hooks/pre-push.sh")), executable=True)
        self.put("hooks/pre-push", slurp(os.path.join(ROOT, "hooks/pre-push")), executable=True)
        self.put("src/app.py", "x = 1\n")
        self.put("docs/a.md", "doc\n")
        self.g("init", "-q", "-b", "main")
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "init")

    def g(self, *args):
        proc = subprocess.run(["git", "-C", self.repo, "-c", "user.email=t@t", "-c", "user.name=t"] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return proc.stdout.decode()

    def put(self, rel, text, executable=False):
        full = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(text.encode("utf-8") if isinstance(text, str) else text)
        if executable:
            os.chmod(full, os.stat(full).st_mode | stat.S_IXUSR)

    def results(self, **kw):
        return doctor.check_repo(self.repo, **kw)

    def get(self, name, **kw):
        found = [(s, d) for n, s, d in self.results(**kw) if n == name]
        self.assertTrue(found, "no result named %s in %s" % (name, [n for n, _, _ in self.results(**kw)]))
        return found[0]

    def status(self, name, **kw):
        return self.get(name, **kw)[0]

    def statuses(self, name):
        return [s for n, s, _ in self.results() if n == name]


class Basics(Install):
    def test_shipped_source_has_no_doctor_failures(self):
        code, out, err = run_main(["--root", ROOT, "--json"])
        report = json.loads(out)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(report["summary"][doctor.FAIL], 0)
        self.assertEqual([row["status"] for row in report["results"]
                          if row["name"] == "scanner-invokes-gate"], [doctor.OK])

    def test_correct_install_has_no_failures_and_exits_zero(self):
        results = self.results()
        self.assertEqual([r for r in results if r[1] == doctor.FAIL], [])
        code, out, _ = run_main(["--root", self.repo])
        self.assertEqual(code, 0, out)
        self.assertIn("summary:", out)

    def test_config_is_verified_by_parsing_not_by_existing(self):
        # Regression: the old doctor said "config: verified" for any file that merely existed.
        self.put("scripts/lane-config.yaml", 'version: 1\ncritcal:\n  - "auth/**"\n')
        self.assertEqual(self.status("config"), doctor.OK)              # file is there
        status, detail = self.get("config-valid")
        self.assertEqual(status, doctor.FAIL)                            # but it is invalid
        self.assertIn("unknown key", detail)
        self.assertEqual(run_main(["--root", self.repo])[0], 1)

    def test_missing_core_files_fail_not_unverified(self):
        # Regression: a missing file used to be labelled "unverified".
        for name, rel in (("config", "scripts/lane-config.yaml"), ("ci-template", ".github/workflows/sdlc-gate.yml"),
                          ("lane-script", "scripts/lane.py"), ("evidence-script", "scripts/evidence_check.py")):
            full = os.path.join(self.repo, rel)
            saved = slurp(full)
            os.remove(full)
            self.assertEqual(self.status(name), doctor.FAIL, name)
            self.assertEqual(run_main(["--root", self.repo])[0], 1, name)
            self.put(rel, saved)

    def test_missing_advisory_files_warn_but_do_not_fail(self):
        for name, rel in (("hook-template", "hooks/pre-push.sh"), ("pr-template", ".github/pull_request_template.md")):
            os.remove(os.path.join(self.repo, rel))
            self.assertEqual(self.status(name), doctor.WARN, name)
        self.assertEqual(run_main(["--root", self.repo])[0], 0)

    def test_nonexistent_root_is_a_usage_error(self):
        code, _, err = run_main(["--root", "/nonexistent/xyz"])
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)

    def test_strict_turns_warnings_into_failures(self):
        self.assertIn(doctor.WARN, [s for _, s, _ in self.results()])
        self.assertEqual(run_main(["--root", self.repo])[0], 0)
        self.assertEqual(run_main(["--root", self.repo, "--strict"])[0], 1)

    def test_json_output_is_pure_json(self):
        code, out, _ = run_main(["--root", self.repo, "--json"])
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["version"], doctor.VERSION)
        self.assertTrue(all({"name", "status", "detail"} <= set(r) for r in data["results"]))

    def test_unmerged_branch_protection_is_always_unverified_by_default(self):
        self.assertEqual(self.status("required-check"), doctor.UNVERIFIED)

    def test_doctor_does_not_modify_the_repo_it_inspects(self):
        before = sorted(os.path.join(d, f) for d, _, fs in os.walk(self.repo) if ".git" not in d.split(os.sep) for f in fs)
        run_main(["--root", self.repo])
        after = sorted(os.path.join(d, f) for d, _, fs in os.walk(self.repo) if ".git" not in d.split(os.sep) for f in fs)
        self.assertEqual(before, after)
        self.assertEqual(self.g("status", "--porcelain").strip(), "")

    def test_doctor_never_executes_the_repos_own_scripts(self):
        marker = os.path.join(self.repo, "PWNED")
        self.put("scripts/lane.py", "open(%r, 'w').write('x')\n" % marker)
        self.put("scripts/evidence_check.py", "open(%r, 'w').write('x')\n" % marker)
        run_main(["--root", self.repo])
        self.assertFalse(os.path.exists(marker))

    def test_running_from_the_repos_own_scripts_dir_skips_the_comparison(self):
        by_name = {n: (s, d) for n, s, d in doctor.check_repo(ROOT)}
        self.assertEqual(by_name["script-drift"][0], doctor.OK)
        self.assertIn("nothing to compare", by_name["script-drift"][1])

    def test_doctor_disables_bytecode_writing_before_importing_anything(self):
        self.assertTrue(sys.dont_write_bytecode)

    def test_script_drift_is_reported(self):
        self.assertEqual(self.status("script-drift"), doctor.OK)
        self.put("scripts/lane.py", slurp(os.path.join(ROOT, "scripts/lane.py")) + "\n# local edit\n")
        status, detail = self.get("script-drift")
        self.assertEqual(status, doctor.WARN)
        self.assertIn("lane.py", detail)

    def test_not_a_git_repo_is_unverified_not_a_crash(self):
        plain = tempfile.mkdtemp(dir=self.workspace)
        for rel in COPIED:
            dest = os.path.join(plain, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(os.path.join(ROOT, rel), dest)
        os.makedirs(os.path.join(plain, "hooks"))
        with open(os.path.join(plain, "hooks", "pre-push.sh"), "w") as handle:
            handle.write("#!/bin/sh\n")
        by_name = {n: (s, d) for n, s, d in doctor.check_repo(plain)}
        for name in ("rule-coverage", "hook-active", "tooling-on-default-branch"):
            self.assertEqual(by_name[name][0], doctor.UNVERIFIED, name)
        self.assertIn("not a git work tree", by_name["hook-active"][1])
        self.assertIn("not a git work tree", by_name["tooling-on-default-branch"][1])
        self.assertNotIn("shallow-clone", by_name)


class ConfigChecks(Install):
    def cfg(self, text):
        self.put("scripts/lane-config.yaml", text)

    def test_no_critical_rules_warns(self):
        self.cfg('version: 1\nlite:\n  - "docs/**"\n')
        self.assertEqual(self.status("config-critical"), doctor.WARN)

    def test_catch_all_rules_warn(self):
        self.cfg('version: 1\ncritical:\n  - "auth/**"\nlite:\n  - "**"\n')
        status, detail = self.get("config-catch-all")
        self.assertEqual(status, doctor.WARN)
        self.assertIn("safe default", detail)
        self.cfg('version: 1\ncritical:\n  - "**"\n')
        self.assertIn("alert fatigue", self.get("config-catch-all")[1])

    def test_markdown_as_non_executable_warns(self):
        self.cfg('version: 1\ncritical:\n  - "auth/**"\nnon_executable:\n  - "*.md"\n')
        self.assertEqual(self.status("config-non-executable"), doctor.WARN)

    def test_builtin_protection_canary(self):
        self.assertEqual(self.status("builtin-protection"), doctor.OK)
        with mock.patch.object(doctor.lanelib, "classify", return_value=("Lite", "x")):
            self.assertEqual(self.status("builtin-protection"), doctor.FAIL)

    def test_dead_critical_rule_is_reported(self):
        self.cfg('version: 1\ncritical:\n  - "auth/**"\n  - "src/**"\nstandard:\n  - "docs/**"\n')
        status, detail = self.get("rule-dead-critical")
        self.assertEqual(status, doctor.WARN)
        self.assertIn("auth/**", detail)
        self.assertNotIn("src/**", detail)

    def test_critical_share_warns_above_threshold(self):
        for i in range(30):
            self.put("auth/f%d.py" % i, "x\n")
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "more")
        self.cfg('version: 1\ncritical:\n  - "auth/**"\n')
        status, detail = self.get("rule-critical-share")
        self.assertEqual(status, doctor.WARN)
        self.assertIn("%", detail)

    def test_small_repos_never_get_a_critical_share_warning(self):
        # The fixture repo has few files and a high Critical share; below the minimum it must stay quiet.
        self.assertEqual(self.statuses("rule-critical-share"), [])

    def test_coverage_info_line_counts_files(self):
        status, detail = self.get("rule-coverage")
        self.assertEqual(status, doctor.INFO)
        self.assertIn("tracked files", detail)


class WorkflowChecks(Install):
    def wf(self):
        return slurp(os.path.join(self.repo, ".github/workflows/sdlc-gate.yml"))

    def edit(self, old, new):
        text = self.wf()
        if old.startswith("python3 ") and old not in text:
            old, new = old.replace("python3 ", "python3 -I ", 1), new.replace("python3 ", "python3 -I ", 1)
        self.assertIn(old, text)
        self.put(".github/workflows/sdlc-gate.yml", text.replace(old, new))

    def test_shipped_workflow_has_no_failures_and_trusts_base_tooling(self):
        for name in ("ci-no-pr-target", "ci-trigger", "ci-edited-trigger", "ci-invokes-gate", "ci-fetch-depth",
                     "ci-trusted-tooling", "ci-permissions", "ci-persist-credentials",
                     "ci-manifest-artifact"):
            self.assertEqual(self.status(name), doctor.OK, name)

    def test_pull_request_target_is_a_failure(self):
        self.edit("on:\n  pull_request:", "on:\n  pull_request_target:")
        self.assertEqual(self.status("ci-no-pr-target"), doctor.FAIL)
        self.assertEqual(self.status("ci-trigger"), doctor.FAIL)

    def test_comments_do_not_count(self):
        self.put(".github/workflows/sdlc-gate.yml", "# never use pull_request_target\n" + self.wf())
        self.assertEqual(self.status("ci-no-pr-target"), doctor.OK)

    def test_shallow_checkout_is_a_failure(self):
        self.edit("fetch-depth: 0", "fetch-depth: 1")
        self.assertEqual(self.status("ci-fetch-depth"), doctor.FAIL)

    def test_running_the_prs_own_copy_is_a_warning(self):
        self.edit("python3 trusted/scripts/evidence_check.py", "python3 change/scripts/evidence_check.py")
        self.assertEqual(self.status("ci-trusted-tooling"), doctor.WARN)

    def test_running_unprefixed_scripts_is_a_warning(self):
        self.edit("python3 trusted/scripts/evidence_check.py", "python3 scripts/evidence_check.py")
        self.assertEqual(self.status("ci-trusted-tooling"), doctor.WARN)

    def test_missing_ci_flag_or_base_fails(self):
        self.edit("evidence_check.py --ci", "evidence_check.py")
        self.assertEqual(self.status("ci-invokes-gate"), doctor.FAIL)

    def test_missing_edited_trigger_and_permissions_warn(self):
        self.edit("edited, ", "")
        self.assertEqual(self.status("ci-edited-trigger"), doctor.WARN)
        self.edit("permissions:\n  contents: read\n", "")
        self.assertEqual(self.status("ci-permissions"), doctor.WARN)

    def test_persist_credentials_warns_when_absent(self):
        self.edit("          persist-credentials: false\n", "")
        self.assertEqual(self.status("ci-persist-credentials"), doctor.WARN)

    def test_unpinned_actions_warn_once_each_and_pinned_pass(self):
        import re
        self.put(".github/workflows/sdlc-gate.yml", re.sub(r"actions/checkout@[\w.]+", "actions/checkout@v6", self.wf()))
        status, detail = self.get("ci-pinned-actions")
        self.assertEqual(status, doctor.WARN)
        self.assertEqual(detail.count("actions/checkout@v6"), 1)
        text = self.wf()
        self.put(".github/workflows/sdlc-gate.yml", re.sub(r"actions/checkout@v6", "actions/checkout@" + PINNED, text))
        self.assertEqual(self.status("ci-pinned-actions"), doctor.OK)


class HookChecks(Install):
    def test_nothing_runs_until_git_is_pointed_at_the_hook(self):
        status, detail = self.get("hook-active")
        self.assertEqual(status, doctor.WARN)
        self.assertIn(".git/hooks/pre-push", detail)

    def test_hookspath_with_the_dispatcher_is_active(self):
        self.g("config", "core.hooksPath", "hooks")
        status, detail = self.get("hook-active")
        self.assertEqual(status, doctor.OK)
        self.assertIn(os.path.join("hooks", "pre-push"), detail)

    def test_hookspath_with_only_the_dot_sh_file_is_NOT_active(self):
        # Regression: doctor once said "verified" here. Git only runs a file named exactly "pre-push".
        os.remove(os.path.join(self.repo, "hooks/pre-push"))
        self.g("config", "core.hooksPath", "hooks")
        status, detail = self.get("hook-active")
        self.assertEqual(status, doctor.WARN)
        self.assertIn("exactly 'pre-push'", detail)

    def test_non_executable_hook_warns(self):
        support.require_executable_bits()
        self.g("config", "core.hooksPath", "hooks")
        os.chmod(os.path.join(self.repo, "hooks/pre-push"), 0o644)
        status, detail = self.get("hook-active")
        self.assertEqual(status, doctor.WARN)
        self.assertIn("chmod +x", detail)

    def test_copy_into_git_hooks_counts(self):
        dest = os.path.join(self.repo, ".git", "hooks", "pre-push")
        shutil.copy(os.path.join(self.repo, "hooks/pre-push.sh"), dest)
        os.chmod(dest, 0o755)
        self.assertEqual(self.status("hook-active"), doctor.OK)

    def test_someone_elses_hook_is_not_reported_as_ours(self):
        dest = os.path.join(self.repo, ".git", "hooks", "pre-push")
        with open(dest, "w") as handle:
            handle.write("#!/bin/sh\nnpm test\n")
        os.chmod(dest, 0o755)
        status, detail = self.get("hook-active")
        self.assertEqual(status, doctor.WARN)
        self.assertIn("not the sdlc hook", detail)

    def test_no_hook_file_means_no_hook_result(self):
        os.remove(os.path.join(self.repo, "hooks/pre-push.sh"))
        self.assertEqual(self.statuses("hook-active"), [])


class HookPathReporting(unittest.TestCase):
    def inspect_hook(self, exists, executable, text, formatter_error=None, root=None, target=None):
        root = root or os.path.abspath("repo with spaces")
        target = target or os.path.abspath(os.path.join("shared hooks", "pre-push"))
        template = os.path.join(root, "hooks", "pre-push.sh")
        with mock.patch.object(doctor, "in_git", return_value=True), \
                mock.patch.object(doctor, "git", return_value=(0, target, "")) as lookup, \
                mock.patch.object(doctor.os.path, "isfile",
                                  side_effect=lambda path: path == template or (path == target and exists)) as isfile, \
                mock.patch.object(doctor.os, "access", return_value=executable) as access, \
                mock.patch.object(doctor, "read_text", return_value=text) as read, \
                mock.patch.object(doctor.os.path, "relpath", wraps=os.path.relpath,
                                  side_effect=formatter_error) as relative:
            try:
                rows = doctor.check_hook(root)
            except ValueError as exc:
                self.fail("hook-path display must not interrupt inspection: %s" % exc)
            lookup.assert_called_once_with(root, "rev-parse", "--git-path", "hooks/pre-push")
            relative.assert_called_once_with(target, root)
            isfile.assert_any_call(target)
            if exists:
                access.assert_called_once_with(target, os.X_OK)
            else:
                access.assert_not_called()
            if exists and executable:
                read.assert_called_once_with(target)
            else:
                read.assert_not_called()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "hook-active")
        return rows[0][1], rows[0][2]

    def test_unrepresentable_relative_path_preserves_status_and_access_target(self):
        for label, exists, executable, text, expected in (
                ("missing", False, False, "", doctor.WARN),
                ("not executable", True, False, "", doctor.WARN),
                ("foreign hook", True, True, "another hook", doctor.WARN),
                ("toolkit hook", True, True, doctor.HOOK_MARKER, doctor.OK)):
            with self.subTest(state=label):
                target = os.path.abspath(os.path.join("shared hooks", "pre-push"))
                status, detail = self.inspect_hook(exists, executable, text,
                                                  formatter_error=ValueError("different volumes"), target=target)
                self.assertEqual(status, expected)
                self.assertIn(target, detail)

    def test_same_volume_display_stays_relative(self):
        root = os.path.abspath("repo with spaces")
        target = os.path.abspath(os.path.join("shared hooks", "pre-push"))
        expected = os.path.relpath(target, root)
        status, detail = self.inspect_hook(True, True, doctor.HOOK_MARKER, root=root, target=target)
        self.assertEqual(status, doctor.OK)
        self.assertIn("git runs " + expected, detail)

    def test_unrelated_formatter_error_is_not_hidden(self):
        with self.assertRaisesRegex(RuntimeError, "unexpected formatter failure"):
            self.inspect_hook(False, False, "", formatter_error=RuntimeError("unexpected formatter failure"))

    @unittest.skipUnless(os.name == "nt", "Windows drive-letter path semantics")
    def test_native_cross_volume_paths_remain_absolute(self):
        root, target = r"C:\worktree with spaces", r"D:\common git\hooks\pre-push"
        for exists, expected in ((False, doctor.WARN), (True, doctor.OK)):
            with self.subTest(exists=exists):
                status, detail = self.inspect_hook(exists, exists, doctor.HOOK_MARKER, root=root, target=target)
                self.assertEqual(status, expected)
                self.assertIn(target, detail)

    def test_unknown_git_target_remains_unverified_without_formatting(self):
        for is_repo, response in ((False, (0, "", "")), (True, (1, "", "failure")), (True, (0, "", ""))):
            with self.subTest(is_repo=is_repo, response=response):
                with mock.patch.object(doctor.os.path, "isfile", return_value=True), \
                        mock.patch.object(doctor, "in_git", return_value=is_repo), \
                        mock.patch.object(doctor, "git", return_value=response), \
                        mock.patch.object(doctor.os.path, "relpath") as relative:
                    rows = doctor.check_hook("repo")
                    self.assertEqual(rows[0][1], doctor.UNVERIFIED)
                    relative.assert_not_called()


@unittest.skipUnless(os.name == "nt", "native Windows cross-volume worktree")
class CrossVolumeHookChecks(Install):
    workspace_parent = ROOT

    def setUp(self):
        if Path(ROOT).resolve().drive.lower() == Path(tempfile.gettempdir()).drive.lower():
            self.skipTest("two approved Windows fixture volumes are unavailable")
        try:
            with support.TemporaryDirectory(prefix="sdlc-volume-probe-", dir=ROOT):
                pass
        except PermissionError:
            self.skipTest("workspace volume cannot host an owned temporary Git fixture")
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, PYTHONDONTWRITEBYTECODE="1")
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        super(CrossVolumeHookChecks, self).setUp()

    def test_linked_worktree_on_another_volume_reports_missing_hook(self):
        with support.TemporaryDirectory(prefix="sdlc-linked-worktree-") as directory:
            worktree = Path(directory, "worktree with spaces")
            self.g("worktree", "add", "--quiet", "--detach", str(worktree), "HEAD")
            try:
                lookup = subprocess.run(["git", "-C", str(worktree), "rev-parse", "--git-path", "hooks/pre-push"],
                                        check=True, capture_output=True, text=True)
                target = lookup.stdout.strip()
                self.assertTrue(os.path.isabs(target))
                self.assertEqual(Path(target).resolve(), Path(self.repo, ".git", "hooks", "pre-push").resolve())
                self.assertNotEqual(Path(target).drive.lower(), worktree.drive.lower())
                self.assertFalse(Path(target).exists())
                config = Path(self.repo, ".git", "config")
                config_before = config.read_bytes()
                status_before = self.g("status", "--porcelain")
                result = subprocess.run([sys.executable, "-I", "-B", os.path.join(ROOT, "scripts", "doctor.py"),
                                         "--root", str(worktree), "--json"], cwd=str(worktree),
                                        capture_output=True, text=True, timeout=60)
                self.assertEqual(config.read_bytes(), config_before)
                self.assertEqual(self.g("status", "--porcelain"), status_before)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertFalse(report["failed"])
                hook = next(row for row in report["results"] if row["name"] == "hook-active")
                self.assertEqual(hook["status"], doctor.WARN)
                self.assertIn(target, hook["detail"])
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(Path(target).exists())
            finally:
                self.g("worktree", "remove", "--force", str(worktree))


class CodeownersChecks(Install):
    def owners(self, text, rel=".github/CODEOWNERS"):
        self.put(rel, text)

    def test_missing_file_warns(self):
        self.assertEqual(self.status("codeowners"), doctor.WARN)

    def test_catch_all_covers_everything(self):
        self.owners("* @acme/platform\n")
        self.assertEqual(self.status("codeowners"), doctor.OK)

    def test_specific_paths_cover(self):
        self.owners("# gate\n/scripts/ @acme/sec\n/.github/ @acme/sec  # workflows\n")
        self.assertEqual(self.status("codeowners"), doctor.OK)

    def test_partial_coverage_names_the_gaps(self):
        self.owners("/docs/ @acme/docs\n/scripts/ @acme/sec\n")
        status, detail = self.get("codeowners")
        self.assertEqual(status, doctor.WARN)
        self.assertIn(".github/workflows/sdlc-gate.yml", detail)
        self.assertNotIn("scripts/lane.py", detail)

    def test_owner_less_line_un_owns_a_path(self):
        self.owners("* @acme/platform\n/scripts/\n/.github/\n")
        self.assertEqual(self.status("codeowners"), doctor.WARN)

    def test_other_codeowners_locations_found(self):
        self.owners("* @acme/platform\n", rel="CODEOWNERS")
        self.assertEqual(self.status("codeowners"), doctor.OK)


class GitState(Install):
    def add_origin(self, files=None):
        bare = tempfile.mkdtemp(dir=self.workspace)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        if files is None:
            self.g("remote", "add", "origin", bare)
            self.g("push", "-q", "origin", "main")
        else:
            seed = tempfile.mkdtemp(dir=self.workspace)
            subprocess.run(["git", "init", "-q", "-b", "main", seed], check=True)
            for name in files:
                with open(os.path.join(seed, name), "w") as handle:
                    handle.write("x\n")
            for cmd in (["add", "-A"], ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "seed"],
                        ["push", "-q", bare, "main"]):
                subprocess.run(["git", "-C", seed] + cmd, check=True)
            self.g("remote", "add", "origin", bare)
            self.g("fetch", "-q", "origin")
        self.g("remote", "set-head", "origin", "main")

    def test_origin_head_unknown_is_unverified(self):
        self.assertEqual(self.status("tooling-on-default-branch"), doctor.UNVERIFIED)

    def test_tooling_present_on_default_branch(self):
        self.add_origin()
        status, detail = self.get("tooling-on-default-branch")
        self.assertEqual(status, doctor.OK)
        self.assertIn("last fetch", detail)

    def test_tooling_missing_on_default_branch_warns(self):
        self.add_origin(files=["README.md"])
        status, detail = self.get("tooling-on-default-branch")
        self.assertEqual(status, doctor.WARN)
        self.assertIn("scripts/lane.py", detail)

    def test_uncommitted_gate_files_warn_but_bytecode_does_not(self):
        self.put("scripts/__pycache__/x.cpython-312.pyc", "x")
        self.assertEqual(self.statuses("gate-files-committed"), [])
        self.put("scripts/new_helper.py", "x = 1\n")
        self.assertEqual(self.status("gate-files-committed"), doctor.WARN)

    def test_shallow_clone_warns(self):
        clone = tempfile.mkdtemp(dir=self.workspace)
        subprocess.run(["git", "clone", "-q", "--depth", "1", Path(self.repo).resolve().as_uri(), clone + "/c"], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        results = doctor.check_repo(clone + "/c")
        self.assertIn(doctor.WARN, [s for n, s, _ in results if n == "shallow-clone"])
        self.assertEqual(self.statuses("shallow-clone"), [])


FAKE_GH = """import os, sys
from urllib.parse import quote
args = sys.argv[1:]
d = os.environ["FAKE_GH_DIR"]
if args[:1] != ["api"]:
    sys.exit(2)
name = quote(args[1], safe="") + ".json"
path = os.path.join(d, name)
if not os.path.exists(path):
    sys.stderr.write("gh: Not Found (HTTP 404)\\n"); sys.exit(1)
body = open(path).read()
if body.startswith("ERR:"):
    sys.stderr.write(body[4:] + "\\n"); sys.exit(1)
sys.stdout.write(body)
"""


class RemoteChecks(Install):
    def setUp(self):
        super(RemoteChecks, self).setUp()
        self.g("remote", "add", "origin", "https://github.com/acme/widgets.git")
        self.bin = tempfile.mkdtemp(dir=self.workspace)
        self.data = tempfile.mkdtemp(dir=self.workspace)
        self.api("repos/acme/widgets", {"default_branch": "main"})
        self.api("apps/github-actions", {"id": 15368, "slug": "github-actions", "owner": {"login": "github"}})
        env = {"PATH": self.bin + os.pathsep + os.environ["PATH"], "FAKE_GH_DIR": self.data}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def api(self, path, payload):
        body = payload if isinstance(payload, str) else json.dumps(payload)
        with open(os.path.join(self.data, quote(path, safe="") + ".json"), "w") as handle:
            handle.write(body)

    def rules(self, payload):
        self.api("repos/acme/widgets/rules/branches/main?per_page=100&page=1", payload)

    def protection(self, payload):
        self.api("repos/acme/widgets/branches/main/protection", payload)

    def remote(self, with_cli=True, check_name="evidence"):
        with contextlib.ExitStack() as stack:
            if with_cli:
                command = support.fake_command(self.bin, "gh", FAKE_GH)
                if os.name == "nt":
                    original_run, original_which = doctor.run, doctor.shutil.which

                    def run_fixture(argv, *args, **kwargs):
                        if argv and argv[0] == "gh":
                            argv = command + list(argv[1:])
                        return original_run(argv, *args, **kwargs)

                    def which_fixture(name, *args, **kwargs):
                        return command[0] if name == "gh" else original_which(name, *args, **kwargs)

                    stack.enter_context(mock.patch.object(doctor, "run", side_effect=run_fixture))
                    stack.enter_context(mock.patch.object(doctor.shutil, "which", side_effect=which_fixture))
            return {n: (s, d) for n, s, d in doctor.check_repo(self.repo, check_remote=True, check_name=check_name)}

    def test_ruleset_requires_the_check_pinned_to_an_app(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "evidence", "integration_id": 15368}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        got = self.remote()
        self.assertEqual(got["required-check"][0], doctor.OK)
        self.assertNotIn("required-check-source", got)

    def test_classic_protection_with_unpinned_check_warns_not_verified(self):
        self.rules([])
        self.protection({"required_status_checks": {"contexts": ["evidence"], "checks": [{"context": "evidence", "app_id": -1}]},
                         "enforce_admins": {"enabled": True}})
        got = self.remote()
        self.assertEqual(got["required-check"][0], doctor.WARN)
        self.assertEqual(got["required-check-source"][0], doctor.WARN)

    def test_ruleset_check_without_integration_id_is_flagged_unpinned(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "evidence"}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        got = self.remote()
        self.assertEqual(got["required-check"][0], doctor.WARN)
        self.assertEqual(got["required-check-source"][0], doctor.WARN)

    def test_ui_style_context_name_does_not_match_exact_identity(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "sdlc-gate / evidence", "integration_id": 1}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        self.assertEqual(self.remote()["required-check"][0], doctor.FAIL)

    def test_authoritatively_not_required_is_a_failure(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "lint", "integration_id": 1}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        status, detail = self.remote()["required-check"]
        self.assertEqual(status, doctor.FAIL)
        self.assertIn("NOT a required", detail)

    def test_no_rules_and_no_protection_is_a_failure(self):
        self.rules([])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        self.assertEqual(self.remote()["required-check"][0], doctor.FAIL)

    def test_permission_errors_are_unverified_never_a_pass_or_failure(self):
        self.rules("ERR:gh: Resource not accessible (HTTP 403)")
        self.protection("ERR:gh: Resource not accessible (HTTP 403)")
        status, detail = self.remote()["required-check"]
        self.assertEqual(status, doctor.UNVERIFIED)
        self.assertIn("403", detail)

    def test_one_source_unreadable_and_other_lacks_check_is_unverified(self):
        self.rules([])
        self.protection("ERR:gh: Resource not accessible (HTTP 403)")
        self.assertEqual(self.remote()["required-check"][0], doctor.UNVERIFIED)

    def test_positive_evidence_wins_even_if_other_source_errors(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "evidence", "integration_id": 15368}]}}])
        self.protection("ERR:gh: Resource not accessible (HTTP 403)")
        self.assertEqual(self.remote()["required-check"][0], doctor.OK)

    def test_codeowner_review_and_admin_bypass(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "evidence", "integration_id": 1}]}}])
        self.protection({"required_status_checks": {"contexts": [], "checks": []},
                         "required_pull_request_reviews": {"require_code_owner_reviews": False},
                         "enforce_admins": {"enabled": False}})
        got = self.remote()
        self.assertEqual(got["codeowners-required"][0], doctor.WARN)
        self.assertEqual(got["admins-bound"][0], doctor.WARN)
        self.protection({"required_status_checks": {"contexts": [], "checks": []},
                         "required_pull_request_reviews": {"require_code_owner_reviews": True},
                         "enforce_admins": {"enabled": True}})
        got = self.remote()
        self.assertEqual(got["codeowners-required"][0], doctor.OK)
        self.assertNotIn("admins-bound", got)

    def test_ruleset_code_owner_requirement(self):
        self.rules([{"type": "pull_request", "parameters": {"require_code_owner_review": True}},
                    {"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "evidence", "integration_id": 1}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        self.assertEqual(self.remote()["codeowners-required"][0], doctor.OK)

    def test_custom_check_name(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "gate", "integration_id": 15368}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        self.assertEqual(self.remote(check_name="gate")["required-check"][0], doctor.OK)

    def test_garbage_responses_are_unverified(self):
        self.rules("<html>not json</html>")
        self.protection("[1, 2, 3]")
        self.assertEqual(self.remote()["required-check"][0], doctor.UNVERIFIED)

    def test_gh_missing_is_unverified(self):
        self.assertEqual(os.listdir(self.bin), [])
        with mock.patch.object(doctor.shutil, "which", return_value=None):
            status, detail = self.remote(with_cli=False)["required-check"]
        self.assertEqual(status, doctor.UNVERIFIED)
        self.assertIn("gh CLI", detail)

    def test_non_github_remote_is_unverified(self):
        self.g("remote", "set-url", "origin", "https://gitlab.com/acme/widgets.git")
        self.assertEqual(self.remote(with_cli=False)["required-check"][0], doctor.UNVERIFIED)

    def test_remote_url_forms(self):
        for url in ("https://github.com/acme/widgets", "https://github.com/acme/widgets.git",
                    "git@github.com:acme/widgets.git", "ssh://git@github.com/acme/widgets.git",
                    "https://x-access-token:abc@github.com/acme/widgets.git"):
            match = doctor._REMOTE.match(url)
            self.assertEqual(match.groups() if match else None, ("acme", "widgets"), url)
        self.assertIsNone(doctor._REMOTE.match("https://github.com.evil.com/acme/widgets"))

    def test_default_run_never_calls_gh(self):
        with mock.patch.object(doctor, "_gh", side_effect=AssertionError("network call")):
            doctor.check_repo(self.repo)

    def test_fake_cli_keeps_real_process_io_and_environment(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "evidence", "integration_id": 15368}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        with mock.patch.object(doctor.subprocess, "run", wraps=doctor.subprocess.run) as spawn:
            self.assertEqual(self.remote()["required-check"][0], doctor.OK)
        prefix = [sys.executable, "-B", str(Path(self.bin, "gh.py"))] if os.name == "nt" else ["gh"]
        calls = [call for call in spawn.call_args_list if call[0][0][:len(prefix)] == prefix]
        self.assertTrue(calls, "API replies must come from a real subprocess")
        self.assertTrue(any(call[0][0][0] == "git" for call in spawn.call_args_list))
        for call in calls:
            command = call[0][0][len(prefix):]
            self.assertEqual(command[0], "api")
            self.assertEqual(command[command.index("--method") + 1], "GET")
            self.assertEqual(command[command.index("--hostname") + 1], "github.com")
            self.assertEqual(call[1]["stdout"], subprocess.PIPE)
            self.assertEqual(call[1]["stderr"], subprocess.PIPE)
            self.assertEqual(call[1]["env"]["FAKE_GH_DIR"], self.data)
            self.assertEqual(call[1]["env"]["GH_HOST"], "github.com")
            self.assertEqual(call[1]["env"]["GH_PROMPT_DISABLED"], "1")
            self.assertEqual(call[1]["env"]["GH_NO_UPDATE_NOTIFIER"], "1")


EVIDENCE_PROFILE = """name: sdlc-gate
on:
  pull_request:
    types: [opened, synchronize, reopened, edited, ready_for_review]
permissions:
  contents: read
concurrency:
  group: sdlc-gate-${{ github.event.pull_request.number }}
  cancel-in-progress: true
jobs:
  evidence:
    name: evidence
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Checkout trusted tooling (base)
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          path: trusted
          persist-credentials: false
      - name: Checkout change under review (head)
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          path: change
          fetch-depth: 0
          persist-credentials: false
      - name: Check lane evidence (fail-closed)
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: |
          python3 -I trusted/scripts/evidence_check.py --ci \\
            --config trusted/scripts/lane-config.yaml \\
            --repo-root change \\
            --base="$BASE_SHA" --head="$HEAD_SHA" \\
            --emit-json evidence-manifest.json \\
            --event-path "$GITHUB_EVENT_PATH"
      - name: Upload evidence manifest
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: evidence-manifest
          path: evidence-manifest.json
          if-no-files-found: error
"""

SCANNER_PROFILE = """name: gitleaks
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
  pull-requests: read
jobs:
  scan:
    name: gitleaks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: gitleaks/gitleaks-action@f586c14365d4643c6aa59d472ae6e984bf47bb34
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_ENABLE_COMMENTS: "false"
          GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}
"""


class ScannerProfiles(Install):
    V2 = "f586c14365d4643c6aa59d472ae6e984bf47bb34"
    V3 = "e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e"

    def setUp(self):
        super(ScannerProfiles, self).setUp()
        self.inspector = Path(self.workspace, "trusted inspector")
        self.inspector.mkdir()
        self.registry = self.inspector / "scanner-profiles.json"
        self.profiles = {"version": 1, "scanner": "gitleaks/gitleaks-action", "approved": [
            {"release": "v2.3.8", "sha": self.V2}, {"release": "v3.0.0", "sha": self.V3}]}
        self.registry.write_text(json.dumps(self.profiles), encoding="utf-8")
        self.put(".github/workflows/gitleaks.yml", SCANNER_PROFILE)
        for name in ("doctor.py", "lane.py"):
            shutil.copy2(Path(ROOT, "scripts", name), self.inspector / name)
        patcher = mock.patch.object(doctor, "HERE", str(self.inspector))
        patcher.start()
        self.addCleanup(patcher.stop)

    def scan(self, text=SCANNER_PROFILE):
        return {name: (status, detail) for name, status, detail in doctor.workflow_results(text, scanner=True)}

    def assert_bad_registry(self):
        rows = self.scan()
        self.assertIn("scanner-profile-data", rows, rows)
        self.assertEqual(rows["scanner-profile-data"][0], doctor.FAIL)
        self.assertIn("scanner-profiles.json", rows["scanner-profile-data"][1])
        self.assertNotEqual(rows.get("scanner-invokes-gate", (None,))[0], doctor.OK)

    def test_reviewed_v3_and_existing_v2_are_recognized(self):
        for sha in (self.V2, self.V3):
            with self.subTest(sha=sha):
                rows = self.scan(SCANNER_PROFILE.replace(self.V2, sha))
                self.assertEqual(rows["scanner-invokes-gate"][0], doctor.OK, rows)
                self.assertFalse(any(status == doctor.FAIL for status, _ in rows.values()))

    def test_approval_comes_from_the_registry_not_a_compiled_fallback(self):
        self.profiles["approved"] = [self.profiles["approved"][1]]
        self.registry.write_text(json.dumps(self.profiles), encoding="utf-8")
        self.assertEqual(self.scan()["scanner-invokes-gate"][0], doctor.FAIL)

    def test_unlisted_wrong_owner_and_mutable_references_are_rejected(self):
        original = "gitleaks/gitleaks-action@" + self.V2
        for ref in ("gitleaks/gitleaks-action@" + "a" * 40,
                    "untrusted/gitleaks-action@" + self.V2,
                    "gitleaks/gitleaks-action@v3.0.0", "gitleaks/gitleaks-action@" + self.V3[:7], "[]", "{}"):
            with self.subTest(ref=ref):
                self.assertNotEqual(self.scan(SCANNER_PROFILE.replace(original, ref))["scanner-invokes-gate"][0], doctor.OK)

    def test_invalid_registry_shapes_and_entries_fail_closed(self):
        invalid = [None, [], {}, dict(self.profiles, version=True), dict(self.profiles, version="1"),
                   dict(self.profiles, version=2), dict(self.profiles, scanner="untrusted/action"),
                   dict(self.profiles, extra=True), dict(self.profiles, approved=[]),
                   dict(self.profiles, approved="all"), dict(self.profiles, approved=[self.profiles["approved"][0]] * 2)]
        for entry in (None, {}, {"release": "", "sha": self.V2}, {"release": 2, "sha": self.V2},
                      {"release": "v2.3.8", "sha": self.V2[:7]}, {"release": "v2.3.8", "sha": self.V2.upper()},
                      {"release": "v2.3.8", "sha": True}, {"release": "v2.3.8", "sha": self.V2, "extra": True}):
            invalid.append(dict(self.profiles, approved=[entry]))
        for index, value in enumerate(invalid):
            with self.subTest(case=index):
                self.registry.write_text(json.dumps(value), encoding="utf-8")
                self.assert_bad_registry()

    def test_duplicate_keys_encoding_and_excessive_data_are_rejected(self):
        raw = json.dumps(self.profiles)
        for value in (raw.replace('"version": 1', '"version": 2, "version": 1').encode(),
                      raw.replace('"release": "v2.3.8"', '"release": "other", "release": "v2.3.8"').encode(),
                      b"\xff", b"[" * 2000, b" " * (doctor.MAX_FILE_BYTES + 1)):
            with self.subTest(size=len(value)):
                self.registry.write_bytes(value)
                self.assert_bad_registry()

    def test_missing_own_registry_fails_even_without_a_target_scanner(self):
        self.registry.unlink()
        Path(self.repo, ".github/workflows/gitleaks.yml").unlink()
        code, out, err = run_main(["--root", self.repo, "--json"])
        self.assertEqual(code, 1, out + err)
        self.assertTrue(json.loads(out)["failed"])
        self.assertIn("scanner-profile-data", out)
        self.assertNotIn("Traceback", err)

    def test_target_registry_and_cwd_cannot_approve_an_unknown_scanner(self):
        forged = dict(self.profiles, approved=[{"release": "v9.0.0", "sha": "a" * 40}])
        target_registry = Path(self.repo, "scripts/scanner-profiles.json")
        self.put("scripts/scanner-profiles.json", json.dumps(forged))
        self.put(".github/workflows/gitleaks.yml", SCANNER_PROFILE.replace(self.V2, "a" * 40))
        env = dict(os.environ, SDLC_SCANNER_PROFILES=str(target_registry), SCANNER_PROFILES=str(target_registry))
        result = subprocess.run([sys.executable, "-I", "-B", str(self.inspector / "doctor.py"),
                                 "--root", self.repo, "--json"], cwd=self.repo, env=env,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        rows = {row["name"]: row["status"] for row in json.loads(result.stdout)["results"]}
        self.assertEqual(rows["scanner-invokes-gate"], doctor.FAIL)

    def test_external_inspector_does_not_require_target_registry(self):
        self.assertFalse(Path(self.repo, "scripts/scanner-profiles.json").exists())
        self.put(".github/workflows/gitleaks.yml", SCANNER_PROFILE.replace(self.V2, self.V3))
        self.assertEqual(self.status("scanner-invokes-gate"), doctor.OK)
        self.assertFalse(any(status == doctor.FAIL for _, status, _ in self.results()))

    def test_invalid_own_registry_is_reported_by_the_real_cli(self):
        self.registry.write_text("not JSON", encoding="utf-8")
        result = subprocess.run([sys.executable, "-I", "-B", str(self.inspector / "doctor.py"),
                                 "--root", self.repo, "--json"], cwd=self.repo,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["failed"])
        self.assertIn("scanner-profile-data", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


class EnforcementChecks(Install):
    """Provider fixtures establish inspector behavior, not successful hosted scans."""

    APP_ID = 15368
    BRANCH_SHA = "a" * 40
    TREE_SHA = "b" * 40
    PREFIX = "repos/acme/widgets"

    def setUp(self):
        super(EnforcementChecks, self).setUp()
        self.g("remote", "add", "origin", "https://github.com/acme/widgets.git")
        self.put(".github/workflows/sdlc-gate.yml", EVIDENCE_PROFILE)
        self.put(".github/workflows/gitleaks.yml", SCANNER_PROFILE)
        self.put(".github/CODEOWNERS", "* @acme/platform\n")
        self.api_data = {
            "apps/github-actions": {"id": self.APP_ID, "slug": "github-actions", "owner": {"login": "github"}},
            self.PREFIX: {"default_branch": "main"},
            self.PREFIX + "/branches/main": {"name": "main", "protected": True,
                "commit": {"sha": self.BRANCH_SHA, "commit": {"tree": {"sha": self.TREE_SHA}}}},
            self.PREFIX + "/rules/branches/main?per_page=100&page=1": [],
            self.PREFIX + "/rulesets?includes_parents=true&per_page=100&page=1": [],
            self.PREFIX + "/branches/main/protection": {
                "required_status_checks": {"strict": True, "contexts": ["evidence", "gitleaks"],
                    "checks": [{"context": c, "app_id": self.APP_ID} for c in ("evidence", "gitleaks")]},
                "required_pull_request_reviews": {"required_approving_review_count": 1,
                    "require_code_owner_reviews": True, "dismiss_stale_reviews": True,
                    "require_last_push_approval": False,
                    "bypass_pull_request_allowances": {"users": [], "teams": [], "apps": []}},
                "enforce_admins": {"enabled": True},
                "allow_force_pushes": {"enabled": False},
                "allow_deletions": {"enabled": False}},
            self.PREFIX + "/codeowners/errors?ref=" + self.BRANCH_SHA: {"errors": []},
        }
        self.publish()
        patcher = mock.patch.object(doctor, "_gh", side_effect=self.api)
        self.gh = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(doctor, "_gh_queue", return_value=(
            "ok", {"data": {"repository": {"mergeQueue": None}}}, ""))
        self.queue = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(doctor.shutil, "which", return_value="/mock/gh")
        patcher.start()
        self.addCleanup(patcher.stop)

    @property
    def protection(self):
        return self.api_data[self.PREFIX + "/branches/main/protection"]

    def api(self, path):
        data = self.api_data.get(path, ("error", None, "fixture: endpoint unavailable"))
        return data if isinstance(data, tuple) else ("ok", copy.deepcopy(data), "")

    def publish(self, extra=None):
        paths = list(COPIED) + [".github/workflows/gitleaks.yml", ".github/CODEOWNERS"]
        paths += list(extra or [])
        tree = []
        for path in paths:
            body = Path(self.repo, path).read_bytes()
            sha = hashlib.sha1(b"blob " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()
            tree.append({"path": path, "mode": "100644", "type": "blob", "sha": sha})
            self.api_data[self.PREFIX + "/git/blobs/" + sha] = {
                "sha": sha, "encoding": "base64", "size": len(body),
                "content": base64.b64encode(body).decode("ascii")}
        self.api_data[self.PREFIX + "/git/trees/" + self.TREE_SHA + "?recursive=1"] = {
            "sha": self.TREE_SHA, "truncated": False, "tree": tree}

    def strict(self, extra=None):
        code, out, err = run_main(["--root", self.repo, "--check-branch-protection",
                                   "--require-enforcement", "--json"] + list(extra or []))
        data = json.loads(out) if out.strip().startswith("{") else {"results": []}
        got = {r["name"]: (r["status"], r["detail"]) for r in data["results"]}
        return code, got, out + err

    def not_ready(self, diagnostic):
        code, got, output = self.strict()
        self.assertEqual(code, 1, output)
        self.assertNotEqual(got.get("enforcement-readiness", (None,))[0], doctor.OK, output)
        failures = " ".join(name + " " + detail for name, (status, detail) in got.items() if status != doctor.OK)
        self.assertIn(diagnostic, failures, output)

    def test_resumed_complete_classic_profile_uses_observed_queue_state(self):
        code, got, output = self.strict()
        self.assertEqual(code, 0, output)
        self.assertEqual(got["enforcement-merge-queue"][0], doctor.OK)
        self.assertEqual(got["enforcement-check-evidence"][0], doctor.OK)
        self.assertEqual(got["enforcement-readiness"][0], doctor.OK)
        self.assertEqual(got["hook-active"][0], doctor.WARN)
        self.assertIn("main", output)
        self.assertIn(str(self.APP_ID), output)
        self.assertIn("not code correctness", output)
        self.queue.assert_called_once_with("acme", "widgets", "main")

    def test_resumed_queue_errors_missing_data_and_wrong_shapes_are_unverified(self):
        responses = [
            ("error", None, "HTTP 403"), ("error", None, "request timeout"),
            ("ok", {"data": {"__schema": {}}}, ""),
            ("ok", {"data": {"repository": None}}, ""),
            ("ok", {"data": {"repository": {}}}, ""),
            ("ok", {"data": []}, ""),
            ("ok", {"errors": [{"message": "private provider message"}],
                    "data": {"repository": {"mergeQueue": None}}}, ""),
            ("ok", {"errors": {}, "data": {"repository": {"mergeQueue": None}}}, ""),
        ]
        responses += [("ok", {"data": {"repository": {"mergeQueue": value}}}, "")
                      for value in (False, 0, "", {}, {"id": None}, {"id": 1})]
        for response in responses:
            with self.subTest(response=response):
                self.queue.return_value = response
                code, got, output = self.strict()
                self.assertEqual(code, 1, output)
                self.assertEqual(got["enforcement-merge-queue"][0], doctor.UNVERIFIED, output)
                self.assertNotIn("private provider message", output)

    def test_resumed_enabled_classic_merge_queue_is_unsupported(self):
        self.queue.return_value = ("ok", {"data": {"repository": {"mergeQueue": {"id": "MQ_fixture"}}}}, "")
        code, got, output = self.strict()
        self.assertEqual(code, 1, output)
        self.assertEqual(got["enforcement-merge-queue"][0], doctor.FAIL, output)
        self.assertIn("unsupported", got["enforcement-merge-queue"][1])

    def test_strict_flag_requires_explicit_remote_opt_in(self):
        code, _, err = run_main(["--root", self.repo, "--require-enforcement"])
        self.assertEqual(code, 2)
        self.assertIn("requires --check-branch-protection", err)
        self.gh.assert_not_called()
        self.queue.assert_not_called()

    def test_strict_profile_cannot_be_redefined_with_check_name(self):
        code, _, err = run_main(["--root", self.repo, "--check-branch-protection",
                                 "--require-enforcement", "--check-name", "gate"])
        self.assertEqual(code, 2)
        self.assertIn("evidence", err)
        self.gh.assert_not_called()

    def test_offline_zero_is_explicitly_not_hosted_readiness(self):
        code, out, _ = run_main(["--root", self.repo, "--json"])
        self.assertEqual(code, 0, out)
        results = {r["name"]: r["status"] for r in json.loads(out)["results"]}
        self.assertEqual(results.get("enforcement-readiness"), doctor.UNVERIFIED)
        self.gh.assert_not_called()
        self.queue.assert_not_called()

    def test_each_exact_check_and_authoritative_app_identity_is_required(self):
        original = copy.deepcopy(self.protection["required_status_checks"])
        for check in ("evidence", "gitleaks"):
            for replacement in (None, "sdlc-gate / " + check, check + "-extra"):
                with self.subTest(check=check, replacement=replacement):
                    required = self.protection["required_status_checks"] = copy.deepcopy(original)
                    required["checks"] = [r for r in required["checks"] if r["context"] != check]
                    required["contexts"].remove(check)
                    if replacement:
                        required["checks"].append({"context": replacement, "app_id": self.APP_ID})
                        required["contexts"].append(replacement)
                    self.not_ready(check)
        for app_id in (1, 0, -1, None, True, str(self.APP_ID)):
            with self.subTest(app_id=app_id):
                required = self.protection["required_status_checks"] = copy.deepcopy(original)
                required["checks"][0]["app_id"] = app_id
                self.not_ready("evidence")

    def test_actions_identity_cannot_be_guessed_from_historical_app_id(self):
        for response in (("error", None, "HTTP 403"), {}, {"id": self.APP_ID, "slug": "other"},
                         {"id": True, "slug": "github-actions", "owner": {"login": "github"}}):
            with self.subTest(response=response):
                self.api_data["apps/github-actions"] = response
                self.not_ready("application")

    def test_resolved_app_id_is_not_hard_coded(self):
        detail = self.ruleset()
        self.api_data["apps/github-actions"]["id"] = 24680
        for check in detail["rules"][0]["parameters"]["required_status_checks"]:
            check["integration_id"] = 24680
        code, _, output = self.strict()
        self.assertEqual(code, 0, output)
        self.assertIn("24680", output)

    def test_pr_owner_review_and_freshness_are_independent_requirements(self):
        original = copy.deepcopy(self.protection["required_pull_request_reviews"])
        for field, value, diagnostic in (
                ("require_code_owner_reviews", False, "owner"),
                ("required_approving_review_count", 0, "review"),
                ("dismiss_stale_reviews", False, "fresh"),
                ("dismiss_stale_reviews", None, "fresh")):
            with self.subTest(field=field, value=value):
                reviews = self.protection["required_pull_request_reviews"] = copy.deepcopy(original)
                if value is None:
                    del reviews[field]
                else:
                    reviews[field] = value
                self.not_ready(diagnostic)
        self.protection["required_pull_request_reviews"] = None
        self.not_ready("pull request")

    def test_supported_last_push_approval_alternative(self):
        reviews = self.ruleset()["rules"][1]["parameters"]
        reviews["dismiss_stale_reviews_on_push"] = False
        reviews["require_last_push_approval"] = True
        code, _, output = self.strict()
        self.assertEqual(code, 0, output)

    def test_checks_must_be_up_to_date(self):
        for value in (False, None, "true"):
            with self.subTest(value=value):
                required = self.protection["required_status_checks"]
                if value is None:
                    required.pop("strict", None)
                else:
                    required["strict"] = value
                self.not_ready("up-to-date")

    def test_classic_bypasses_must_be_visible_and_absent(self):
        original = copy.deepcopy(self.protection)
        for field, value in (("enforce_admins", {"enabled": False}),
                             ("enforce_admins", {}), ("allow_force_pushes", {"enabled": True}),
                             ("allow_deletions", {"enabled": True})):
            with self.subTest(field=field, value=value):
                self.api_data[self.PREFIX + "/branches/main/protection"] = copy.deepcopy(original)
                self.protection[field] = value
                self.not_ready("bypass")
        for allowances in (None, {}, {"users": [{"login": "operator"}], "teams": [], "apps": []}):
            with self.subTest(allowances=allowances):
                self.api_data[self.PREFIX + "/branches/main/protection"] = copy.deepcopy(original)
                reviews = self.protection["required_pull_request_reviews"]
                if allowances is None:
                    del reviews["bypass_pull_request_allowances"]
                else:
                    reviews["bypass_pull_request_allowances"] = allowances
                self.not_ready("bypass")

    def ruleset(self):
        rules = [
            {"type": "required_status_checks", "parameters": {
                "required_status_checks": [{"context": c, "integration_id": self.APP_ID}
                                           for c in ("evidence", "gitleaks")],
                "strict_required_status_checks_policy": True, "do_not_enforce_on_create": False}},
            {"type": "pull_request", "parameters": {"required_approving_review_count": 1,
                "require_code_owner_review": True, "dismiss_stale_reviews_on_push": True,
                "require_last_push_approval": False}},
            {"type": "deletion"}, {"type": "non_fast_forward"}]
        detail = {"id": 42, "source_type": "Repository", "source": "acme/widgets",
                  "target": "branch", "enforcement": "active", "bypass_actors": [],
                  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
                  "rules": rules}
        self.api_data[self.PREFIX + "/rulesets?includes_parents=true&per_page=100&page=1"] = [
            {k: detail[k] for k in ("id", "source_type", "source", "target", "enforcement")}]
        self.api_data[self.PREFIX + "/rulesets/42"] = detail
        self.api_data[self.PREFIX + "/rules/branches/main"] = [dict(
            r, ruleset_id=42, ruleset_source_type="Repository", ruleset_source="acme/widgets") for r in rules]
        self.api_data[self.PREFIX + "/rules/branches/main?per_page=100&page=1"] = self.api_data[self.PREFIX + "/rules/branches/main"]
        self.api_data[self.PREFIX + "/branches/main/protection"] = (
            "error", None, "gh: Branch not protected (HTTP 404)")
        return detail

    def test_complete_effective_ruleset_profile(self):
        self.ruleset()
        code, got, output = self.strict()
        self.assertEqual(code, 0, output)
        self.assertEqual(got.get("enforcement-readiness", (None,))[0], doctor.OK, output)
        self.assertEqual(got["hook-active"][0], doctor.WARN)
        self.assertIn("not code correctness", output)
        self.queue.assert_not_called()

    def test_ruleset_bypass_visibility_and_policy(self):
        for bypass in (None, [{"actor_id": 1, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
                       [{"actor_id": 2, "actor_type": "Team", "bypass_mode": "pull_request"}]):
            with self.subTest(bypass=bypass):
                detail = self.ruleset()
                if bypass is None:
                    del detail["bypass_actors"]
                else:
                    detail["bypass_actors"] = bypass
                self.not_ready("bypass")

    def test_effective_rules_cannot_hide_unreadable_or_unevaluated_rulesets(self):
        self.ruleset()
        self.api_data[self.PREFIX + "/rulesets/42"] = ("error", None, "HTTP 403")
        self.not_ready("ruleset")
        detail = self.ruleset()
        detail["enforcement"] = "evaluate"
        self.not_ready("ruleset")

    def test_merge_queue_and_unknown_rules_fail_closed(self):
        for kind in ("merge_queue", "future_provider_rule"):
            with self.subTest(kind=kind):
                detail = self.ruleset()
                detail["rules"].append({"type": kind})
                self.api_data[self.PREFIX + "/rules/branches/main"].append({"type": kind,
                    "ruleset_id": 42, "ruleset_source_type": "Repository", "ruleset_source": "acme/widgets"})
                self.not_ready("unsupported")

    def test_every_required_provider_source_must_be_readable(self):
        paths = ["apps/github-actions", self.PREFIX, self.PREFIX + "/branches/main",
                 self.PREFIX + "/rules/branches/main?per_page=100&page=1", self.PREFIX + "/branches/main/protection",
                 self.PREFIX + "/rulesets?includes_parents=true&per_page=100&page=1",
                 self.PREFIX + "/codeowners/errors?ref=" + self.BRANCH_SHA]
        for path in paths:
            with self.subTest(path=path):
                saved = self.api_data[path]
                self.api_data[path] = ("error", None, "HTTP 403")
                self.not_ready("unverified")
                self.api_data[path] = saved

    def test_completeness_effective_rules_are_paginated(self):
        self.ruleset()
        code, _, output = self.strict()
        self.assertEqual(code, 0, output)
        self.assertIn(mock.call(self.PREFIX + "/rules/branches/main?per_page=100&page=1"), self.gh.call_args_list)

    def test_completeness_conflicting_check_app_bindings_are_not_accepted(self):
        for app in (None, 1):
            with self.subTest(app=app):
                self.protection["required_status_checks"]["checks"].append({"context": "evidence", "app_id": app})
                self.not_ready("evidence")
                self.protection["required_status_checks"]["checks"].pop()

    def test_completeness_numeric_yaml_booleans_are_not_supported(self):
        self.put(".github/workflows/gitleaks.yml", SCANNER_PROFILE.replace('GITLEAKS_ENABLE_COMMENTS: "false"',
                                                                        'GITLEAKS_ENABLE_COMMENTS: 0'))
        self.publish()
        self.not_ready("gitleaks")

    def test_completeness_unrelated_safe_matrix_workflow_does_not_block_profile(self):
        self.ruleset()
        self.put(".github/workflows/tests.yml", 'name: tests\non:\n  pull_request:\npermissions:\n  contents: read\n'
                 'jobs:\n  test:\n    runs-on: ${{ matrix.os }}\n    strategy:\n      matrix:\n        include:\n'
                 '          - {os: ubuntu-latest, python: "3.8"}\n    steps:\n      - run: python -m unittest\n')
        self.publish(extra=[".github/workflows/tests.yml"])
        code, _, output = self.strict()
        self.assertEqual(code, 0, output)

    def test_skipped_ignored_or_indirect_workflows_never_verify(self):
        mutations = [
            ("    steps:\n", "    if: false\n    steps:\n"),
            ("        run: |\n", "        if: false\n        run: |\n"),
            ("        run: |\n", "        continue-on-error: true\n        run: |\n"),
            ("        run: |\n", "        shell: bash {0}\n        run: |\n"),
            ("python3 -I trusted/", "python3 trusted/"),
            ("--event-path \"$GITHUB_EVENT_PATH\"", "--event-path \"$GITHUB_EVENT_PATH\" || true"),
            ("  contents: read", "  contents: read\n  actions: write"),
            ("  contents: read", "  contents: ${{ 'read' }}"),
            ("    types: [opened, synchronize, reopened, edited, ready_for_review]",
             "    types: [opened, synchronize, reopened, ready_for_review]"),
            ("  pull_request:", "  pull_request_target:"),
            ("      - name: Checkout trusted tooling (base)", "      - name: Checkout trusted tooling (base)\n        if: false"),
        ]
        for before, after in mutations:
            with self.subTest(after=after):
                self.put(".github/workflows/sdlc-gate.yml", EVIDENCE_PROFILE.replace(before, after))
                self.publish()
                self.not_ready("workflow")

    def test_yaml_duplicates_aliases_and_block_decoys_are_not_proof(self):
        for text in (EVIDENCE_PROFILE + "jobs: {}\n",
                     EVIDENCE_PROFILE.replace("permissions:\n", "permissions: &perms\n"),
                     "name: decoy\non: [pull_request]\njobs:\n  evidence:\n    runs-on: ubuntu-latest\n"
                     "    steps:\n      - run: |\n          echo '" + EVIDENCE_PROFILE.replace("\n", " ") + "'\n"):
            with self.subTest(text=text[:80]):
                self.put(".github/workflows/sdlc-gate.yml", text)
                self.publish()
                self.not_ready("workflow")

    def test_scanner_token_comments_pins_credentials_and_steps(self):
        for before, after in (
                ("          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n", ""),
                ('GITLEAKS_ENABLE_COMMENTS: "false"', 'GITLEAKS_ENABLE_COMMENTS: "true"'),
                ("  pull-requests: read\n", ""),
                ("persist-credentials: false", "persist-credentials: true"),
                ("@f586c14365d4643c6aa59d472ae6e984bf47bb34", "@v2"),
                ("        env:\n", "        continue-on-error: true\n        env:\n"),
                ("        env:\n", "        if: false\n        env:\n")):
            with self.subTest(after=after):
                self.put(".github/workflows/gitleaks.yml", SCANNER_PROFILE.replace(before, after))
                self.publish()
                self.not_ready("gitleaks")

    def test_local_workflow_recognition_is_not_a_stale_hosted_attestation(self):
        self.put(".github/workflows/sdlc-gate.yml", EVIDENCE_PROFILE.replace("python3 -I", "true # python3 -I"))
        self.publish()
        self.put(".github/workflows/sdlc-gate.yml", EVIDENCE_PROFILE)
        self.not_ready("workflow")

    def test_ownership_must_cover_future_execution_dependencies(self):
        for owners in ("/scripts/lane.py @acme/platform\n/.github/ @acme/platform\n",
                       "* @acme/platform\n/scripts/\n", "*\n", "# no owners\n"):
            with self.subTest(owners=owners):
                self.put(".github/CODEOWNERS", owners)
                self.publish()
                self.not_ready("ownership")

    def test_provider_codeowners_errors_prevent_owner_claims(self):
        self.api_data[self.PREFIX + "/codeowners/errors?ref=" + self.BRANCH_SHA] = {
            "errors": [{"line": 1, "kind": "Invalid owner", "message": "private fixture content"}]}
        code, _, output = self.strict()
        self.assertEqual(code, 1, output)
        self.assertNotIn("private fixture content", output)
        self.assertIn("ownership", output)

    def test_truncated_tree_symlinks_and_missing_hosted_files_are_unverified(self):
        path = self.PREFIX + "/git/trees/" + self.TREE_SHA + "?recursive=1"
        for mode in ("truncated", "symlink", "missing"):
            with self.subTest(mode=mode):
                self.publish()
                tree = self.api_data[path]
                if mode == "truncated":
                    tree["truncated"] = True
                elif mode == "symlink":
                    tree["tree"][0]["mode"] = "120000"
                else:
                    tree["tree"] = [r for r in tree["tree"] if r["path"] != ".github/workflows/gitleaks.yml"]
                self.not_ready("enforcement")

    def test_duplicate_check_names_in_another_workflow_are_not_ready(self):
        self.put(".github/workflows/decoy.yml", "name: decoy\non: [pull_request]\njobs:\n"
                 "  harmless:\n    name: evidence\n    runs-on: ubuntu-latest\n"
                 "    steps:\n      - run: 'true'\n")
        self.publish(extra=[".github/workflows/decoy.yml"])
        self.not_ready("workflow")

    def test_read_only_inspection_does_not_change_files_or_git_settings(self):
        self.ruleset()
        before = self.g("status", "--porcelain")
        config = self.g("config", "--local", "--list")
        code, _, output = self.strict()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.g("status", "--porcelain"), before)
        self.assertEqual(self.g("config", "--local", "--list"), config)
        self.assertTrue(all(len(call.args) == 1 and not call.kwargs for call in self.gh.call_args_list))


class WorkflowSafetyRegression(Install):
    def test_resumed_graphql_transport_has_one_constant_query_and_only_variables(self):
        inspect_queue = getattr(doctor, "_gh_queue", None)
        self.assertTrue(callable(inspect_queue), "fixed GraphQL POST transport is not implemented")
        owner = 'someone") { mutation { forbidden } } #'
        response = {"data": {"repository": {"mergeQueue": None}}}
        with mock.patch.object(doctor, "run", return_value=(0, json.dumps(response), "")) as run:
            result = inspect_queue(owner, "widgets", "release/branch")
        self.assertEqual(result, ("ok", response, ""))
        args = run.call_args.args[0]
        self.assertEqual(args[:3], ["gh", "api", "graphql"])
        self.assertEqual(args[args.index("--method") + 1], "POST")
        self.assertEqual(args[args.index("--hostname") + 1], "github.com")
        fields = dict(args[i + 1].split("=", 1) for i, arg in enumerate(args) if arg == "-f")
        expected = ('query SdlcMergeQueue($owner: String!, $repo: String!, $branch: String!) { '
                    'repository(owner: $owner, name: $repo) { mergeQueue(branch: $branch) { id } } }')
        self.assertEqual(fields, {"query": expected, "owner": owner, "repo": "widgets", "branch": "release/branch"})
        self.assertNotIn("mutation", fields["query"])
        with self.assertRaises(TypeError):
            inspect_queue(owner, "widgets", "main", "mutation { forbidden }")

    def test_skipped_gate_does_not_claim_execution_from_a_matching_string(self):
        self.put(".github/workflows/sdlc-gate.yml", EVIDENCE_PROFILE.replace(
            "        run: |", "        if: false\n        run: |"))
        results = {n: s for n, s, _ in doctor.check_workflow(self.repo)}
        self.assertNotEqual(results.get("ci-invokes-gate"), doctor.OK)

    def test_exact_context_identity_does_not_accept_display_suffix(self):
        self.assertFalse(doctor._context_matches("sdlc-gate / evidence", "evidence"))

    def test_gh_explicitly_uses_get_and_github_com(self):
        with mock.patch.object(doctor, "run", return_value=(0, "{}", "")) as run:
            doctor._gh("apps/github-actions")
        args = run.call_args.args[0]
        self.assertIn("GET", args)
        self.assertIn("--hostname", args)
        self.assertIn("github.com", args)
        self.assertNotIn("POST", args)


class ResumedOwnershipProof(unittest.TestCase):
    def test_ambiguous_root_slashes_are_not_normalized_into_global_ownership(self):
        for pattern in ("//**", "/**/", "**/", "*/"):
            with self.subTest(pattern=pattern), self.assertRaises(doctor.ProfileError):
                doctor._ownership_coverage(pattern + " @acme/platform\n", {"scripts/lane.py"})

    def test_root_only_declarations_do_not_own_nested_control_files(self):
        owners = "\n".join("/" + path + " @acme/platform" for path in doctor.lanelib.BUILTIN_CRITICAL)
        with self.assertRaises(doctor.ProfileError):
            doctor._ownership_coverage(owners, {"nested/AGENTS.md"})

    def test_current_lowercase_files_cannot_prove_future_case_variants(self):
        owners = "\n".join(path + " @acme/platform" for path in doctor.lanelib.BUILTIN_CRITICAL)
        with self.assertRaises(doctor.ProfileError):
            doctor._ownership_coverage(owners, {"scripts/lane.py", "AGENTS.md"})

    def test_both_upper_and_lower_samples_do_not_cover_mixed_case(self):
        with mock.patch.object(doctor.lanelib, "BUILTIN_CRITICAL", ("scripts/**",)):
            with self.assertRaises(doctor.ProfileError):
                doctor._ownership_coverage("/scripts/ @acme/a\n/SCRIPTS/ @acme/b\n", {"scripts/lane.py"})

    def test_root_wildcard_is_not_recursive(self):
        with mock.patch.object(doctor.lanelib, "BUILTIN_CRITICAL", ("*.py",)):
            with self.assertRaises(doctor.ProfileError):
                doctor._ownership_coverage("/*.py @acme/platform\n", {"nested/gate.py"})

    def test_targeted_wildcard_proof_does_not_require_a_global_owner(self):
        with mock.patch.object(doctor.lanelib, "BUILTIN_CRITICAL", ("scripts/**",)):
            try:
                doctor._ownership_coverage("/???????/** @acme/platform\n", {"ScRiPtS/new.py"})
            except doctor.ProfileError as exc:
                self.fail("complete case-variant wildcard coverage was rejected: %s" % exc)

    def test_global_fallback_covers_future_files_even_with_root_overrides(self):
        doctor._ownership_coverage("* @acme/platform\n/AGENTS.md @acme/agent-owners\n",
                                   {"nested/AGENTS.md", "SCRIPTS/future.py", ".gitattributes"})

    def test_ownership_proof_includes_new_critical_attributes_boundary(self):
        with mock.patch.object(doctor.lanelib, "BUILTIN_CRITICAL", ("scripts/**", ".gitattributes")):
            with self.assertRaisesRegex(doctor.ProfileError, "gitattributes"):
                doctor._ownership_coverage("/???????/** @acme/platform\n", {"scripts/lane.py"})


if __name__ == "__main__":
    unittest.main()
