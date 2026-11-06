"""Validate fault-injection anchors on the unmutated baseline only."""

from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import mutate


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
            self.assertTrue(mutate.run_tests(".", ["tests.test_lane"]))
            self.assertIn("--failfast", run.call_args[0][0])
            self.assertIn("-B", run.call_args[0][0])

    def test_focused_doctor_observers_keep_the_full_module_fallback(self):
        observers = mutate.TESTS[mutate.D]
        self.assertIn("tests.test_doctor.WorkflowChecks", observers)
        self.assertEqual(observers[-1], "tests.test_doctor")


if __name__ == "__main__":
    unittest.main()
