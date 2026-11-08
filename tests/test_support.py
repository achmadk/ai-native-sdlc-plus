"""Contracts for fixtures shared by native and POSIX test runs."""

import importlib
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import unittest
from unittest import mock


class SupportContract(unittest.TestCase):
    def setUp(self):
        name = (__package__ + ".support") if __package__ else "support"
        self.assertIsNotNone(importlib.util.find_spec(name),
                             "shared shell, cleanup, capability and native-command support is required")
        self.support = importlib.import_module(name)
        self.directory = self.support.TemporaryDirectory(prefix="sdlc-support-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_read_only_git_objects_are_removed(self):
        repo = self.root / "repository"
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
                       input=b"fixture blob\n", check=True, capture_output=True)
        objects = [path for path in (repo / ".git/objects").rglob("*") if path.is_file()]
        self.assertTrue(objects)
        for path in objects:
            path.chmod(stat.S_IREAD)
        self.support.remove_tree(repo)
        self.assertFalse(repo.exists())
        self.support.remove_tree(repo)

    def test_context_cleanup_runs_after_an_exception(self):
        with self.assertRaisesRegex(RuntimeError, "fixture failure"):
            with self.support.TemporaryDirectory(dir=self.root) as directory:
                Path(directory, "readonly").write_bytes(b"temporary")
                Path(directory, "readonly").chmod(stat.S_IREAD)
                raise RuntimeError("fixture failure")
        self.assertFalse(Path(directory).exists())

    def test_read_only_and_unreadable_directories_are_removed(self):
        for mode in (0o500, 0o000):
            with self.subTest(mode=oct(mode)):
                tree = self.root / ("protected-%o" % mode)
                child = tree / "nested"
                child.mkdir(parents=True)
                (child / "readonly").write_bytes(b"fixture")
                (child / "readonly").chmod(stat.S_IREAD)
                child.chmod(mode)
                tree.chmod(mode)
                try:
                    try:
                        self.support.remove_tree(tree)
                    except Exception as exc:
                        self.fail("protected directory cleanup must complete: %r" % exc)
                finally:
                    if tree.exists():
                        tree.chmod(0o700)
                        if child.exists():
                            child.chmod(0o700)
                self.assertFalse(tree.exists())

    @unittest.skipUnless(shutil.rmtree.avoids_symlink_attacks, "fd-based rmtree unavailable")
    def test_failed_directory_open_retries_the_deletion_not_the_open_call(self):
        tree = self.root / "open-retry"
        tree.mkdir()
        (tree / "file").write_bytes(b"fixture")
        real_open = os.open
        denied = []

        def deny_once(*args, **kwargs):
            if not denied:
                denied.append(True)
                raise PermissionError("simulated directory open failure")
            return real_open(*args, **kwargs)

        with mock.patch.object(os, "open", side_effect=deny_once):
            try:
                self.support.remove_tree(tree)
            except Exception as exc:
                self.fail("directory-open recovery must finish deletion: %r" % exc)
        self.assertTrue(denied)
        self.assertFalse(tree.exists())

    def test_directory_symlink_cleanup_does_not_touch_its_target(self):
        self.support.require_symlinks(directory=True)
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_bytes(b"keep")
        tree = self.root / "tree"
        tree.mkdir()
        (tree / "link").symlink_to(outside, target_is_directory=True)
        self.support.remove_tree(tree)
        self.assertEqual(sentinel.read_bytes(), b"keep")
        for index, suffix in enumerate(("", os.sep, os.sep + ".")):
            with self.subTest(suffix=suffix):
                sentinel.write_bytes(b"keep")
                link = self.root / ("root-link-%s" % index)
                link.symlink_to(outside, target_is_directory=True)
                try:
                    self.support.remove_tree(str(link) + suffix)
                except OSError as exc:
                    self.fail("root link cleanup must not traverse its target: %r" % exc)
                self.assertEqual(sentinel.read_bytes(), b"keep")

    @unittest.skipUnless(os.name == "nt", "Windows junction capability")
    def test_junction_cleanup_does_not_traverse_nested_or_root_links(self):
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_bytes(b"keep")
        tree = self.root / "tree"
        tree.mkdir()
        for link in (tree / "nested", self.root / "root-junction"):
            self.support.make_junction(link, outside)
        self.support.remove_tree(tree)
        self.assertEqual(sentinel.read_bytes(), b"keep")
        self.support.remove_tree(str(self.root / "root-junction") + os.sep)
        self.assertEqual(sentinel.read_bytes(), b"keep")

    @unittest.skipUnless(os.name == "nt", "Windows junction capability")
    def test_junction_fixture_errors_are_not_capability_skips(self):
        result = subprocess.CompletedProcess([], 1, "", "invalid fixture destination")
        with mock.patch.object(self.support.subprocess, "run", return_value=result):
            try:
                with self.assertRaisesRegex(RuntimeError, "junction fixture creation failed"):
                    self.support.make_junction(self.root / "link", self.root)
            except unittest.SkipTest:
                self.fail("junction fixture errors must not be hidden as capability skips")

    def test_discovered_shell_can_read_a_native_path_with_spaces(self):
        shell = self.support.find_shell()
        if shell is None:
            self.skipTest(self.support.SHELL_REQUIRED)
        script = self.root / "shell fixture.sh"
        script.write_bytes(b"printf '%s' \"$1\"\n")
        result = subprocess.run([shell, self.support.shell_path(script), "two words"],
                                capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stdout), (0, "two words"), result.stderr)
        if os.name == "nt":
            git_root = Path(shutil.which("git")).resolve().parent.parent
            self.assertIn(git_root, Path(shell).resolve().parents)

    def test_missing_shell_is_not_replaced_with_a_nonexistent_default(self):
        self.assertIsNone(self.support.find_shell("sdlc-no-such-shell"))

    def test_native_fake_command_preserves_arguments_stdin_and_exit_status(self):
        directory = self.root / "command fixture"
        command = self.support.fake_command(
            directory, "fixture-command",
            "import json, sys\n"
            "print(json.dumps([sys.argv[1:], sys.stdin.read()]))\n"
            "sys.stderr.write('fixture stderr')\n"
            "sys.exit(7)\n")
        arguments = ["two words", "C:\\path\\with spaces\\", 'quoted"value', ""]
        env = dict(os.environ, PATH=str(directory) + os.pathsep + os.environ.get("PATH", ""))
        invocation = command if os.name == "nt" else ["fixture-command"]
        with mock.patch.dict(os.environ, env):
            result = subprocess.run(invocation + arguments, env=env, input="input text",
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        import json
        self.assertEqual(json.loads(result.stdout), [arguments, "input text"])
        self.assertEqual(result.stderr, "fixture stderr")
        self.assertTrue(Path(command[0]).is_file())
        if os.name == "nt":
            self.assertEqual(command, [sys.executable, "-B", str(directory / "fixture-command.py")])
        else:
            self.assertEqual(command, [str(directory / "fixture-command")])

    @unittest.skipUnless(os.name == "nt", "Windows command fixture")
    def test_windows_fake_command_needs_no_compiler_or_generated_executable(self):
        with mock.patch.object(self.support.subprocess, "run",
                               side_effect=AssertionError("fixture construction must not launch processes")), \
                mock.patch.object(self.support.shutil, "copy2",
                                  side_effect=AssertionError("fixtures must not copy executables")):
            command = self.support.fake_command(self.root, "fixture", "raise SystemExit(0)\n")
        self.assertEqual(command, [sys.executable, "-B", str(self.root / "fixture.py")])
        self.assertEqual(list(self.root.iterdir()), [self.root / "fixture.py"])

    def test_shell_environment_uses_the_test_interpreter(self):
        shell = self.support.find_shell()
        if shell is None:
            self.skipTest(self.support.SHELL_REQUIRED)
        env = self.support.shell_environment(self.root)
        result = subprocess.run([shell, "-c", "python3 -c 'import sys; print(sys.executable)'"],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), Path(sys.executable).resolve())

    def test_filename_probe_cannot_accept_an_alternate_data_stream(self):
        if os.name == "nt":
            with self.assertRaisesRegex(unittest.SkipTest, "literal filename"):
                self.support.require_filename("fixture:stream")
        else:
            self.support.require_filename("fixture:stream")

    def test_command_text_roundtrips_the_host_parser(self):
        spec = importlib.util.spec_from_file_location(
            "support_redgreen_subject",
            str(Path(__file__).resolve().parents[1] / "skills/verify-and-evals/scripts/redgreen.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        arguments = [sys.executable, "-c", "print('two words')", "space here", ""]
        self.assertEqual(module.split_command(self.support.command_text(arguments)), arguments)


if __name__ == "__main__":
    unittest.main()
