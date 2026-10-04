import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ZERO = "0" * 40
SH = shutil.which("sh") or "/bin/sh"


def slurp(path):
    with open(path) as handle:
        return handle.read()


class HookRepo(unittest.TestCase):
    """A work repo with an origin, the gate scripts, and both hook files, on a default branch 'main'."""

    def setUp(self):
        base = tempfile.mkdtemp()
        self.origin = os.path.join(base, "origin.git")
        self.repo = os.path.join(base, "work")
        self.bin = os.path.join(base, "bin")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.origin], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", self.repo], check=True)
        for rel in ("scripts/lane.py", "scripts/evidence_check.py", "scripts/lane-config.yaml",
                    "hooks/pre-push.sh", "hooks/pre-push"):
            self.put(rel, slurp(os.path.join(ROOT, rel)), executable=rel.startswith("hooks/"))
        self.put(".gitignore", "__pycache__/\n")
        self.put("auth/login.py", "x = 1\n")
        self.put("src/app.py", "x = 1\n")
        self.put("docs/a.md", "doc\n")
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "base")
        self.g("remote", "add", "origin", self.origin)
        self.g("push", "-q", "origin", "main")
        self.g("remote", "set-head", "origin", "main")
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

    def g(self, *args, **kw):
        proc = subprocess.run(["git", "-C", self.repo, "-c", "user.email=t@t", "-c", "user.name=t"] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=kw.get("env"))
        return proc

    def put(self, rel, text, executable=False):
        full = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as handle:
            handle.write(text)
        if executable:
            os.chmod(full, 0o755)

    def branch(self, name, **files):
        """Create a branch off main with the given files (keys use __ for / and _dot_ for .); return its sha."""
        self.g("checkout", "-q", "main")
        self.g("checkout", "-q", "-b", name)
        for key, text in files.items():
            self.put(key.replace("__", "/").replace("_dot_", "."), text)
        self.g("add", "-A")
        self.g("commit", "-q", "-m", name)
        return self.g("rev-parse", "HEAD").stdout.decode().strip()

    def line(self, sha, name, local_ref=None, remote_sha=ZERO):
        return "%s %s refs/heads/%s %s\n" % (local_ref or "refs/heads/" + name, sha, name, remote_sha)

    def hook(self, stdin, env=None, script="hooks/pre-push.sh", path=None):
        run_env = dict(self.env, **(env or {}))
        if path is not None:
            run_env["PATH"] = path
        proc = subprocess.run([SH, os.path.join(self.repo, script)], cwd=self.repo, input=stdin.encode(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=run_env, timeout=60)
        return proc.returncode, proc.stdout.decode(), proc.stderr.decode()


class Reporting(HookRepo):
    def test_standard_change_without_tests_reports_lane_and_owed_evidence(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        code, out, err = self.hook(self.line(sha, "feat"))
        self.assertEqual(code, 0)
        self.assertIn("sdlc: note: lane Standard", err)
        self.assertIn("must carry: spec_link, trace_block, review_notes", err)
        self.assertIn("MISSING  test_changes", err)
        self.assertEqual(out, "")  # advice goes to stderr only

    def test_test_change_means_the_diff_checks_pass(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n", tests__test_app_dot_py="assert True\n")
        _, _, err = self.hook(self.line(sha, "feat"))
        self.assertIn("sdlc: diff checks ok for Standard", err)
        self.assertNotIn("sdlc: evidence ok", err)  # it must not claim the PR description was checked

    def test_docs_only_branch_is_lite(self):
        sha = self.branch("docs", docs__a_dot_md="changed\n")
        _, _, err = self.hook(self.line(sha, "docs"))
        self.assertIn("lane Lite", err)

    def test_critical_change_lists_critical_evidence(self):
        sha = self.branch("sec", auth__login_dot_py="x = 2\n")
        _, _, err = self.hook(self.line(sha, "sec"))
        self.assertIn("lane Critical", err)
        self.assertIn("threat_note", err)
        self.assertIn("rollout_plan", err)

    def test_classifies_the_whole_branch_not_just_the_last_push(self):
        # Two commits: the first touches auth, the second only docs. The PR gate sees both.
        self.branch("multi", auth__login_dot_py="x = 2\n")
        self.put("docs/a.md", "later\n")
        self.g("commit", "-q", "-am", "docs later")
        sha = self.g("rev-parse", "HEAD").stdout.decode().strip()
        prev = self.g("rev-parse", "HEAD~1").stdout.decode().strip()
        _, _, err = self.hook(self.line(sha, "multi", remote_sha=prev))
        self.assertIn("lane Critical", err)

    def test_every_ref_is_reported(self):
        a = self.branch("a", docs__a_dot_md="a\n")
        b = self.branch("b", auth__login_dot_py="b\n")
        _, _, err = self.hook(self.line(a, "a") + self.line(b, "b"))
        self.assertEqual(err.count("sdlc: note: lane "), 2)
        self.assertIn("lane Lite", err)
        self.assertIn("lane Critical", err)

    def test_direct_push_to_default_branch_is_called_out(self):
        self.g("checkout", "-q", "main")
        self.put("docs/a.md", "direct\n")
        self.g("commit", "-q", "-am", "direct")
        sha = self.g("rev-parse", "HEAD").stdout.decode().strip()
        _, _, err = self.hook(self.line(sha, "main", remote_sha=self.g("rev-parse", "origin/main").stdout.decode().strip()))
        self.assertIn("pushing straight to main", err)
        self.assertNotIn("lane", err)

    def test_branch_deletion_and_tags_are_ignored(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        deletion = "(delete) %s refs/heads/feat %s\n" % (ZERO, sha)
        tag = "refs/tags/v1 %s refs/tags/v1 %s\n" % (sha, ZERO)
        self.assertEqual(self.hook(deletion + tag)[2], "")

    def test_an_all_zero_local_sha_is_skipped_even_under_a_branch_ref(self):
        # Git sends "(delete)" as the local ref for deletions, so this is a defensive guard; test it directly.
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        line = "refs/heads/feat %s refs/heads/feat %s\n" % (ZERO, sha)
        self.assertEqual(self.hook(line)[2], "")

    def test_prefixes_every_line_so_it_is_attributable(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        _, _, err = self.hook(self.line(sha, "feat"))
        self.assertTrue(err.strip())
        for line in err.strip().splitlines():
            self.assertTrue(line.startswith("sdlc: "), line)

    def test_never_modifies_the_repo(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        before = self.g("status", "--porcelain").stdout
        self.hook(self.line(sha, "feat"))
        self.assertEqual(self.g("status", "--porcelain").stdout, before)


class NeverBlocks(HookRepo):
    def test_exit_zero_when_the_gate_script_crashes(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        self.put("scripts/evidence_check.py", "raise SystemExit(7)\n")
        self.assertEqual(self.hook(self.line(sha, "feat"))[0], 0)

    def test_exit_zero_and_a_visible_warning_when_the_config_is_broken(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        self.put("scripts/lane-config.yaml", "version: 1\ncritcal:\n  - x\n")
        code, _, err = self.hook(self.line(sha, "feat"))
        self.assertEqual(code, 0)
        self.assertIn("tooling error", err)

    def test_missing_gate_scripts_are_reported_not_fatal(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        os.remove(os.path.join(self.repo, "scripts/evidence_check.py"))
        code, _, err = self.hook(self.line(sha, "feat"))
        self.assertEqual(code, 0)
        self.assertIn("gate scripts not found", err)

    def test_missing_python_is_reported_not_fatal(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        os.makedirs(self.bin)
        for tool in ("git", "sed"):
            os.symlink(shutil.which(tool), os.path.join(self.bin, tool))
        code, _, err = self.hook(self.line(sha, "feat"), path=self.bin)
        self.assertEqual(code, 0)
        self.assertIn("python3 not found; lane check skipped", err)

    def test_no_merge_base_is_reported_not_fatal(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        self.g("update-ref", "-d", "refs/remotes/origin/main")
        self.g("remote", "set-head", "origin", "-d")
        code, _, err = self.hook(self.line(sha, "feat"))
        self.assertEqual(code, 0)
        self.assertIn("no merge-base with the default branch for feat", err)

    def test_branch_names_with_shell_metacharacters_are_inert(self):
        # Refs cannot contain spaces, but $(...), backticks and ${IFS} are all legal. They must stay data.
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        self.g("update-ref", "-d", "refs/remotes/origin/main")
        self.g("remote", "set-head", "origin", "-d")
        for index, evil in enumerate(("x$(touch${IFS}PWNED1)", "x`touch${IFS}PWNED2`", "x;touch${IFS}PWNED3")):
            self.assertEqual(self.g("check-ref-format", "--branch", evil).returncode, 0, evil)  # a legal name
            line = "refs/heads/feat %s refs/heads/%s %s\n" % (sha, evil, ZERO)
            code, _, err = self.hook(line)
            self.assertEqual(code, 0)
            self.assertIn(evil, err)  # printed back as plain data
            self.assertFalse(os.path.exists(os.path.join(self.repo, "PWNED%d" % (index + 1))), evil)

    def test_children_cannot_eat_the_ref_list(self):
        # A child that reads stdin must not swallow the refs that follow. Use a python3 that does exactly that.
        a = self.branch("a", docs__a_dot_md="a\n")
        b = self.branch("b", docs__a_dot_md="b\n")
        os.makedirs(self.bin)
        fake = os.path.join(self.bin, "python3")
        with open(fake, "w") as handle:
            handle.write("#!/bin/sh\ncat >/dev/null\necho FAKE-GATE-RAN\n")
        os.chmod(fake, 0o755)
        code, _, err = self.hook(self.line(a, "a") + self.line(b, "b"), path=self.bin + os.pathsep + os.environ["PATH"])
        self.assertEqual(code, 0)
        self.assertEqual(err.count("FAKE-GATE-RAN"), 2)

    def test_interactive_terminal_does_not_hang(self):
        import pty
        master, slave = pty.openpty()
        try:
            proc = subprocess.run([SH, os.path.join(self.repo, "hooks/pre-push.sh")], cwd=self.repo, stdin=slave,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, env=self.env)
        finally:
            os.close(master)
            os.close(slave)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("run this through 'git push'", proc.stderr.decode())

    def test_dispatcher_never_blocks_even_if_the_target_is_missing(self):
        os.remove(os.path.join(self.repo, "hooks/pre-push.sh"))
        self.assertEqual(self.hook("", script="hooks/pre-push")[0], 0)


class Silencing(HookRepo):
    def test_env_var_silences(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        self.assertEqual(self.hook(self.line(sha, "feat"), env={"SDLC_HOOK": "off"})[2], "")

    def test_git_config_silences(self):
        sha = self.branch("feat", src__app_dot_py="x = 2\n")
        self.g("config", "sdlc.hook", "off")
        self.assertEqual(self.hook(self.line(sha, "feat"))[2], "")


class RealPushes(HookRepo):
    def push(self, *refspecs):
        return subprocess.run(["git", "-C", self.repo, "push", "origin"] + list(refspecs), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=self.env)

    def test_core_hookspath_runs_the_dispatcher_and_the_push_succeeds(self):
        self.branch("feat", auth__login_dot_py="x = 2\n")
        self.g("config", "core.hooksPath", "hooks")
        proc = self.push("feat")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn("sdlc: note: lane Critical", proc.stderr.decode())

    def test_dot_sh_file_alone_is_never_run_by_git(self):
        # The pitfall that made the original hook inert under core.hooksPath.
        self.branch("feat", auth__login_dot_py="x = 2\n")
        self.g("config", "core.hooksPath", "hooks")
        os.remove(os.path.join(self.repo, "hooks/pre-push"))
        proc = self.push("feat")
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("sdlc:", proc.stderr.decode())

    def test_copying_the_dot_sh_into_git_hooks_works_standalone(self):
        self.branch("feat", auth__login_dot_py="x = 2\n")
        dest = os.path.join(self.repo, ".git", "hooks", "pre-push")
        shutil.copy(os.path.join(self.repo, "hooks/pre-push.sh"), dest)
        os.chmod(dest, 0o755)
        proc = self.push("feat")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("sdlc: note: lane Critical", proc.stderr.decode())

    def test_push_succeeds_even_when_the_gate_is_broken(self):
        self.branch("feat", auth__login_dot_py="x = 2\n")
        self.g("config", "core.hooksPath", "hooks")
        self.put("scripts/evidence_check.py", "raise SystemExit(7)\n")
        self.assertEqual(self.push("feat").returncode, 0)

    def test_works_under_every_posix_shell_available(self):
        sha = self.branch("feat", auth__login_dot_py="x = 2\n")
        tried = 0
        for shell in ("dash", "bash", "sh", "ash"):
            path = shutil.which(shell)
            if not path:
                continue
            tried += 1
            proc = subprocess.run([path, os.path.join(self.repo, "hooks/pre-push.sh")], cwd=self.repo,
                                  input=self.line(sha, "feat").encode(), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env=self.env, timeout=60)
            self.assertEqual(proc.returncode, 0, shell)
            self.assertIn("lane Critical", proc.stderr.decode(), shell)
        self.assertGreater(tried, 0)


if __name__ == "__main__":
    unittest.main()
