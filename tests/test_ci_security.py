"""Exercise the actual gate entry points without executing candidate tooling."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

if __package__:
    from . import support
else:
    import support

ROOT = Path(__file__).resolve().parents[1]
SH = support.find_shell()
RUNNER = ROOT / "skills/ai-sdlc/assets/ci-generic.sh"
GATE_WORKFLOW = ROOT / ".github/workflows/sdlc-gate.yml"
SCAN_WORKFLOW = ROOT / ".github/workflows/gitleaks.yml"


class TrustedExecution(unittest.TestCase):
    def setUp(self):
        self.directory = support.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.repo = self.root / "candidate"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        scripts = self.repo / "scripts"
        scripts.mkdir()
        for name in ("lane.py", "lane-config.yaml", "evidence_check.py"):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        (self.repo / "docs").mkdir()
        (self.repo / "docs/guide.md").write_text("base\n", encoding="utf-8")
        self.body = self.root / "body.md"
        self.body.write_text("", encoding="utf-8")

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Fixture",
                                 "-c", "user.email=fixture@example.invalid", *args],
                                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode().strip()

    def prepare(self, module=None, weaken_head=False):
        if module:
            (self.repo / "scripts" / (module + ".py")).write_text("raise SystemExit(0)\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "trusted baseline")
        self.base = self.git("rev-parse", "HEAD")
        self.trusted = self.root / "trusted"
        shutil.copytree(self.repo / "scripts", self.trusted / "scripts")
        (self.repo / "docs/guide.md").write_text("changed\n", encoding="utf-8")
        if weaken_head:
            (self.repo / "scripts/evidence_check.py").write_text("print('FORGED-GREEN')\n", encoding="utf-8")
            (self.repo / "scripts/lane-config.yaml").write_text('version: 1\nlite:\n  - "**"\n', encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "candidate")
        self.head = self.git("rev-parse", "HEAD")

    def execute(self, generic=False, ambient=False, user_site=False, unisolated=False):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env.pop("GITHUB_EVENT_PATH", None)
        env.pop("GITHUB_STEP_SUMMARY", None)
        if ambient:
            directory = self.root / "ambient"
            directory.mkdir(exist_ok=True)
            (directory / "json.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
            env.update(PYTHONPATH=str(directory), PYTHONUSERBASE=str(directory))
        if user_site:
            directory = self.root / "user-site"
            env["PYTHONUSERBASE"] = str(directory)
            env.pop("PYTHONNOUSERSITE", None)
            # Framework builds on macOS use a different user-site layout.
            probe = subprocess.run([sys.executable, "-B", "-S", "-c",
                                    "import site; print(site.getusersitepackages())"],
                                   env=env, check=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
            packages = Path(probe.stdout.strip())
            packages.mkdir(parents=True, exist_ok=True)
            (packages / "injection.pth").write_text("import os; os._exit(0)\n", encoding="utf-8")
        if generic:
            env = support.shell_environment(self.root / "shell-bin", env)
            env.update(SDLC_BASE=self.base, SDLC_HEAD=self.head, SDLC_REPO_ROOT=str(self.repo),
                       SDLC_PR_BODY_FILE=support.shell_path(self.body))
            command = [SH, support.shell_path(RUNNER)]
        else:
            command = [sys.executable, "-B"]
            if not unisolated and "python3 -I trusted/scripts/evidence_check.py" in GATE_WORKFLOW.read_text(encoding="utf-8"):
                command.append("-I")
            command += [str(self.trusted / "scripts/evidence_check.py"), "--ci",
                        "--config", str(self.trusted / "scripts/lane-config.yaml"),
                        "--repo-root", str(self.repo), "--base", self.base, "--head", self.head,
                        "--pr-body-file", str(self.body)]
        return subprocess.run(command, cwd=self.repo, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, timeout=30)

    def assert_gate_rejected(self, result, lane="Lite"):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("missing evidence for " + lane, result.stdout)
        self.assertNotIn("FORGED-GREEN", result.stdout)

    def test_github_adjacent_stdlib_module_cannot_short_circuit(self):
        self.prepare(module="json")
        self.assert_gate_rejected(self.execute())

    def test_github_late_import_cannot_short_circuit(self):
        self.prepare(module="unicodedata")
        self.assert_gate_rejected(self.execute())

    def test_github_ambient_python_path_is_ignored(self):
        self.prepare()
        self.assert_gate_rejected(self.execute(ambient=True))

    def test_github_user_site_startup_code_is_ignored(self):
        self.prepare()
        control = self.execute(user_site=True, unisolated=True)
        if control.returncode != 0 or "missing evidence" in control.stdout:
            self.skipTest("user site is disabled in this interpreter; injection control unavailable")
        self.assert_gate_rejected(self.execute(user_site=True))

    @unittest.skipUnless(SH, support.SHELL_REQUIRED)
    def test_generic_adjacent_stdlib_module_cannot_short_circuit(self):
        self.prepare(module="json")
        self.assert_gate_rejected(self.execute(generic=True))

    @unittest.skipUnless(SH, support.SHELL_REQUIRED)
    def test_generic_late_import_cannot_short_circuit(self):
        self.prepare(module="unicodedata")
        self.assert_gate_rejected(self.execute(generic=True))

    @unittest.skipUnless(SH, support.SHELL_REQUIRED)
    def test_generic_ambient_python_path_is_ignored(self):
        self.prepare()
        self.assert_gate_rejected(self.execute(generic=True, ambient=True))

    @unittest.skipUnless(SH, support.SHELL_REQUIRED)
    def test_generic_user_site_startup_code_is_ignored(self):
        self.prepare()
        control = self.execute(user_site=True, unisolated=True)
        if control.returncode != 0 or "missing evidence" in control.stdout:
            self.skipTest("user site is disabled in this interpreter; injection control unavailable")
        self.assert_gate_rejected(self.execute(generic=True, user_site=True))

    def test_github_candidate_cannot_replace_base_checker_or_policy(self):
        self.prepare(weaken_head=True)
        self.assert_gate_rejected(self.execute(), "Critical")

    @unittest.skipUnless(SH, support.SHELL_REQUIRED)
    def test_generic_candidate_cannot_replace_base_checker_or_policy(self):
        self.prepare(weaken_head=True)
        self.assert_gate_rejected(self.execute(generic=True), "Critical")

    @unittest.skipUnless(SH, support.SHELL_REQUIRED)
    def test_generic_candidate_cannot_inject_spec_inputs_helper(self):
        self.prepare()
        helper = self.repo / "skills/spec-first/scripts/spec_inputs.py"
        helper.parent.mkdir(parents=True, exist_ok=True)
        helper.write_text("raise SystemExit(0)\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "candidate injects helper")
        self.head = self.git("rev-parse", "HEAD")
        self.assert_gate_rejected(self.execute(generic=True), "Critical")

    @unittest.skipUnless(SH, support.SHELL_REQUIRED)
    def test_generic_candidate_cannot_replace_base_spec_inputs(self):
        helper_base = self.repo / "skills/spec-first/scripts/spec_inputs.py"
        helper_base.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "skills/spec-first/scripts/spec_inputs.py", helper_base)
        self.prepare()
        helper_base.write_text("raise SystemExit(0)\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "candidate weakens helper")
        self.head = self.git("rev-parse", "HEAD")
        self.assert_gate_rejected(self.execute(generic=True), "Critical")


class WorkflowContract(unittest.TestCase):
    def test_windows_job_executes_native_install_and_dispatch_contracts(self):
        text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = re.search(r"(?ms)^  windows-install:\n(.*?)(?=^  [\w-]+:|\Z)", text)
        self.assertIsNotNone(job, "focused Windows installation job must remain")
        for expected in ("runs-on: windows-latest", 'python: ["3.8", "3.13"]', "shell: pwsh",
                         "python -B tests/test_install.py PowerShellInstallation FilesystemSafety -v",
                         "exit $LASTEXITCODE"):
            self.assertIn(expected, job.group(1))

    def test_windows_full_suite_retains_verbose_verdicts_and_python_floor(self):
        text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = re.search(r"(?ms)^  windows-test:\n(.*?)(?=^  [\w-]+:|\Z)", text)
        self.assertIsNotNone(job, "full Windows suite must run separately from the focused job")
        for expected in ("runs-on: windows-latest", 'python: ["3.8", "3.13"]', "shell: pwsh",
                         "python -B -m unittest discover -s tests -v", "exit $LASTEXITCODE",
                         'PYTHONDONTWRITEBYTECODE: "1"', "fail-fast: false"):
            self.assertIn(expected, job.group(1))
        self.assertRegex(job.group(1), r"timeout-minutes:\s*45\b")
        self.assertNotRegex(job.group(1), r"(?m)^\s*(?:if|continue-on-error):")
        for entry in ('{os: ubuntu-latest, python: "3.10"}', '{os: ubuntu-latest, python: "3.12"}',
                      '{os: ubuntu-latest, python: "3.13"}', '{os: macos-latest, python: "3.12"}'):
            self.assertIn(entry, text)

    def test_all_enforcement_actions_have_full_immutable_pins(self):
        for path in (GATE_WORKFLOW, SCAN_WORKFLOW):
            with self.subTest(path=path.name):
                uses = re.findall(r"(?m)^\s*(?:- )?uses:\s*([^\s#]+)", path.read_text(encoding="utf-8"))
                self.assertTrue(uses)
                for occurrence, action in enumerate(uses, 1):
                    with self.subTest(occurrence=occurrence, action=action):
                        self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")

    def test_every_checkout_disables_persisted_credentials(self):
        for path in (GATE_WORKFLOW, SCAN_WORKFLOW):
            for step in re.split(r"(?m)^      - ", path.read_text(encoding="utf-8")):
                if re.search(r"uses:\s*actions/checkout@", step):
                    with self.subTest(path=path.name, step=step.splitlines()[0]):
                        self.assertRegex(step, r"persist-credentials:\s*false\b")

    def test_scanner_supplies_token_and_disables_comments(self):
        text = SCAN_WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^\s+GITHUB_TOKEN:\s*\$\{\{\s*secrets\.GITHUB_TOKEN\s*\}\}")
        self.assertRegex(text, r"(?m)^\s+GITLEAKS_ENABLE_COMMENTS:\s*['\"]?false['\"]?\s*$")
        self.assertRegex(text, r"(?m)^  pull-requests:\s*read\s*$")
        self.assertRegex(text, r"(?m)^\s+GITLEAKS_LICENSE:\s*\$\{\{\s*secrets\.GITLEAKS_LICENSE\s*\}\}")

    def test_enforcement_is_read_only_and_does_not_ignore_failures(self):
        for path in (GATE_WORKFLOW, SCAN_WORKFLOW):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotRegex(text, r"(?m)^\s*[A-Za-z-]+:\s*write\s*$")
                self.assertNotRegex(text, r"(?m)^\s*pull_request_target:")
                self.assertNotRegex(text, r"(?m)^\s*(?:if|continue-on-error):")
                self.assertNotIn("|| true", text)
        gate = GATE_WORKFLOW.read_text(encoding="utf-8")
        for event in ("opened", "synchronize", "reopened", "edited", "ready_for_review"):
            self.assertIn(event, gate)
        self.assertIn("python3 -I trusted/scripts/evidence_check.py --ci", gate)
        self.assertIn("--config trusted/scripts/lane-config.yaml", gate)
        self.assertIn(' --head="$HEAD_SHA"', gate)
        self.assertRegex(gate, r"timeout-minutes:\s*5\b")


if __name__ == "__main__":
    unittest.main()
