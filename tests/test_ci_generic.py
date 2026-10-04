import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPT = os.path.join(ROOT, "skills", "ai-sdlc", "assets", "ci-generic.sh")
SH = shutil.which("sh") or "/bin/sh"
GOOD_LITE = ("## Intent\nFix a typo in the install guide so the command can be copied.\n\n"
             "## Trace\nUsed an agent to find the typo; kept the change minimal on purpose.\n")


def slurp(path):
    with open(path) as handle:
        return handle.read()


class CiRepo(unittest.TestCase):
    """A repo whose base commit carries the gate tooling, with a PR branch on top."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.tmp = tempfile.mkdtemp()           # isolated TMPDIR so leftovers are detectable
        self.body = os.path.join(self.tmp, "body.md")
        self.g("init", "-q", "-b", "main")
        for rel in ("scripts/lane.py", "scripts/evidence_check.py", "scripts/lane-config.yaml"):
            self.put(rel, slurp(os.path.join(ROOT, rel)))
        self.put(".gitignore", "__pycache__/\n")
        self.put("docs/a.md", "doc\n")
        self.put("auth/login.py", "x = 1\n")
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "base")
        self.base = self.g("rev-parse", "HEAD").strip()
        self.g("checkout", "-q", "-b", "pr")

    def g(self, *args):
        return subprocess.run(["git", "-C", self.repo, "-c", "user.email=t@t", "-c", "user.name=t"] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.decode()

    def put(self, rel, text):
        full = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as handle:
            handle.write(text)

    def commit(self):
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "change")
        return self.g("rev-parse", "HEAD").strip()

    def run_script(self, base=None, head=None, body=GOOD_LITE, env=None, shell=SH):
        if body is not None:
            with open(self.body, "w") as handle:
                handle.write(body)
        run_env = dict(os.environ, TMPDIR=self.tmp, PYTHONDONTWRITEBYTECODE="1")
        for key, value in (("SDLC_BASE", base or self.base), ("SDLC_HEAD", head or self.g("rev-parse", "HEAD").strip()),
                           ("SDLC_PR_BODY_FILE", self.body)):
            run_env[key] = value
        run_env.update(env or {})
        proc = subprocess.run([shell, SCRIPT], cwd=self.repo, env=run_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        return proc.returncode, proc.stdout.decode(), proc.stderr.decode()


class Outcomes(CiRepo):
    def test_a_docs_change_with_real_evidence_passes(self):
        self.put("docs/a.md", "fixed\n")
        self.commit()
        code, out, err = self.run_script()
        self.assertEqual(code, 0, out + err)
        self.assertIn("evidence ok for Lite", out)

    def test_missing_evidence_fails_closed(self):
        self.put("docs/a.md", "fixed\n")
        self.commit()
        code, out, _ = self.run_script(body="")
        self.assertEqual(code, 1)
        self.assertIn("FAIL: missing evidence for Lite", out)

    def test_the_lane_comes_from_the_diff(self):
        self.put("auth/login.py", "x = 2\n")
        self.commit()
        code, out, _ = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("missing evidence for Critical", out)


class TamperResistance(CiRepo):
    def test_a_pr_that_neuters_the_gate_script_still_fails(self):
        self.put("auth/login.py", "x = 2\n")
        self.put("scripts/evidence_check.py", "import sys\nsys.exit(0)\n")   # the attacker's version always passes
        self.commit()
        code, out, _ = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("missing evidence for Critical", out)

    def test_a_pr_that_downgrades_the_lane_config_still_fails(self):
        self.put("scripts/lane-config.yaml", 'version: 1\nlite:\n  - "**"\n')
        self.put("auth/login.py", "x = 2\n")
        self.commit()
        code, out, _ = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("Critical", out)

    def test_editing_the_gate_itself_is_critical(self):
        self.put("scripts/lane.py", slurp(os.path.join(ROOT, "scripts/lane.py")) + "\n# harmless comment\n")
        self.commit()
        code, out, _ = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("Critical", out)


class ConfigIsTrusted(CiRepo):
    def test_a_pr_cannot_widen_the_test_patterns_to_satisfy_test_evidence(self):
        # Lane math is protected by the built-in Critical rule for the config file, but the "tests:" and
        # "non_executable:" sections are NOT lane math. Reading the PR's own config would let it declare any file a test.
        self.put("docs/spec.md", "# spec\n")
        self.put("docs/intent.md", "# intent\n")
        self.put("auth/login.py", "x = 2\n")
        config = slurp(os.path.join(ROOT, "scripts/lane-config.yaml")) + '\ntests:\n  - "**"\n'
        self.put("scripts/lane-config.yaml", config)
        self.commit()
        filled = "a real sentence with enough characters to count as content here"
        body = ("## Intent\n%s\n\nSpec: docs/spec.md\nIntent link: docs/intent.md\n\n## Trace\n%s\n\n## Review notes\n%s\n\n"
                "## Threat note\n%s\n\n## Rollout plan\n%s\n" % ((filled,) * 5))
        code, out, _ = self.run_script(body=body)
        self.assertEqual(code, 1, out)
        self.assertIn("missing evidence for Critical: test_changes", out)


class SetupErrors(CiRepo):
    def test_missing_or_empty_inputs(self):
        self.put("docs/a.md", "x\n")
        self.commit()
        for name in ("SDLC_BASE", "SDLC_HEAD", "SDLC_PR_BODY_FILE"):
            code, _, err = self.run_script(env={name: ""})
            self.assertEqual(code, 2, name)
            self.assertIn("set SDLC_BASE, SDLC_HEAD and SDLC_PR_BODY_FILE", err)

    def test_unset_variables_are_handled_under_set_u(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("SDLC_")}
        proc = subprocess.run([SH, SCRIPT], cwd=self.repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("set SDLC_BASE", proc.stderr.decode())

    def test_bad_shas(self):
        self.put("docs/a.md", "x\n")
        self.commit()
        for value, fragment in (("main", "not a commit SHA"), ("abc123", "need a full commit SHA"),
                                ("--output=/tmp/x", "not a commit SHA"), ("G" * 40, "not a commit SHA")):
            code, _, err = self.run_script(base=value)
            self.assertEqual(code, 2, value)
            self.assertIn(fragment, err)

    def test_missing_body_file(self):
        self.put("docs/a.md", "x\n")
        self.commit()
        code, _, err = self.run_script(env={"SDLC_PR_BODY_FILE": "/nonexistent/body.md"}, body=None)
        self.assertEqual(code, 2)
        self.assertIn("PR description file not found", err)

    def test_a_base_commit_that_is_not_in_the_checkout(self):
        self.put("docs/a.md", "x\n")
        self.commit()
        code, _, err = self.run_script(base="0123456789abcdef0123456789abcdef01234567")
        self.assertEqual(code, 2)
        self.assertIn("base commit not in this checkout", err)

    def test_a_base_without_the_tooling_is_a_tooling_error(self):
        self.g("checkout", "-q", "--orphan", "bare")
        self.g("rm", "-rq", "--cached", ".")
        for rel in ("scripts", "auth", ".gitignore"):
            path = os.path.join(self.repo, rel)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        self.put("README.md", "no tooling here\n")
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "no tooling")
        bare = self.g("rev-parse", "HEAD").strip()
        self.put("docs/a.md", "x\n")
        head = self.commit()
        code, _, err = self.run_script(base=bare, head=head)
        self.assertEqual(code, 3)
        self.assertIn("the base commit has no usable scripts/", err)

    def test_python_missing(self):
        self.put("docs/a.md", "x\n")
        self.commit()
        bindir = tempfile.mkdtemp()
        for tool in ("git", "tar", "mktemp", "rm", "dirname", "cat"):
            found = shutil.which(tool)
            if found:
                os.symlink(found, os.path.join(bindir, tool))
        code, _, err = self.run_script(env={"PATH": bindir})
        self.assertEqual(code, 2)
        self.assertIn("python3 not found", err)


class Hygiene(CiRepo):
    def test_it_cleans_up_after_itself_and_never_writes_into_the_repo(self):
        self.put("docs/a.md", "fixed\n")
        self.commit()
        before = self.g("status", "--porcelain")
        self.run_script()
        self.run_script(body="")                      # failing runs clean up too
        self.assertEqual(os.listdir(self.tmp), ["body.md"])
        self.assertEqual(self.g("status", "--porcelain"), before)

    def test_it_runs_under_every_posix_shell_available(self):
        self.put("docs/a.md", "fixed\n")
        self.commit()
        tried = 0
        for name in ("dash", "bash", "sh", "ash"):
            shell = shutil.which(name)
            if shell:
                tried += 1
                code, out, err = self.run_script(shell=shell)
                self.assertEqual(code, 0, "%s: %s%s" % (name, out, err))
        self.assertGreater(tried, 0)

    def test_the_script_is_syntactically_valid_for_dash_and_bash(self):
        for name in ("dash", "bash"):
            shell = shutil.which(name)
            if shell:
                self.assertEqual(subprocess.run([shell, "-n", SCRIPT]).returncode, 0, name)


if __name__ == "__main__":
    unittest.main()
