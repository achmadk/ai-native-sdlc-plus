"""Contracts for aggregate offline verification and revision-bound receipts."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
VERIFY_ALL = ROOT / "scripts" / "verify_all.py"


def sha256(value):
    return hashlib.sha256(value).hexdigest()


class VerifyAllContract(unittest.TestCase):
    def module(self):
        self.assertTrue(VERIFY_ALL.is_file(), "expected aggregate verifier at %s" % VERIFY_ALL)
        spec = importlib.util.spec_from_file_location("verify_all_under_test", str(VERIFY_ALL))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_plan_uses_fixed_trusted_argv_and_finite_timeouts(self):
        module = self.module()
        plan = module.fixed_plan(str(ROOT), sys.executable, str(ROOT / "evals/loader-record.json"))
        self.assertEqual([stage["name"] for stage in plan], ["unit", "mutation", "doctor", "footprint"])
        for stage in plan:
            self.assertGreater(stage["timeout"], 0)
            self.assertLessEqual(stage["timeout"], 7200)
            if stage["kind"] == "subprocess":
                self.assertIsInstance(stage["command"], list)
                self.assertEqual(stage["command"][0], sys.executable)
                self.assertNotIn("shell", stage)
            else:
                self.assertEqual(stage["kind"], "footprint")

    def test_failure_is_retained_and_later_stages_are_skipped(self):
        module = self.module()
        plan = [{"name": name, "kind": "test", "timeout": 1} for name in
                ("unit", "mutation", "doctor", "footprint")]

        def runner(stage):
            if stage["name"] == "mutation":
                return {"name": "mutation", "status": "fail", "exit_code": 1,
                        "duration_ms": 2, "counts": {}, "limitations": ["fixture failure"]}
            return {"name": stage["name"], "status": "pass", "exit_code": 0,
                    "duration_ms": 1, "counts": {}, "limitations": []}

        results = module.execute_plan(plan, runner)
        self.assertEqual([item["status"] for item in results], ["pass", "fail", "skipped", "skipped"])
        self.assertEqual(results[1]["limitations"], ["fixture failure"])
        self.assertIsNone(results[2]["exit_code"])

    def test_subprocess_stage_uses_argv_hashes_output_and_reports_timeout(self):
        module = self.module()
        stage = {"name": "unit", "kind": "subprocess", "command": [sys.executable, "fixed.py"], "timeout": 5}

        def completed(argv, **kwargs):
            self.assertEqual(argv, stage["command"])
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["timeout"], 5)
            return subprocess.CompletedProcess(argv, 0, b"stdout", b"Ran 3 tests in 0.1s\n\nOK (skipped=1)\n")

        result = module.run_subprocess_stage(stage, str(ROOT), {}, run=completed)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["stdout_sha256"], sha256(b"stdout"))
        self.assertEqual(result["stderr_sha256"], sha256(b"Ran 3 tests in 0.1s\n\nOK (skipped=1)\n"))
        self.assertEqual(result["counts"], {"tests": 3, "skipped": 1, "failures": 0, "errors": 0})

        def failed(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 7, b"partial", b"failed")

        failure = module.run_subprocess_stage(stage, str(ROOT), {}, run=failed)
        self.assertEqual(failure["status"], "fail")
        self.assertEqual(failure["exit_code"], 7)

        def timed_out(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output=b"partial", stderr=b"waiting")

        timeout = module.run_subprocess_stage(stage, str(ROOT), {}, run=timed_out)
        self.assertEqual(timeout["status"], "fail")
        self.assertEqual(timeout["exit_code"], 124)
        self.assertIn("timeout", " ".join(timeout["limitations"]).lower())
        self.assertEqual(timeout["stdout_sha256"], sha256(b"partial"))

    def test_structured_counts_cover_mutation_and_doctor(self):
        module = self.module()
        mutation = module.parse_counts(
            "mutation", b"", b"[+] Mutation score: 17/17 killed, 0 survived, 0 infrastructure error(s), 1 equivalent\n")
        self.assertEqual(mutation, {"killed": 17, "total": 17, "survived": 0,
                                    "infrastructure_errors": 0, "equivalent": 1})
        current_mutation = module.parse_counts(
            "mutation", b"killed 181 / 181 non-equivalent mutants; 0 equivalent survivor(s) documented\n", b"")
        self.assertEqual(current_mutation, {"killed": 181, "total": 181, "survived": 0,
                                            "infrastructure_errors": 0, "equivalent": 0})
        doctor_data = [{"id": "one", "status": "OK"}, {"id": "two", "status": "WARN"}]
        doctor = module.parse_counts("doctor", json.dumps(doctor_data).encode("utf-8"), b"")
        self.assertEqual(doctor, {"OK": 1, "WARN": 1, "FAIL": 0})
        doctor_summary = {"version": "0.3.0", "failed": False,
                          "summary": {"verified": 32, "WARN": 3, "info": 1, "unverified": 2, "FAIL": 0},
                          "results": []}
        doctor = module.parse_counts("doctor", json.dumps(doctor_summary).encode("utf-8"), b"")
        self.assertEqual(doctor, doctor_summary["summary"])

    def test_git_provenance_marks_relevant_dirty_paths_but_excludes_receipt(self):
        module = self.module()
        with tempfile.TemporaryDirectory(prefix="verify-all-git-") as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "tracked.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Test",
                            "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "base"], check=True)
            (root / "tracked.txt").write_text("changed\n", encoding="utf-8")
            (root / "new.txt").write_text("new\n", encoding="utf-8")
            receipt = root / "evals" / "results" / "latest.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text("{}\n", encoding="utf-8")
            result = module.git_provenance(str(root), ["evals/results/latest.json"])
            self.assertEqual(result["state"], "dirty")
            self.assertEqual(set(result["changed_paths"]), {"new.txt", "tracked.txt"})
            self.assertRegex(result["tested_sha"], r"^[0-9a-f]{40}$")

    def test_footprint_reports_exact_bytes_and_unverified_tokens_without_loader_record(self):
        module = self.module()
        missing = Path(tempfile.gettempdir()) / "missing-real-evals-loader-record.json"
        if missing.exists():
            missing.unlink()
        result = module.measure_footprint(str(ROOT), str(missing))
        self.assertEqual(result["status"], "unverified")
        self.assertGreater(result["descriptions"]["bytes"], 0)
        self.assertGreater(result["bodies"]["bytes"], 0)
        self.assertIsNone(result["descriptions"]["tokens"])
        self.assertIsNone(result["bodies"]["tokens"])
        self.assertIsNone(result["max_lane_tokens"])
        self.assertNotIn("estimated", json.dumps(result).lower())

    def test_actual_loader_record_requires_matching_hashes_and_no_hidden_content(self):
        module = self.module()
        inputs = module.footprint_inputs(str(ROOT))
        body_records = [
            {"path": path, "sha256": values["sha256"], "tokens": index + 100}
            for index, (path, values) in enumerate(sorted(inputs["bodies"].items()))
        ]
        body_tokens = {item["path"]: item["tokens"] for item in body_records}
        lanes = {}
        for lane, paths in {
            "Lite": ["skills/ai-sdlc/SKILL.md"],
            "Standard": ["skills/ai-sdlc/SKILL.md", "skills/spec-first/SKILL.md"],
            "Critical": ["skills/ai-sdlc/SKILL.md", "skills/spec-first/SKILL.md",
                         "skills/verify-and-evals/SKILL.md"],
        }.items():
            lanes[lane] = {
                "loaded_paths": paths,
                "unexpected_paths": [],
                "repeated_paths": [],
                "total_tokens": 500 + sum(body_tokens[path] for path in paths),
            }
        record = {
            "version": 1,
            "recorded_revision": subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
            "accounting": {
                "method": "kilo-skill-tool-step-token-delta",
                "provider": "fixture-provider",
                "model": "fixture-model",
                "probe_evidence_sha256": "c" * 64,
            },
            "catalog": {"sha256": inputs["catalog_sha256"], "tokens": 500},
            "skill_bodies": body_records,
            "lanes": lanes,
        }
        with tempfile.TemporaryDirectory(prefix="verify-all-loader-") as directory:
            path = Path(directory) / "loader.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            result = module.measure_footprint(str(ROOT), str(path))
            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["accounting"]["method"], "kilo-skill-tool-step-token-delta")
            self.assertEqual(result["descriptions"]["tokens"], 500)
            self.assertEqual(result["bodies"]["tokens"], sum(body_tokens.values()))
            self.assertEqual(result["max_lane_tokens"], lanes["Critical"]["total_tokens"])

            record["skill_bodies"][0]["sha256"] = "0" * 64
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(module.VerificationError):
                module.measure_footprint(str(ROOT), str(path))
            record["skill_bodies"][0]["sha256"] = inputs["bodies"][record["skill_bodies"][0]["path"]]["sha256"]
            record["lanes"]["Critical"]["unexpected_paths"] = ["hidden/prompt.md"]
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(module.VerificationError):
                module.measure_footprint(str(ROOT), str(path))

    def test_atomic_receipt_keeps_previous_file_when_replace_fails(self):
        module = self.module()
        with tempfile.TemporaryDirectory(prefix="verify-all-atomic-") as directory:
            path = Path(directory) / "latest.json"
            path.write_text('{"old":true}\n', encoding="utf-8")

            def fail_replace(source, target):
                raise OSError("fixture replace failure")

            with self.assertRaises(module.VerificationError):
                module.atomic_json(str(path), {"new": True}, replace=fail_replace)
            self.assertEqual(path.read_text(encoding="utf-8"), '{"old":true}\n')
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])

    def test_receipt_records_environment_inputs_and_nonpassing_status(self):
        module = self.module()
        stages = [
            {"name": "unit", "status": "pass", "exit_code": 0, "duration_ms": 1,
             "counts": {"tests": 3}, "limitations": []},
            {"name": "footprint", "status": "unverified", "exit_code": 4, "duration_ms": 1,
             "counts": {}, "limitations": ["loader unavailable"]},
        ]
        receipt = module.build_receipt(
            {"tested_sha": "a" * 40, "state": "clean", "changed_paths": []},
            stages,
            {"status": "unverified", "descriptions": {"bytes": 1, "tokens": None},
             "bodies": {"bytes": 2, "tokens": None}, "max_lane_tokens": None},
            {"python": "3.8.0", "platform": "fixture"},
            {"scripts/a.py": "b" * 64},
            "2026-11-13T00:00:00Z",
        )
        self.assertEqual(receipt["schema_version"], 1)
        self.assertEqual(receipt["overall_status"], "unverified")
        self.assertEqual(receipt["tested_sha"], "a" * 40)
        self.assertEqual(receipt["input_hashes"], {"scripts/a.py": "b" * 64})
        self.assertEqual(receipt["environment"]["python"], "3.8.0")

    def test_current_claim_markers_cover_all_three_documents_and_are_unique(self):
        if os.environ.get("VERIFY_ALL_UPDATING_RECEIPT") == "1":
            self.skipTest("latest.json is being replaced; validate real markers after receipt publication")
        module = self.module()
        self.assertTrue(hasattr(module, "validate_claims"), "claim validator is not implemented")
        receipt = ROOT / "evals" / "results" / "latest.json"
        self.assertTrue(receipt.is_file(), "current claims require evals/results/latest.json")
        claims = module.validate_claims(
            str(ROOT), str(receipt),
            [str(ROOT / "README.md"), str(ROOT / "LIMITATIONS.md"), str(ROOT / "PATCH-NOTES.md")],
            require_each=True,
        )
        ids = [claim["id"] for claim in claims]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 3)

    def test_claim_value_status_revision_and_stale_inputs_fail_closed(self):
        module = self.module()
        self.assertTrue(hasattr(module, "render_claim_block"), "claim renderer is not implemented")
        self.assertTrue(hasattr(module, "validate_claims"), "claim validator is not implemented")
        with tempfile.TemporaryDirectory(prefix="verify-all-claims-") as directory:
            root = Path(directory)
            source = root / "scripts" / "fixed.py"
            source.parent.mkdir(parents=True)
            source.write_text("value = 1\n", encoding="utf-8")
            receipt = {
                "schema_version": 1,
                "tested_sha": "a" * 40,
                "overall_status": "pass",
                "input_hashes": {"scripts/fixed.py": sha256(source.read_bytes().replace(b"\r\n", b"\n"))},
                "stages": [{"name": "unit", "status": "pass", "counts": {"tests": 321}}],
            }
            receipt_path = root / "latest.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            config = {
                "id": "fixture-unit-tests",
                "label": "unit tests",
                "value_path": "stages.unit.counts.tests",
                "unit": "tests",
                "status_path": "stages.unit.status",
            }
            document = root / "README.md"
            document.write_text(module.render_claim_block(config, receipt), encoding="utf-8")
            claims = module.validate_claims(str(root), str(receipt_path), [str(document)], require_each=True)
            self.assertEqual(claims[0]["value"], 321)

            document.write_text(document.read_text(encoding="utf-8").replace("321 tests", "322 tests"),
                                encoding="utf-8")
            with self.assertRaises(module.VerificationError):
                module.validate_claims(str(root), str(receipt_path), [str(document)], require_each=True)
            document.write_text(module.render_claim_block(config, receipt), encoding="utf-8")
            source.write_text("value = 2\n", encoding="utf-8")
            with self.assertRaises(module.VerificationError):
                module.validate_claims(str(root), str(receipt_path), [str(document)], require_each=True)

    def test_duplicate_marker_and_missing_receipt_path_are_rejected(self):
        module = self.module()
        self.assertTrue(hasattr(module, "render_claim_block"), "claim renderer is not implemented")
        self.assertTrue(hasattr(module, "validate_claims"), "claim validator is not implemented")
        with tempfile.TemporaryDirectory(prefix="verify-all-duplicate-") as directory:
            root = Path(directory)
            receipt = {
                "schema_version": 1,
                "tested_sha": "b" * 40,
                "overall_status": "pass",
                "input_hashes": {},
                "stages": [{"name": "unit", "status": "pass", "counts": {"tests": 9}}],
            }
            receipt_path = root / "latest.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            config = {"id": "duplicate", "label": "unit tests",
                      "value_path": "stages.unit.counts.tests", "unit": "tests",
                      "status_path": "stages.unit.status"}
            block = module.render_claim_block(config, receipt)
            first = root / "README.md"
            second = root / "LIMITATIONS.md"
            first.write_text(block, encoding="utf-8")
            second.write_text(block, encoding="utf-8")
            with self.assertRaises(module.VerificationError):
                module.validate_claims(str(root), str(receipt_path), [str(first), str(second)])

            bad = dict(config)
            bad["id"] = "missing"
            bad["value_path"] = "stages.unit.counts.missing"
            with self.assertRaises(module.VerificationError):
                module.render_claim_block(bad, receipt)

    def test_unmarked_patch_note_history_is_preserved(self):
        text = (ROOT / "PATCH-NOTES.md").read_text(encoding="utf-8")
        for historical in (
            "374 tests plus 2 overview tests",
            "175 of 175 non-equivalent mutants killed",
            "368 tests (ResourceWarning as error)",
            "255 unit/integration tests",
            "112 of 112 non-equivalent hand-picked mutants killed",
        ):
            self.assertIn(historical, text)


if __name__ == "__main__":
    unittest.main()
