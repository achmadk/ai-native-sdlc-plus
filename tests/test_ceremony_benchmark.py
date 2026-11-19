"""Unit and contract tests for ceremony benchmark runner and registration (WS4)."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EVALS = ROOT / "evals"
CASES_FILE = EVALS / "ceremony-cases.json"
BENCHMARK_SCRIPT = SCRIPTS / "ceremony_benchmark.py"


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(PYTHONDONTWRITEBYTECODE="1", **extra)
    return env


class CeremonyBenchmarkContractTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sdlc-bench-test-")
        self.work = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_benchmark(self, *args, cwd=None):
        cmd = [sys.executable, "-I", "-B", str(BENCHMARK_SCRIPT)] + [str(a) for a in args]
        return subprocess.run(
            cmd,
            cwd=str(cwd or self.work),
            env=clean_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )


class RegistrationValidationContract(CeremonyBenchmarkContractTestCase):
    """Task 4.1: registration validation, counting rules, and token accounting contracts."""

    def test_preregistered_ceremony_cases_file_is_valid(self):
        self.assertTrue(CASES_FILE.is_file(), "expected %s to exist" % CASES_FILE)
        data = json.loads(CASES_FILE.read_text(encoding="utf-8"))
        self.assertEqual(data.get("version"), 1)
        self.assertIn("registration_id", data)
        self.assertIn("protocol", data)
        protocol = data["protocol"]
        self.assertEqual(protocol.get("repetitions"), 3)
        self.assertIn("finite_budgets", protocol)
        budgets = protocol["finite_budgets"]
        self.assertEqual(budgets.get("Lite"), 8000)
        self.assertEqual(budgets.get("Standard"), 16000)
        self.assertEqual(budgets.get("Critical"), 24000)

        case_ids = {c["id"] for c in data.get("cases", [])}
        self.assertEqual(case_ids, {"lite-fixture", "standard-fixture", "critical-fixture"})

    def test_benchmark_script_requires_valid_registration(self):
        # When scripts/ceremony_benchmark.py is not yet implemented, or called with --help:
        self.assertTrue(BENCHMARK_SCRIPT.is_file(), "expected runner at %s" % BENCHMARK_SCRIPT)
        res_help = self.run_benchmark("--help")
        self.assertEqual(res_help.returncode, 0, res_help.stderr)
        self.assertIn("ceremony_benchmark", res_help.stdout)
        self.assertIn("--cases", res_help.stdout)

    def test_incomplete_registration_is_rejected(self):
        # Missing finite_budgets or unregistered case ID fails validation
        bad_reg = {
            "version": 1,
            "registration_id": "bad-reg",
            "protocol": {"repetitions": 1},  # missing finite_budgets!
            "cases": [],
        }
        bad_file = self.work / "bad-cases.json"
        bad_file.write_text(json.dumps(bad_reg), encoding="utf-8")

        res = self.run_benchmark("--cases", str(bad_file))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("registration error", res.stderr.lower())

    def test_missing_registration_id_is_rejected(self):
        bad_reg = {
            "version": 1,
            "protocol": {"repetitions": 1, "finite_budgets": {"Lite": 8000, "Standard": 16000, "Critical": 24000}},
            "cases": [{"id": "lite-fixture", "lane": "Lite", "token_budget": 8000}],
        }
        bad_file = self.work / "no-id-cases.json"
        bad_file.write_text(json.dumps(bad_reg), encoding="utf-8")
        res = self.run_benchmark("--cases", str(bad_file))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("missing 'registration_id'", res.stderr)

    def test_counting_rules_separate_human_approvals_from_tool_consents(self):
        # Synthetic run record with both human approvals and tool consents
        synthetic_record = {
            "case_id": "standard-fixture",
            "lane": "Standard",
            "events": [
                {"type": "tool_consent", "detail": "User allowed git status"},
                {"type": "tool_consent", "detail": "User allowed test run"},
                {"type": "human_approval", "actor": "Alice Lead", "role": "reviewer"},
            ],
            "step_timings": {"start": 0.0, "preflight": 0.5, "checks": 1.2, "complete": 2.0},
        }
        record_file = self.work / "record.json"
        record_file.write_text(json.dumps(synthetic_record), encoding="utf-8")

        res = self.run_benchmark("--record", str(record_file), "--dry-run")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertEqual(data["human_approvals"], 1)
        self.assertEqual(data["tool_consents"], 2)
        # Verify tool consents did not increment human approval count
        self.assertNotEqual(data["human_approvals"], 3)

    def test_token_accounting_requires_actual_loader_records_and_rejects_estimates(self):
        # Test that missing token provenance reports as unavailable (null), not zero or chars/4
        res = self.run_benchmark("--case", "lite-fixture", "--dry-run")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertIn("token_accounting", data)
        # Without loader provenance, loaded_tokens must be null/unavailable
        self.assertIsNone(data["token_accounting"]["loaded_tokens"])
        self.assertFalse(data["token_accounting"]["verified"])
        self.assertEqual(data["token_accounting"]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()

