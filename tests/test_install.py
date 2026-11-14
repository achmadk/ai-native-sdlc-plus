"""Exercise real installation entry points and their shared filesystem contract."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

if __package__:
    from . import support
else:
    import support

ROOT = Path(__file__).resolve().parents[1]
SH = support.find_shell()
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
STATE = ".sdlc-install.json"
CORE_FILES = {
    ".gitattributes", "install.sh", "install.ps1", "scripts/sdlc.py", "scripts/agent_profiles.py",
    "scripts/install.py", "scripts/install-manifest.json",
    "scripts/lane.py", "scripts/lane-config.yaml", "scripts/lite.py", "scripts/evidence_check.py", "scripts/scanner-profiles.json",
    "scripts/doctor.py", "scripts/doctor_online.py", "scripts/lane_backtest.py",
    "scripts/trace_lint.py", "scripts/check_spec.py", "scripts/check_brief.py", "scripts/redgreen.py",
    ".github/pull_request_template.md", ".github/workflows/sdlc-gate.yml",
    ".github/workflows/gitleaks.yml", "hooks/pre-push", "hooks/pre-push.sh", "hooks/pre-push.ps1",
    "adapters/ci/README.md", "adapters/ci/gitlab-ci.yml", "adapters/ci/azure-pipelines.yml",
    "adapters/ci/bitbucket-pipelines.yml",
    "adapters/openspec/config.fragment.yaml",
    "adapters/openspec/sdlc-governed/schema.yaml",
    "adapters/openspec/sdlc-governed/templates/proposal.md",
    "adapters/openspec/sdlc-governed/templates/spec.md",
    "adapters/openspec/sdlc-governed/templates/design.md",
    "adapters/openspec/sdlc-governed/templates/threat-note.md",
    "adapters/openspec/sdlc-governed/templates/rollout-plan.md",
    "adapters/openspec/sdlc-governed/templates/tasks.md",
    "adapters/spec-kit/extension/extension.yml",
    "adapters/spec-kit/extension/bin/speckit-sdlc-gate",
    "adapters/spec-kit/preset/preset.yml",
    "adapters/spec-kit/preset/templates/plan-additions.md",
    "adapters/spec-kit/preset/templates/tasks-additions.md",
}
SKILL_FILES = {
    "ai-sdlc/SKILL.md", "ai-sdlc/assets/ci-generic.sh", "ai-sdlc/references/init.md",
    "ai-sdlc/references/doctor.md", "ai-sdlc/references/onboarding.md",
    "spec-first/SKILL.md", "spec-first/scripts/check_spec.py", "spec-first/scripts/spec_inputs.py", "spec-first/references/examples.md",
    "spec-first/assets/intent-template.md", "spec-first/assets/intent-critical-template.md",
    "spec-first/assets/spec-critical-template.md", "spec-first/assets/threat-note-template.md",
    "context-pack/SKILL.md", "context-pack/scripts/check_brief.py", "context-pack/assets/brief-template.md",
    "decision-trace/SKILL.md", "decision-trace/assets/trace-block.md",
    "decision-trace/references/reconstruction-test.md", "learning-mode/SKILL.md",
    "learning-mode/assets/understanding-note-template.md", "learning-mode/references/question-bank.md",
    "learning-mode/references/example-session.md", "review-by-intent/SKILL.md",
    "review-by-intent/assets/review-checklist.md", "review-by-intent/assets/review-notes-template.md",
    "verify-and-evals/SKILL.md", "verify-and-evals/scripts/redgreen.py",
    "verify-and-evals/assets/eval-plan-template.md", "ship-and-observe/SKILL.md",
    "ship-and-observe/assets/incident-intent-template.md", "ship-and-observe/assets/rollout-plan-template.md",
    "ship-and-observe/references/loop-runbooks.md", "autonomy-policy/SKILL.md",
    "autonomy-policy/assets/policy-template.md", "autonomy-policy/references/action-catalog.md",
    "ai-readiness-and-metrics/SKILL.md", "ai-readiness-and-metrics/references/rubric.md",
    "ai-readiness-and-metrics/references/metrics.md",
}
EXPECTED_FILES = CORE_FILES | {"skills/" + path for path in SKILL_FILES}
LF_FILES = (".gitattributes", "install.sh", "hooks/pre-push", "hooks/pre-push.sh",
            "skills/ai-sdlc/assets/ci-generic.sh")
HELPERS = {
    "check_spec.py": "skills/spec-first/scripts/check_spec.py",
    "check_brief.py": "skills/context-pack/scripts/check_brief.py",
    "redgreen.py": "skills/verify-and-evals/scripts/redgreen.py",
}


def find_shellcheck():
    executable = shutil.which("shellcheck")
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return executable if result.returncode == 0 else None


SHELLCHECK = find_shellcheck()


def clean_env(**extra):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    if os.name == "nt" and SH:
        env["PATH"] = os.path.dirname(SH) + os.pathsep + env.get("PATH", "")
    env.update(PYTHONDONTWRITEBYTECODE="1", **extra)
    return env


remove_tree = support.remove_tree


class ShellLint(unittest.TestCase):
    @unittest.skipUnless(SHELLCHECK, "ShellCheck unavailable on this host")
    def test_shell_entrypoints_pass_shellcheck(self):
        result = subprocess.run([SHELLCHECK, "install.sh", "hooks/pre-push", "hooks/pre-push.sh"],
                                cwd=str(ROOT), env=clean_env(), capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class InstallFixture(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="sdlc-install-test-"))
        self.addCleanup(remove_tree, self.temp)
        self.source = self.temp / "source distribution"
        self.source.mkdir()
        for name in ("scripts", "skills", "adapters", ".github"):
            shutil.copytree(str(ROOT / name), str(self.source / name),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("install.sh", "install.ps1"):
            shutil.copy2(str(ROOT / name), str(self.source / name))
        if (ROOT / ".gitattributes").is_file():
            shutil.copy2(str(ROOT / ".gitattributes"), str(self.source / ".gitattributes"))
        shutil.copytree(str(ROOT / "hooks"), str(self.source / "hooks"))
        self.target = self.temp / "target repository"
        self.target.mkdir()
        self.cwd = self.temp / "unrelated directory"
        self.cwd.mkdir()
        self.git("init", "-q", "-b", "main")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.target), "-c", "user.name=Fixture",
                               "-c", "user.email=fixture@example.invalid"] + list(args),
                              env=clean_env(), capture_output=True, check=True).stdout.decode().strip()

    def put(self, path, content, mode=0o644):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)
        path.chmod(mode)
        return path

    def snapshot(self, root=None):
        root = root or self.target
        return {path.relative_to(root).as_posix():
                (path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_mtime_ns)
                for path in root.rglob("*") if path.is_file() and not path.is_symlink()}

    def invoke(self, cwd=None, env=None):
        if getattr(self, "powershell", False):
            command = [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                       "-File", str(self.source / "install.ps1"), "-Root", str(self.target)]
        else:
            command = [SH, str(self.source / "install.sh"), str(self.target)]
        return subprocess.run(command, cwd=str(cwd or self.cwd), env=env or clean_env(),
                              capture_output=True, text=True, timeout=60)

    def successful_install(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.target / STATE).is_file(), "completed installation must publish ownership state")
        return result

    def manifest(self):
        path = self.source / "scripts/install-manifest.json"
        self.assertTrue(path.is_file(), "shared explicit source manifest is required")
        return json.loads(path.read_text())

    def installer(self):
        path = ROOT / "scripts/install.py"
        self.assertTrue(path.is_file(), "shared installer must implement safe plan and publication")
        spec = importlib.util.spec_from_file_location("sdlc_install_test_subject", str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def direct(self, module):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main([str(self.target)], source_root=str(self.source))
        return code, out.getvalue(), err.getvalue()


class InvocationCases:
    def test_clean_target_from_unrelated_cwd_contains_exact_payload_and_state(self):
        git_before = self.snapshot(self.target / ".git")
        result = self.successful_install()
        entries = self.manifest()["files"]
        self.assertEqual({entry["destination"] for entry in entries}, EXPECTED_FILES)
        installed = {path.relative_to(self.target).as_posix() for path in self.target.rglob("*")
                     if path.is_file() and ".git" not in path.relative_to(self.target).parts}
        self.assertEqual(installed, EXPECTED_FILES | {STATE})
        state = json.loads((self.target / STATE).read_text())
        self.assertEqual(state["version"], 1)
        identity = hashlib.sha256((self.source / "scripts/install-manifest.json").read_bytes()).hexdigest()
        self.assertEqual(state["source_manifest"], "sha256:" + identity)
        self.assertEqual(set(state["files"]), EXPECTED_FILES)
        for entry in entries:
            rel = entry["destination"]
            with self.subTest(path=rel):
                self.assertEqual((self.target / rel).read_bytes(), (self.source / entry["source"]).read_bytes())
                record = state["files"][rel]
                self.assertEqual(record["sha256"], hashlib.sha256((self.target / rel).read_bytes()).hexdigest())
                self.assertEqual(record["mode_sha256"], hashlib.sha256(record["mode"].encode("ascii")).hexdigest())
                if os.name != "nt":
                    self.assertEqual(stat.S_IMODE((self.target / rel).stat().st_mode), int(entry["mode"], 8))
                    self.assertEqual(record["mode"], entry["mode"])
        self.assertEqual(self.snapshot(self.target / ".git"), git_before)
        rules = [line for line in (self.target / ".gitattributes").read_text().splitlines()
                 if line and not line.startswith("#")]
        self.assertEqual(rules, ["/%s text eol=lf" % path for path in LF_FILES])
        self.assertIn("hosted merge enforcement: unverified", result.stdout.lower())
        self.assertIn("doctor.py", result.stdout)

    def test_identical_rerun_does_not_rewrite_files_or_completed_state(self):
        initial = self.invoke(cwd=self.source)
        self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
        for path in self.target.rglob("*"):
            if path.is_file() and ".git" not in path.relative_to(self.target).parts:
                os.utime(str(path), ns=(1600000000000000000, 1600000000000000000))
        before = self.snapshot()
        result = self.invoke(cwd=self.source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertIn("retained", result.stdout.lower())
        self.assertTrue((self.target / STATE).is_file())

    def test_legacy_identical_file_is_retained_without_ownership(self):
        rel = "scripts/lane-config.yaml"
        path = self.put(self.target / rel, (self.source / rel).read_bytes())
        os.utime(str(path), ns=(1600000000000000000, 1600000000000000000))
        before = self.snapshot()[rel]
        result = self.invoke(cwd=self.source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.snapshot()[rel], before)
        self.assertTrue((self.target / STATE).is_file())

    def test_custom_policy_workflow_template_hook_and_skill_prevent_all_payload_writes(self):
        for rel in ("scripts/lane-config.yaml", "scripts/scanner-profiles.json", ".github/workflows/sdlc-gate.yml",
                    ".github/workflows/gitleaks.yml", ".github/pull_request_template.md",
                    "hooks/pre-push", "hooks/pre-push.sh", "hooks/pre-push.ps1", "skills/ai-sdlc/SKILL.md"):
            with self.subTest(path=rel):
                path = self.put(self.target / rel, "local customization\n")
                before = self.snapshot()
                result = self.invoke(cwd=self.source)
                self.assertNotEqual(result.returncode, 0, "conflicting install must fail")
                self.assertIn("conflict", (result.stdout + result.stderr).lower())
                self.assertIn(rel, result.stdout + result.stderr)
                self.assertEqual(self.snapshot(), before)
                path.unlink()

    def test_missing_source_fails_before_payload_writes(self):
        (self.source / "scripts/lane.py").unlink()
        before = self.snapshot()
        result = self.invoke(cwd=self.source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scripts/lane.py", result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_owned_scanner_registry_upgrades_and_preserves_local_changes(self):
        self.successful_install()
        rel = "scripts/scanner-profiles.json"
        target = self.target / rel
        self.assertTrue(target.is_file(), "the installed doctor requires its owned scanner registry")
        updated = (self.source / rel).read_bytes() + b"\n"
        self.put(self.source / rel, updated)
        self.successful_install()
        self.assertEqual(target.read_bytes(), updated)
        state = json.loads((self.target / STATE).read_text())
        self.assertEqual(state["files"][rel]["sha256"], hashlib.sha256(updated).hexdigest())
        self.put(target, updated + b" ")
        before = self.snapshot()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(rel, result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_custom_attributes_conflict_without_payload_writes(self):
        self.put(self.target / ".gitattributes", "*.txt text eol=crlf\n")
        before = self.snapshot()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0, "custom attributes must be a preflight conflict")
        self.assertIn(".gitattributes", result.stdout + result.stderr)
        self.assertIn("conflict", (result.stdout + result.stderr).lower())
        self.assertEqual(self.snapshot(), before)

    def test_malformed_state_does_not_authorize_writes(self):
        self.put(self.target / STATE, '{"version": 1, "files": "not an ownership table"}')
        self.put(self.target / "scripts/lane-config.yaml", "local rules\n")
        before = self.snapshot()
        result = self.invoke(cwd=self.source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(STATE, result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_locally_modified_owned_file_aborts_other_updates(self):
        self.successful_install()
        self.put(self.source / "hooks/pre-push.sh", "new upstream hook\n", 0o755)
        self.put(self.target / "scripts/lane-config.yaml", "local calibrated rules\n")
        before = self.snapshot()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scripts/lane-config.yaml", result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_owned_upgrade_updates_only_unchanged_managed_file_and_state(self):
        self.successful_install()
        before = self.snapshot()
        rel = "skills/ai-sdlc/references/onboarding.md"
        self.put(self.source / rel, "Updated upstream onboarding.\n")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        after = self.snapshot()
        self.assertEqual(after[rel][0], b"Updated upstream onboarding.\n")
        self.assertNotEqual(after[STATE][0], before[STATE][0])
        self.assertEqual({key: value for key, value in before.items() if key not in (rel, STATE)},
                         {key: value for key, value in after.items() if key not in (rel, STATE)})

    def test_unrelated_target_doctor_is_never_executed(self):
        marker = self.temp / "DESTINATION_DOCTOR_RAN"
        self.put(self.target / "scripts/doctor.py",
                 "from pathlib import Path\nPath(%r).write_text('executed')\n" % str(marker))
        (self.source / "scripts/doctor.py").unlink()
        before = self.snapshot()
        result = self.invoke(cwd=self.source)
        self.assertFalse(marker.exists(), "verification must not execute stale target doctor")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_existing_hook_manager_and_git_hook_are_preserved(self):
        self.git("config", "core.hooksPath", "custom-hooks")
        self.put(self.target / ".git/hooks/pre-push", "existing native hook\n", 0o755)
        self.put(self.target / "custom-hooks/pre-push", "existing managed hook\n", 0o755)
        before = self.snapshot()
        result = self.successful_install()
        after = self.snapshot()
        for path, original in before.items():
            self.assertEqual(after[path], original, path)
        self.assertEqual(self.git("config", "--get", "core.hooksPath"), "custom-hooks")
        self.assertIn("custom-hooks", result.stdout)
        self.assertIn("unchanged", result.stdout.lower())

    def test_preexisting_activation_is_reported_without_changing_configuration(self):
        self.git("config", "core.hooksPath", "hooks")
        before = self.snapshot(self.target / ".git")
        result = self.successful_install()
        self.assertEqual(self.snapshot(self.target / ".git"), before)
        self.assertIn("pre-existing", result.stdout.lower())
        self.assertIn("advisory", result.stdout.lower())

    def test_included_preexisting_hook_configuration_is_reported(self):
        config = self.put(self.temp / "included-hook.conf", "[core]\n\thooksPath = hooks\n")
        self.git("config", "include.path", str(config))
        before = self.snapshot(self.target / ".git")
        result = self.successful_install()
        self.assertEqual(self.snapshot(self.target / ".git"), before)
        self.assertIn("pre-existing core.hooksPath", result.stdout)

    @unittest.skipUnless(SH, "Git-dispatched hook requires Git's shell")
    def test_installed_git_dispatched_hook_works_with_only_python(self):
        self.successful_install()
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "installed base fixture")
        for relative in LF_FILES:
            (self.target / relative).unlink()
        self.git("checkout-index", "--all", "--force")
        for relative in LF_FILES:
            self.assertNotIn(b"\r", (self.target / relative).read_bytes(), relative)
        origin = self.temp / "origin.git"
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)],
                       env=clean_env(), check=True, capture_output=True)
        self.git("remote", "add", "origin", str(origin))
        self.git("push", "-q", "origin", "main")
        self.git("remote", "set-head", "origin", "main")
        self.git("checkout", "-q", "-b", "feature")
        self.put(self.target / "auth/login.py", "# fixture change\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "security fixture")
        self.git("config", "core.hooksPath", "hooks")
        bindir = self.temp / "python-only"
        bindir.mkdir()
        self.put(bindir / "python", "#!/bin/sh\nexec %s \"$@\"\n" %
                 shlex.quote(sys.executable.replace("\\", "/")), 0o755)
        if os.name == "nt":
            git_root = Path(shutil.which("git")).parent.parent
            directories = [str(bindir), str(Path(SH).parent), str(git_root / "cmd"),
                           str(git_root / "mingw64/bin"), str(git_root / "usr/bin"),
                           str(Path(os.environ["SystemRoot"]) / "System32")]
        else:
            for tool in ("git", "sh", "dirname", "sed"):
                (bindir / tool).symlink_to(shutil.which(tool))
            directories = [str(bindir)]
        env = clean_env(PATH=os.pathsep.join(directories))
        probe = subprocess.run([SH, "-c", "command -v python3"], env=env, capture_output=True)
        self.assertNotEqual(probe.returncode, 0, "fixture must not expose python3")
        before = (self.target / ".git/config").read_bytes()
        result = subprocess.run([shutil.which("git"), "-C", str(self.target), "push", "origin", "feature"],
                                env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("sdlc: note: lane Critical", result.stderr)
        self.assertEqual((self.target / ".git/config").read_bytes(), before)

    @unittest.skipUnless(SH, "Git-dispatched hook requires Git's shell")
    def test_installed_git_hook_survives_crlf_checkout_policy(self):
        self.git("config", "core.autocrlf", "true")
        before = (self.target / ".git/config").read_bytes()
        self.test_installed_git_dispatched_hook_works_with_only_python()
        self.assertEqual(self.git("config", "--get", "core.autocrlf"), "true")
        self.assertIn(b"autocrlf = true", before)


@unittest.skipUnless(SH, support.SHELL_REQUIRED)
class POSIXInstallation(InvocationCases, InstallFixture):
    def test_relative_launcher_ignores_inherited_cdpath(self):
        shadow = self.temp / "shadow" / self.source.name
        marker = self.temp / "SHADOW_INSTALLER_RAN"
        self.put(shadow / "scripts/install.py",
                 "from pathlib import Path\nPath(%r).write_text('executed')\nraise SystemExit(23)\n" % str(marker))
        shadow_before = self.snapshot(shadow)
        git_before = self.snapshot(self.target / ".git")
        env = clean_env(CDPATH="shadow")
        control = subprocess.run([SH, "-c", 'cd -- "$1" >/dev/null && pwd -P', "cdpath-control", self.source.name],
                                 cwd=str(self.temp), env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(control.returncode, 0, control.stdout + control.stderr)
        self.assertEqual(Path(support.native_path(control.stdout.strip())).resolve(), shadow.resolve())

        launcher = (self.source / "install.sh").relative_to(self.temp).as_posix()
        result = subprocess.run([SH, launcher, str(self.target)], cwd=str(self.temp), env=env,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(marker.exists(), "source lookup must not execute the CDPATH shadow installer")
        installed = {path.relative_to(self.target).as_posix() for path in self.target.rglob("*")
                     if path.is_file() and ".git" not in path.relative_to(self.target).parts}
        self.assertEqual(installed, EXPECTED_FILES | {STATE})
        state = json.loads((self.target / STATE).read_text())
        self.assertEqual(set(state["files"]), EXPECTED_FILES)
        for entry in self.manifest()["files"]:
            with self.subTest(path=entry["destination"]):
                self.assertEqual((self.target / entry["destination"]).read_bytes(),
                                 (self.source / entry["source"]).read_bytes())
        self.assertEqual(self.snapshot(shadow), shadow_before)
        self.assertEqual(self.snapshot(self.target / ".git"), git_before)

    def test_missing_interpreter_fails_before_creating_payload(self):
        bindir = self.temp / "no python"
        bindir.mkdir()
        for tool in ("sh", "dirname", "mkdir", "cp", "chmod"):
            support.shell_wrapper(bindir / tool, "exec %s \"$@\"" %
                                  shlex.quote(support.shell_path(support.shell_tool(tool))))
        before = self.snapshot()
        result = self.invoke(cwd=self.source, env=clean_env(PATH=str(bindir)))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Python >= 3.8", result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_unusable_python3_falls_back_to_usable_python(self):
        bindir = self.temp / "interpreter shims"
        bindir.mkdir()
        self.put(bindir / "python3", "#!/bin/sh\nexit 127\n", 0o755)
        self.put(bindir / "python", "#!/bin/sh\nexec %s \"$@\"\n" %
                 shlex.quote(support.shell_path(sys.executable)), 0o755)
        result = self.invoke(env=clean_env(PATH=str(bindir) + os.pathsep + clean_env()["PATH"]))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.target / STATE).exists())


@unittest.skipUnless(POWERSHELL, "PowerShell unavailable; native Windows CI must run these invocations")
class PowerShellInstallation(InvocationCases, InstallFixture):
    powershell = True

    def test_missing_interpreter_fails_before_payload_writes(self):
        bindir = self.temp / "no python"
        bindir.mkdir()
        before = self.snapshot()
        result = self.invoke(env=clean_env(PATH=str(bindir)))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Python >= 3.8", result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_python_without_python3_is_usable_by_native_entry_point(self):
        bindir = self.temp / "python only"
        bindir.mkdir()
        if os.name == "nt":
            self.put(bindir / "python.cmd", '@echo off\r\n"' + sys.executable + '" %*\r\nexit /b %ERRORLEVEL%\r\n')
        else:
            (bindir / "python").symlink_to(sys.executable)
        env = clean_env(PATH=str(bindir))
        probe = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-Command",
                                "if (Get-Command python3 -ErrorAction SilentlyContinue) { exit 1 }; exit 0"],
                               env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(probe.returncode, 0, "fixture must not expose python3: " + probe.stderr)
        result = self.invoke(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.target / STATE).is_file())

    @unittest.skipUnless(os.name == "nt", "Windows command-discovery fixture")
    def test_two_python_matches_use_the_first_usable_one(self):
        broken = self.temp / "broken interpreter"
        broken.mkdir()
        self.put(broken / "python.cmd", "@echo off\r\nexit /b 1\r\n")
        working = self.temp / "working interpreter"
        working.mkdir()
        self.put(working / "python.cmd",
                 '@echo off\r\n"' + sys.executable + '" %*\r\nexit /b %ERRORLEVEL%\r\n')
        env = clean_env(PATH=os.pathsep.join((str(broken), str(working))))
        probe = subprocess.run(
            [POWERSHELL, "-NoProfile", "-NonInteractive", "-Command",
             "@(Get-Command python -CommandType Application -ErrorAction SilentlyContinue).Count"],
            env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(probe.stdout.strip(), "2",
                         "fixture must expose two python matches: " + probe.stderr)
        result = self.invoke(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.target / STATE).is_file())


@unittest.skipUnless(SH, support.SHELL_REQUIRED)
class FilesystemSafety(InstallFixture):
    def test_source_manifest_is_an_exact_allowlist_not_a_recursive_copy(self):
        manifest = self.manifest()
        self.assertEqual(manifest["version"], 1)
        self.assertEqual({entry["source"] for entry in manifest["files"]}, EXPECTED_FILES)
        self.assertEqual({entry["destination"] for entry in manifest["files"]}, EXPECTED_FILES)
        for rel in ("scripts/unexpected.py", "skills/ai-sdlc/__pycache__/cache.pyc",
                    ".kilo/agent-manager.json", "opencode_session.txt"):
            self.put(self.source / rel, "must not ship\n")
        self.successful_install()
        for rel in ("scripts/unexpected.py", "skills/ai-sdlc/__pycache__/cache.pyc",
                    ".kilo/agent-manager.json", "opencode_session.txt", ".github/workflows/ci.yml",
                    ".github/CODEOWNERS", "AGENTS.md"):
            self.assertFalse((self.target / rel).exists(), rel)

    def test_symlink_directory_escape_is_rejected_without_external_writes(self):
        support.require_symlinks(directory=True)
        outside = self.temp / "outside"
        outside.mkdir()
        (self.target / "scripts").symlink_to(outside, target_is_directory=True)
        before = self.snapshot()
        result = self.invoke(cwd=self.source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scripts", result.stdout + result.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(self.snapshot(), before)

    @unittest.skipUnless(os.name == "nt", "Windows junction contract")
    def test_windows_junction_escape_is_rejected_without_external_writes(self):
        outside = self.temp / "outside"
        outside.mkdir()
        link = self.target / "scripts"
        support.make_junction(link, outside)
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.target / STATE).exists())

    def test_symlink_file_and_state_are_rejected_even_when_bytes_match(self):
        support.require_symlinks()
        for rel in ("scripts/lane.py", STATE):
            with self.subTest(path=rel):
                outside = self.put(self.temp / "outside-file", (self.source / "scripts/lane.py").read_bytes())
                link = self.target / rel
                link.parent.mkdir(exist_ok=True)
                link.symlink_to(outside)
                before = outside.read_bytes()
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(link.is_symlink())
                self.assertEqual(outside.read_bytes(), before)
                link.unlink()

    def test_escaping_duplicate_and_metadata_manifest_paths_fail_preflight(self):
        manifest = self.manifest()
        for bad in ("../escaped.py", "/absolute.py", "scripts/../../escaped.py", "scripts\\escape.py",
                    "C:/escape.py", ".git/hooks/pre-push", STATE, "scripts/lane.py"):
            with self.subTest(path=bad):
                changed = dict(manifest, files=manifest["files"] + [
                    {"source": "scripts/lane.py", "destination": bad, "mode": "0644"}])
                self.put(self.source / "scripts/install-manifest.json", json.dumps(changed))
                before = self.snapshot()
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.snapshot(), before)

    def test_escaping_source_is_rejected_before_writes(self):
        manifest = self.manifest()
        manifest["files"][0]["source"] = "../outside-source"
        self.put(self.source / "scripts/install-manifest.json", json.dumps(manifest))
        before = self.snapshot()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_locally_changed_mode_is_a_conflict_even_when_content_is_identical(self):
        support.require_executable_bits()
        self.successful_install()
        (self.target / "scripts/lane.py").chmod(0o600)
        before = self.snapshot()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scripts/lane.py", result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_post_preflight_edit_is_not_overwritten(self):
        module = self.installer()
        self.successful_install()
        manifest = self.manifest()
        first, second = [entry["destination"] for entry in manifest["files"][:2]]
        for rel in (first, second):
            with (self.source / rel).open("ab") as handle:
                handle.write(b"\n# upstream update\n")
        old_state = (self.target / STATE).read_bytes()
        replace = os.replace

        def racing_replace(source, destination):
            result = replace(source, destination)
            if Path(destination) == self.target / first:
                self.put(self.target / second, "concurrent local edit\n")
            return result

        with mock.patch.object(module.os, "replace", side_effect=racing_replace):
            code, out, err = self.direct(module)
        self.assertNotEqual(code, 0)
        self.assertEqual((self.target / second).read_bytes(), b"concurrent local edit\n")
        self.assertEqual((self.target / STATE).read_bytes(), old_state)
        self.assertIn("changed after preflight", out + err)
        self.assertIn(first, out + err)

    def test_partial_io_failure_reports_paths_without_publishing_state_then_retry_works(self):
        module = self.installer()
        entries = self.manifest()["files"]
        first, second = [entry["destination"] for entry in entries[:2]]
        replace = os.replace

        def failing_replace(source, destination):
            if Path(destination) == self.target / second:
                raise OSError("injected disk failure")
            return replace(source, destination)

        with mock.patch.object(module.os, "replace", side_effect=failing_replace):
            code, out, err = self.direct(module)
        self.assertNotEqual(code, 0)
        self.assertIn("partial", (out + err).lower())
        self.assertIn(first, out + err)
        self.assertIn("injected disk failure", out + err)
        self.assertFalse((self.target / STATE).exists())
        self.assertFalse((self.target / second).exists())
        retained = self.snapshot()[first]
        self.successful_install()
        self.assertEqual(self.snapshot()[first], retained)

    def test_verification_failure_does_not_publish_success(self):
        module = self.installer()
        entries = self.manifest()["files"]
        first, last = entries[0]["destination"], entries[-1]["destination"]
        replace = os.replace

        def corrupt_after_publish(source, destination):
            result = replace(source, destination)
            if Path(destination) == self.target / last:
                self.put(self.target / first, "changed during install\n")
            return result

        with mock.patch.object(module.os, "replace", side_effect=corrupt_after_publish):
            code, out, err = self.direct(module)
        self.assertNotEqual(code, 0)
        self.assertIn("verification", (out + err).lower())
        self.assertFalse((self.target / STATE).exists())
        self.assertNotIn("installation complete", (out + err).lower())

    def test_state_publication_failure_is_nonzero_and_explicitly_partial(self):
        module = self.installer()
        replace = os.replace

        def failing_state(source, destination):
            if Path(destination) == self.target / STATE:
                raise OSError("injected state failure")
            return replace(source, destination)

        with mock.patch.object(module.os, "replace", side_effect=failing_state):
            code, out, err = self.direct(module)
        self.assertNotEqual(code, 0)
        self.assertIn("partial", (out + err).lower())
        self.assertIn(STATE, out + err)
        self.assertFalse((self.target / STATE).exists())

    def test_staging_cleanup_failure_does_not_publish_completed_state(self):
        module = self.installer()
        rmdir = os.rmdir

        def failing_cleanup(path, *args, **kwargs):
            if os.path.basename(path).startswith(".sdlc-stage-"):
                raise OSError("injected staging cleanup failure")
            return rmdir(path, *args, **kwargs)

        with mock.patch.object(module.os, "rmdir", side_effect=failing_cleanup):
            code, out, err = self.direct(module)
        self.assertNotEqual(code, 0)
        self.assertIn("partial", (out + err).lower())
        self.assertFalse((self.target / STATE).exists(), "completed state must be the final publication")

    def test_tampered_staged_state_cannot_be_published_as_complete(self):
        module = self.installer()
        last = self.manifest()["files"][-1]["destination"]
        replace = os.replace

        def tamper_with_state(source, destination):
            result = replace(source, destination)
            if Path(destination) == self.target / last:
                for directory in self.target.glob(".sdlc-stage-*"):
                    for staged in directory.iterdir():
                        self.put(staged, "tampered state\n")
            return result

        with mock.patch.object(module.os, "replace", side_effect=tamper_with_state):
            code, out, err = self.direct(module)
        self.assertNotEqual(code, 0, "state must still match trusted source-side verification")
        self.assertIn("verification", (out + err).lower())
        self.assertFalse((self.target / STATE).exists())

    def test_final_state_is_rechecked_immediately_before_publication(self):
        module = self.installer()
        verify = module.verify_payload

        def tamper_during_payload_check(root, payload):
            verify(root, payload)
            for path in self.target.glob(".sdlc-state-*"):
                self.put(path, "concurrent temporary state edit\n")

        with mock.patch.object(module, "verify_payload", side_effect=tamper_during_payload_check):
            code, out, err = self.direct(module)
        self.assertNotEqual(code, 0, "only the verified completed state may be published")
        self.assertIn("verification", (out + err).lower())
        self.assertFalse((self.target / STATE).exists())

    def test_changed_ownership_state_is_detected_before_payload_replacement(self):
        module = self.installer()
        self.successful_install()
        first = self.manifest()["files"][0]["destination"]
        self.put(self.source / first, "# upgraded payload\n")
        before = self.snapshot()
        fsync = os.fsync
        changed = []

        def change_state(descriptor):
            fsync(descriptor)
            if not changed:
                self.put(self.target / STATE, before[STATE][0] + b"\n")
                changed.append(True)

        with mock.patch.object(module.os, "fsync", side_effect=change_state):
            code, out, err = self.direct(module)
        self.assertNotEqual(code, 0)
        self.assertIn("changed after preflight", out + err)
        self.assertEqual(self.snapshot()[first], before[first])
        self.assertEqual((self.target / STATE).read_bytes(), before[STATE][0] + b"\n")

    def test_unportable_and_state_descendant_destinations_are_rejected_preflight(self):
        manifest = self.manifest()
        for index, bad in enumerate(("scripts/star*.py", "scripts/question?.py", "scripts/pipe|.py", STATE + "/nested")):
            with self.subTest(path=bad):
                self.target = self.temp / ("invalid target %d" % index)
                self.target.mkdir()
                self.git("init", "-q", "-b", "main")
                changed = dict(manifest, files=manifest["files"] + [
                    {"source": "scripts/lane.py", "destination": bad, "mode": "0644"}])
                self.put(self.source / "scripts/install-manifest.json", json.dumps(changed))
                before = self.snapshot()
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.snapshot(), before)

    def test_deeply_malformed_state_has_actionable_error_without_traceback(self):
        self.put(self.target / STATE, '{"version":1,"files":' + "[" * 2000)
        before = self.snapshot()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(STATE, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)


class FingerprintContract(InstallFixture):
    def test_path_and_handle_fingerprints_agree_for_the_same_file(self):
        module = self.installer()
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        for index in range(8):
            sample = self.put(self.temp / ("fingerprint-%d.txt" % index), "content %d\n" % index)
            descriptor = os.open(sample, flags)
            try:
                self.assertEqual(module.stamp(os.lstat(sample)), module.stamp(os.fstat(descriptor)),
                                 sample.name)
            finally:
                os.close(descriptor)


class HelperEntryPoints(InstallFixture):
    @unittest.skipUnless(SH, support.SHELL_REQUIRED)
    def test_installed_doctor_reports_a_missing_registry_without_traceback(self):
        self.successful_install()
        registry = self.target / "scripts/scanner-profiles.json"
        self.assertTrue(registry.is_file(), "required registry must be installed")
        registry.unlink()
        result = subprocess.run([sys.executable, "-I", "-B", str(self.target / "scripts/doctor.py"),
                                 "--root", str(self.target), "--json"], cwd=str(self.cwd),
                                env=clean_env(), capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["failed"])
        self.assertIn("scanner-profile-data", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    @unittest.skipUnless(SH, support.SHELL_REQUIRED)
    def test_installed_doctor_is_healthy_without_source_checkout(self):
        self.successful_install()
        remove_tree(self.source)
        result = subprocess.run([sys.executable, "-I", "-B", str(self.target / "scripts/doctor.py"),
                                 "--root", str(self.target), "--json"], cwd=str(self.cwd),
                                env=clean_env(), capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["failed"])
        self.assertEqual(report["summary"]["FAIL"], 0)
        self.assertEqual([row["status"] for row in report["results"]
                          if row["name"] == "scanner-invokes-gate"], ["verified"])

    def test_root_helpers_delegate_imports_without_shadowing_authoritative_modules(self):
        probe = ("import importlib, sys; sys.path.insert(0, sys.argv[1]); "
                 "module = importlib.import_module(sys.argv[2]); "
                 "assert callable(getattr(module, 'main', None)), 'helper main API missing'; "
                 "assert hasattr(module, 'SECRETS'), 'shared helper patterns missing'; "
                 "assert module.main.__globals__ is vars(module), 'module patches must reach implementation globals'")
        for name in HELPERS:
            with self.subTest(helper=name):
                result = subprocess.run([sys.executable, "-I", "-B", "-c", probe, str(ROOT / "scripts"), name[:-3]],
                                        env=clean_env(), capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def parity(self, root):
        bad = self.put(self.temp / "invalid document.md", "# Not a filled document\n")
        for name, implementation in HELPERS.items():
            entry = root / "scripts" / name
            self.assertTrue(entry.is_file(), "documented root helper is missing: " + name)
            cases = (["--help"], ["--not-a-real-option"])
            if name != "redgreen.py":
                cases += ([str(bad), "--lane", "Standard", "--json"],)
            else:
                cases += (["--base", "nonexistent-revision", "--cmd", "python -V", "--json"],)
            for args in cases:
                with self.subTest(helper=name, args=args):
                    wrapper = subprocess.run([sys.executable, "-B", str(entry)] + args, cwd=str(self.cwd),
                                             env=clean_env(), capture_output=True)
                    original = subprocess.run([sys.executable, "-B", str(root / implementation)] + args,
                                              cwd=str(self.cwd), env=clean_env(), capture_output=True)
                    self.assertEqual((wrapper.returncode, wrapper.stdout, wrapper.stderr),
                                     (original.returncode, original.stdout, original.stderr))

    def test_source_root_helpers_preserve_arguments_output_and_exit_status(self):
        self.parity(ROOT)

    @unittest.skipUnless(SH, support.SHELL_REQUIRED)
    def test_installed_commands_and_generic_runner_work_without_source_checkout(self):
        self.successful_install()
        remove_tree(self.source)
        self.parity(self.target)
        self.put(self.target / "docs/change.md", "base document\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "installed fixture")
        base = self.git("rev-parse", "HEAD")
        self.put(self.target / "docs/change.md", "updated document\n")
        self.git("commit", "-q", "-am", "documentation fixture")
        head = self.git("rev-parse", "HEAD")
        body = self.put(self.temp / "pr-body.md", "## Intent\nClarify the documentation without changing behavior.\n"
                        "## Trace\nUsed the installed toolkit to verify the documentation-only fixture.\n")
        env = support.shell_environment(self.temp / "shell-bin", clean_env(
            SDLC_BASE=base, SDLC_HEAD=head, SDLC_PR_BODY_FILE=support.shell_path(body)))
        result = subprocess.run([SH, str(self.target / "skills/ai-sdlc/assets/ci-generic.sh")],
                                cwd=str(self.target), env=env,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Lite", result.stdout + result.stderr)
        for adapter in ("gitlab-ci.yml", "azure-pipelines.yml", "bitbucket-pipelines.yml"):
            self.assertIn("skills/ai-sdlc/assets/ci-generic.sh", (self.target / "adapters/ci" / adapter).read_text())
        for rel in SKILL_FILES:
            if not rel.endswith(".md"):
                continue
            path = self.target / "skills" / rel
            skill_root = self.target / "skills" / rel.split("/")[0]
            for resource in re.findall(r"`((?:assets|references)/[\w./-]+)`", path.read_text()):
                self.assertTrue((skill_root / resource).is_file(), rel + " references " + resource)


if __name__ == "__main__":
    unittest.main()
