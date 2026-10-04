import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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
        code = doctor.main(argv)
    return code, out.getvalue(), err.getvalue()


class Install(unittest.TestCase):
    """A committed, correct install in a temp git repo."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        for rel in COPIED:
            self.put(rel, slurp(os.path.join(ROOT, rel)))
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
        with open(full, "w") as handle:
            handle.write(text)
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
        plain = tempfile.mkdtemp()
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
        self.assertIn(old, text)
        self.put(".github/workflows/sdlc-gate.yml", text.replace(old, new))

    def test_shipped_workflow_has_no_failures_and_trusts_base_tooling(self):
        for name in ("ci-no-pr-target", "ci-trigger", "ci-edited-trigger", "ci-invokes-gate", "ci-fetch-depth",
                     "ci-trusted-tooling", "ci-permissions", "ci-persist-credentials"):
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
        self.edit("persist-credentials: false", "fetch-depth: 0")
        self.assertEqual(self.status("ci-persist-credentials"), doctor.WARN)

    def test_unpinned_actions_warn_once_each_and_pinned_pass(self):
        status, detail = self.get("ci-pinned-actions")
        self.assertEqual(status, doctor.WARN)
        self.assertEqual(detail.count("actions/checkout@v6"), 1)
        text = self.wf()
        import re
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
        self.assertIn("hooks/pre-push", detail)

    def test_hookspath_with_only_the_dot_sh_file_is_NOT_active(self):
        # Regression: doctor once said "verified" here. Git only runs a file named exactly "pre-push".
        os.remove(os.path.join(self.repo, "hooks/pre-push"))
        self.g("config", "core.hooksPath", "hooks")
        status, detail = self.get("hook-active")
        self.assertEqual(status, doctor.WARN)
        self.assertIn("exactly 'pre-push'", detail)

    def test_non_executable_hook_warns(self):
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
        bare = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        if files is None:
            self.g("remote", "add", "origin", bare)
            self.g("push", "-q", "origin", "main")
        else:
            seed = tempfile.mkdtemp()
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
        clone = tempfile.mkdtemp()
        subprocess.run(["git", "clone", "-q", "--depth", "1", "file://" + self.repo, clone + "/c"], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        results = doctor.check_repo(clone + "/c")
        self.assertIn(doctor.WARN, [s for n, s, _ in results if n == "shallow-clone"])
        self.assertEqual(self.statuses("shallow-clone"), [])


FAKE_GH = """#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
d = os.environ["FAKE_GH_DIR"]
if args[:1] != ["api"]:
    sys.exit(2)
name = args[1].replace("/", "__") + ".json"
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
        self.bin = tempfile.mkdtemp()
        self.data = tempfile.mkdtemp()
        gh = os.path.join(self.bin, "gh")
        with open(gh, "w") as handle:
            handle.write(FAKE_GH)
        os.chmod(gh, 0o755)
        self.api("repos/acme/widgets", {"default_branch": "main"})
        env = {"PATH": self.bin + os.pathsep + os.environ["PATH"], "FAKE_GH_DIR": self.data}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def api(self, path, payload):
        body = payload if isinstance(payload, str) else json.dumps(payload)
        with open(os.path.join(self.data, path.replace("/", "__") + ".json"), "w") as handle:
            handle.write(body)

    def rules(self, payload):
        self.api("repos/acme/widgets/rules/branches/main", payload)

    def protection(self, payload):
        self.api("repos/acme/widgets/branches/main/protection", payload)

    def remote(self):
        return {n: (s, d) for n, s, d in doctor.check_repo(self.repo, check_remote=True)}

    def test_ruleset_requires_the_check_pinned_to_an_app(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "evidence", "integration_id": 15368}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        got = self.remote()
        self.assertEqual(got["required-check"][0], doctor.OK)
        self.assertNotIn("required-check-source", got)

    def test_classic_protection_with_check_verified_but_unpinned_warns(self):
        self.rules([])
        self.protection({"required_status_checks": {"contexts": ["evidence"], "checks": [{"context": "evidence", "app_id": -1}]},
                         "enforce_admins": {"enabled": True}})
        got = self.remote()
        self.assertEqual(got["required-check"][0], doctor.OK)
        self.assertEqual(got["required-check-source"][0], doctor.WARN)

    def test_ruleset_check_without_integration_id_is_flagged_unpinned(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "evidence"}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        got = self.remote()
        self.assertEqual(got["required-check"][0], doctor.OK)
        self.assertEqual(got["required-check-source"][0], doctor.WARN)

    def test_ui_style_context_name_matches(self):
        self.rules([{"type": "required_status_checks",
                     "parameters": {"required_status_checks": [{"context": "sdlc-gate / evidence", "integration_id": 1}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        self.assertEqual(self.remote()["required-check"][0], doctor.OK)

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
                     "parameters": {"required_status_checks": [{"context": "evidence", "integration_id": 1}]}}])
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
                     "parameters": {"required_status_checks": [{"context": "gate", "integration_id": 1}]}}])
        self.protection("ERR:gh: Branch not protected (HTTP 404)")
        got = {n: s for n, s, _ in doctor.check_repo(self.repo, check_remote=True, check_name="gate")}
        self.assertEqual(got["required-check"], doctor.OK)

    def test_garbage_responses_are_unverified(self):
        self.rules("<html>not json</html>")
        self.protection("[1, 2, 3]")
        self.assertEqual(self.remote()["required-check"][0], doctor.UNVERIFIED)

    def test_gh_missing_is_unverified(self):
        os.remove(os.path.join(self.bin, "gh"))
        with mock.patch.object(doctor.shutil, "which", return_value=None):
            status, detail = self.remote()["required-check"]
        self.assertEqual(status, doctor.UNVERIFIED)
        self.assertIn("gh CLI", detail)

    def test_non_github_remote_is_unverified(self):
        self.g("remote", "set-url", "origin", "https://gitlab.com/acme/widgets.git")
        self.assertEqual(self.remote()["required-check"][0], doctor.UNVERIFIED)

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


if __name__ == "__main__":
    unittest.main()
