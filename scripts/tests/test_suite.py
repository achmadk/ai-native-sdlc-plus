"""Unit tests for lane.py, evidence_check.py, doctor.py. Stdlib unittest only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lane import classify
from evidence_check import check as evidence_check
from doctor import check_repo

RULES = {
    "critical": ["auth/**", "**/payment*/**", "**/.github/workflows/**"],
    "standard": ["src/**", "scripts/**", "**/*.py"],
    "lite": ["docs/**", "**/*.md"],
}


class LaneTest(unittest.TestCase):
    def test_auth_filename_is_critical(self):
        rules = {"critical": ["**/*auth*"], "standard": [], "lite": []}
        lane, _ = classify([".specify/specs/auth.md"], rules)
        self.assertEqual(lane, "Critical")

    def test_typo_is_lite(self):
        lane, reason = classify(["docs/guide.md"], RULES)
        self.assertEqual(lane, "Lite")
        self.assertIn("matched", reason)

    def test_auth_is_critical(self):
        lane, _ = classify(["auth/login.py"], RULES)
        self.assertEqual(lane, "Critical")

    def test_payment_is_critical(self):
        lane, _ = classify(["src/payments/charge.py"], RULES)
        self.assertEqual(lane, "Critical")

    def test_feature_is_standard(self):
        lane, _ = classify(["src/app.py"], RULES)
        self.assertEqual(lane, "Standard")

    def test_ambiguous_escalates(self):
        lane, _ = classify(["unknown/thing.xyz"], RULES)
        self.assertIn(lane, ("Standard", "Critical"))

    def test_empty_escalates(self):
        lane, _ = classify([], RULES)
        self.assertEqual(lane, "Standard")

    def test_malformed_escalates(self):
        lane, _ = classify([""], RULES)
        self.assertEqual(lane, "Standard")

    def test_traversal_escalates(self):
        lane, _ = classify(["../etc/passwd"], RULES)
        self.assertEqual(lane, "Standard")

    def test_absolute_escalates(self):
        lane, _ = classify(["/etc/passwd"], RULES)
        self.assertEqual(lane, "Standard")


class EvidenceTest(unittest.TestCase):
    def test_lite_complete(self):
        self.assertEqual(evidence_check(
            "Lite", {"intent_block", "test_changes", "trace_block"}), [])

    def test_standard_missing_trace(self):
        missing = evidence_check(
            "Standard", {"spec_link", "test_changes", "review_notes"})
        self.assertIn("trace_block", missing)

    def test_critical_needs_rollout(self):
        missing = evidence_check("Critical", {"spec_link", "test_changes"})
        self.assertIn("rollout_plan", missing)
        self.assertIn("threat_note", missing)

    def test_lite_requires_trace(self):
        missing = evidence_check(
            "Lite", {"intent_block", "test_changes"})
        self.assertIn("trace_block", missing)

    def test_ci_exit_codes(self):
        import subprocess
        base = ["python3", "scripts/evidence_check.py", "--lane", "Standard",
                "--present", "spec_link", "test_changes"]
        local = subprocess.run(base, capture_output=True, text=True)
        self.assertEqual(local.returncode, 0)
        self.assertIn("WARNING", local.stdout)
        ci = subprocess.run(base + ["--ci"], capture_output=True, text=True)
        self.assertEqual(ci.returncode, 1)
        self.assertIn("FAIL", ci.stdout)

    def test_critical_needs_rollout(self):
        missing = evidence_check("Critical", {"spec_link", "test_changes"})
        self.assertIn("rollout_plan", missing)
        self.assertIn("threat_note", missing)


class DoctorTest(unittest.TestCase):
    def test_required_check_always_unverified(self):
        root = os.path.join(os.path.dirname(__file__), "..", "..")
        results = dict((n, (o, d)) for n, o, d in check_repo(root))
        self.assertIn("required-check", results)
        self.assertFalse(results["required-check"][0])


class SkillsLayoutTest(unittest.TestCase):
    """Guard npx skills discovery: name==dir, description present and YAML-safe."""

    def test_frontmatter_installable(self):
        import re
        root = os.path.join(os.path.dirname(__file__), "..", "..")
        skills = os.path.join(root, "skills")
        found = 0
        for entry in sorted(os.listdir(skills)):
            path = os.path.join(skills, entry, "SKILL.md")
            self.assertTrue(os.path.isfile(path), "missing %s" % path)
            text = open(path, encoding="utf-8").read()
            match = re.match(r"^---\n(.*?)\n---", text, re.S)
            self.assertIsNotNone(match, "no frontmatter in %s" % path)
            front = match.group(1)
            name = re.search(r"^name:\s*(.+)$", front, re.M)
            desc = re.search(r"^description:\s*(.+)$", front, re.M)
            self.assertIsNotNone(name, "no name in %s" % path)
            self.assertIsNotNone(desc, "no description in %s" % path)
            self.assertEqual(name.group(1).strip(), entry)
            value = desc.group(1).strip()
            if ": " in value:
                self.assertTrue(value[0] in "\"'",
                                "unquoted ': ' breaks YAML in %s" % path)
            found += 1
        self.assertGreaterEqual(found, 10, "expected at least 10 skills")


if __name__ == "__main__":
    unittest.main()
