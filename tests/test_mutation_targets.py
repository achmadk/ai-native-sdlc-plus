"""Validate fault-injection anchors on the unmutated baseline only."""

from pathlib import Path
import contextlib
import io
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

if __package__:
    from . import mutate, support
else:
    import mutate
    import support


class MutationTargets(unittest.TestCase):
    maxDiff = None

    def test_registered_faults_match_current_implementation(self):
        root = Path(__file__).resolve().parents[1]
        sources = {path: (root / path).read_text(encoding="utf-8")
                   for path in {item[0] for item in mutate.MUTANTS}}
        stale = [(index, path, old) for index, (path, old, _, _) in enumerate(mutate.MUTANTS, 1)
                 if old not in sources[path]]
        self.assertEqual(stale, [], "update fault anchors without weakening their behavioral intent")

    def test_anchor_checks_are_not_behavioral_mutation_observers(self):
        # A removed anchor must not count as a behavioral kill of its own mutant.
        for modules in mutate.TESTS.values():
            self.assertNotIn("tests.test_mutation_targets", modules)

    def test_baseline_is_complete_and_mutation_observers_fail_fast(self):
        result = subprocess.CompletedProcess([], 0, b"", b"")
        with patch.object(mutate.subprocess, "run", return_value=result) as run:
            self.assertTrue(mutate.run_tests("."))
            self.assertNotIn("--failfast", run.call_args[0][0])
            self.assertIn("-v", run.call_args[0][0])
            self.assertTrue(mutate.run_tests(".", ["tests.test_lane"]))
            self.assertIn("--failfast", run.call_args[0][0])
            self.assertIn("-B", run.call_args[0][0])

    def test_focused_doctor_observers_keep_the_full_module_fallback(self):
        observers = mutate.TESTS[mutate.D]
        self.assertIn("tests.test_doctor.WorkflowChecks", observers)
        self.assertEqual(observers[-1], "tests.test_doctor")

    def test_failed_observer_diagnostics_are_retained_for_review(self):
        result = subprocess.CompletedProcess([], 1, b"fixture output\n", b"observer failure reason\n")
        out, err = io.StringIO(), io.StringIO()
        with patch.object(mutate.subprocess, "run", return_value=result), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertFalse(mutate.run_tests(".", ["tests.test_lane"]))
        self.assertIn("fixture output", out.getvalue())
        self.assertIn("observer failure reason", err.getvalue())

    def test_observers_import_support_from_the_copied_tree(self):
        with support.TemporaryDirectory() as directory:
            target = Path(directory, "tests")
            target.mkdir()
            for name in ("support.py", "test_support.py"):
                shutil.copy2(Path(__file__).parent / name, target / name)
            origin = subprocess.check_output(
                [sys.executable, "-B", "-c", "from tests import support; print(support.__file__)"],
                cwd=directory, text=True).strip()
            self.assertEqual(Path(origin).resolve(), (target / "support.py").resolve())
            self.assertTrue(mutate.run_tests(directory, [
                "tests.test_support.SupportContract.test_context_cleanup_runs_after_an_exception"]))


if __name__ == "__main__":
    unittest.main()
