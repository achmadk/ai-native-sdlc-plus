import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import doctor_online as do  # noqa: E402

REPO = "o/r"
CLASSIC = f"repos/{REPO}/branches/main/protection/required_status_checks"
ADMINS = f"repos/{REPO}/branches/main/protection/enforce_admins"
RULES = f"repos/{REPO}/rules/branches/main"
NOT_FOUND = (1, "", "gh: Not Found (HTTP 404)")


def fake(responses):
    """responses maps `gh api <path>` to (rc, stdout, stderr) or a JSON-able object."""

    def run(args):
        if args[0] == "api":
            value = responses.get(args[1], NOT_FOUND)
            if isinstance(value, tuple):
                return value
            return 0, json.dumps(value), ""
        raise AssertionError(f"unexpected gh call: {args}")

    return run


class VerifyTests(unittest.TestCase):
    def test_required_via_classic_protection_with_admins_enforced(self):
        run = fake({CLASSIC: {"contexts": ["gate"], "checks": []}, ADMINS: {"enabled": True}})
        code, lines = do.verify(run, REPO, "main", "gate")
        self.assertEqual(code, 0)
        self.assertIn("branch protection", lines[0])
        self.assertEqual(len(lines), 1)

    def test_checks_array_is_read(self):
        run = fake({CLASSIC: {"contexts": [], "checks": [{"context": "gate", "app_id": 1}]}, ADMINS: {"enabled": True}})
        self.assertEqual(do.verify(run, REPO, "main", "gate")[0], 0)

    def test_admin_bypass_warning(self):
        run = fake({CLASSIC: {"contexts": ["gate"]}, ADMINS: {"enabled": False}})
        code, lines = do.verify(run, REPO, "main", "gate")
        self.assertEqual(code, 0)
        self.assertTrue(any(line.startswith("WARNING") and "admins" in line for line in lines))

    def test_required_via_ruleset(self):
        rules = [
            {"type": "pull_request", "parameters": {}},
            {"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "gate"}]}},
        ]
        code, lines = do.verify(fake({RULES: rules}), REPO, "main", "gate")
        self.assertEqual(code, 0)
        self.assertIn("ruleset", lines[0])
        self.assertTrue(any(line.startswith("NOTE") for line in lines))

    def test_not_required_lists_what_is_required(self):
        run = fake({CLASSIC: {"contexts": ["lint"]}, ADMINS: {"enabled": True}})
        code, lines = do.verify(run, REPO, "main", "gate")
        self.assertEqual(code, 1)
        self.assertIn("'lint'", lines[0])

    def test_unprotected_branch(self):
        code, lines = do.verify(fake({}), REPO, "main", "gate")
        self.assertEqual(code, 1)
        self.assertTrue(any("no branch protection or ruleset" in line for line in lines))

    def test_api_error_is_not_confused_with_not_protected(self):
        run = fake({CLASSIC: (1, "", "HTTP 403: Resource not accessible")})
        with self.assertRaises(do.GhError):
            do.verify(run, REPO, "main", "gate")


class MainTests(unittest.TestCase):
    def test_resolves_repo_and_branch_via_gh(self):
        def run(args):
            if args[:2] == ["repo", "view"] and "nameWithOwner" in args:
                return 0, "o/r\n", ""
            if args[:2] == ["repo", "view"] and "defaultBranchRef" in args:
                return 0, "main\n", ""
            return fake({CLASSIC: {"contexts": ["gate"]}, ADMINS: {"enabled": True}})(args)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = do.main(["--check", "gate"], runner=run)
        self.assertEqual(rc, 0)
        self.assertIn("OK:", buf.getvalue())

    def test_gh_failure_is_exit_2(self):
        def run(args):
            return 1, "", "gh: not logged in"

        old, sys.stderr = sys.stderr, io.StringIO()
        try:
            rc = do.main(["--check", "gate"], runner=run)
        finally:
            sys.stderr = old
        self.assertEqual(rc, 2)

    def test_missing_gh_binary_is_exit_2(self):
        old, sys.stderr = sys.stderr, io.StringIO()
        try:
            rc = do.main(["--check", "gate", "--repo", REPO, "--gh", "definitely-not-a-real-gh-binary"])
        finally:
            sys.stderr = old
        self.assertEqual(rc, 2)

    def test_not_required_is_exit_1(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = do.main(["--check", "gate", "--repo", REPO, "--branch", "main"], runner=fake({}))
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
