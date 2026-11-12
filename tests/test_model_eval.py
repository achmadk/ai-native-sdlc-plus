"""Contracts for preregistered model-selection and paired task evaluations."""

import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
SELECTION = EVALS / "selection-cases.json"
TASKS = EVALS / "task-cases.json"
PRODUCT_CATALOG = EVALS / "catalogs" / "product-baseline.json"
EXTERNAL_CATALOG = EVALS / "catalogs" / "external-distractors.json"
MODEL_EVAL = ROOT / "scripts" / "model_eval.py"
TRANSCRIPTS = EVALS / "transcripts"
PRODUCT_SKILLS = {
    "ai-readiness-and-metrics",
    "ai-sdlc",
    "autonomy-policy",
    "context-pack",
    "decision-trace",
    "learning-mode",
    "review-by-intent",
    "ship-and-observe",
    "spec-first",
    "verify-and-evals",
}


def load_json(path):
    path = Path(path)
    if not path.is_file():
        raise AssertionError("expected registered artifact at %s" % path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AssertionError("invalid JSON in %s: %s" % (path, exc))


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def assert_sha256(test, value, label):
    test.assertRegex(value, r"^[0-9a-f]{64}$", "%s must be a lowercase SHA-256" % label)


class RegistrationContract(unittest.TestCase):
    def catalogs(self):
        product = load_json(PRODUCT_CATALOG)
        external = load_json(EXTERNAL_CATALOG)
        return product, external, {item["id"] for item in product["skills"] + external["skills"]}

    def test_selection_registration_is_complete_and_split(self):
        data = load_json(SELECTION)
        product, external, catalog_ids = self.catalogs()
        self.assertEqual(data.get("version"), 1)
        self.assertRegex(data.get("registration_id", ""), r"^real-evals-selection-v[0-9]+$")
        protocol = data.get("protocol", {})
        self.assertGreaterEqual(protocol.get("repetitions", 0), 3)
        limits = protocol.get("limits", {})
        self.assertGreater(limits.get("requests", 0), 0)
        self.assertGreater(limits.get("input_tokens", 0), 0)
        self.assertTrue(math.isfinite(limits.get("cost_usd", float("inf"))))
        self.assertGreater(limits.get("cost_usd", 0), 0)
        criteria = data.get("pass_criteria", {})
        for key in ("precision_min", "recall_min"):
            self.assertGreaterEqual(criteria.get(key, -1), 0)
            self.assertLessEqual(criteria.get(key, 2), 1)

        catalogs = data.get("catalogs", {})
        self.assertEqual(catalogs.get("product", {}).get("path"), "evals/catalogs/product-baseline.json")
        self.assertEqual(catalogs.get("external", {}).get("path"), "evals/catalogs/external-distractors.json")
        self.assertEqual(catalogs["product"].get("sha256"), sha256_bytes(PRODUCT_CATALOG.read_bytes()))
        self.assertEqual(catalogs["external"].get("sha256"), sha256_bytes(EXTERNAL_CATALOG.read_bytes()))
        self.assertEqual({item["id"] for item in product["skills"]}, PRODUCT_SKILLS)
        self.assertTrue({item["family"] for item in external["skills"]} >= {"OpenSpec", "Superpowers"})

        cases = data.get("cases", [])
        self.assertGreaterEqual(len(cases), 60)
        ids = [case.get("id") for case in cases]
        self.assertEqual(len(ids), len(set(ids)), "selection case IDs must be unique")
        prompts = [case.get("prompt", "").strip().casefold() for case in cases]
        self.assertEqual(len(prompts), len(set(prompts)), "selection prompts must be unique")
        kinds = {kind: [case for case in cases if case.get("kind") == kind]
                 for kind in ("should_trigger", "near_miss")}
        self.assertGreaterEqual(len(kinds["should_trigger"]), 30)
        self.assertGreaterEqual(len(kinds["near_miss"]), 30)

        for skill in PRODUCT_SKILLS:
            for kind in kinds:
                scoped = [case for case in kinds[kind] if case.get("target_skill") == skill]
                self.assertGreaterEqual(len(scoped), 3, "%s lacks %s coverage" % (skill, kind))
                self.assertEqual({case.get("split") for case in scoped}, {"development", "held_out"})

        for case in cases:
            self.assertIn(case.get("target_skill"), PRODUCT_SKILLS, case)
            self.assertIn(case.get("split"), {"development", "held_out"}, case)
            self.assertGreaterEqual(len(case.get("prompt", "").strip()), 12, case)
            expected = set(case.get("expected", []))
            allowed = set(case.get("allowed", []))
            forbidden = set(case.get("forbidden", []))
            self.assertFalse(expected & allowed or expected & forbidden or allowed & forbidden, case)
            self.assertTrue(expected | allowed | forbidden, case)
            self.assertTrue((expected | allowed | forbidden) <= catalog_ids, case)
            if case["kind"] == "should_trigger":
                self.assertIn(case["target_skill"], expected, case)
            else:
                self.assertIn(case["target_skill"], forbidden, case)

    def test_task_registration_is_condition_independent_and_complete(self):
        data = load_json(TASKS)
        self.assertEqual(data.get("version"), 1)
        self.assertRegex(data.get("registration_id", ""), r"^real-evals-tasks-v[0-9]+$")
        protocol = data.get("protocol", {})
        self.assertGreaterEqual(protocol.get("repetitions", 0), 3)
        self.assertEqual(set(protocol.get("conditions", [])), {"baseline", "with_skill"})
        self.assertTrue(protocol.get("randomize_condition_order"))
        limits = protocol.get("limits", {})
        self.assertGreater(limits.get("requests", 0), 0)
        self.assertGreater(limits.get("input_tokens", 0), 0)
        self.assertTrue(math.isfinite(limits.get("cost_usd", float("inf"))))

        cases = data.get("cases", [])
        self.assertEqual(len(cases), 30)
        self.assertEqual(len({case.get("id") for case in cases}), 30)
        self.assertEqual({case.get("skill") for case in cases}, PRODUCT_SKILLS)
        for skill in PRODUCT_SKILLS:
            scoped = [case for case in cases if case.get("skill") == skill]
            self.assertEqual({case.get("role") for case in scoped}, {"leader", "ic", "edge"})
        for case in cases:
            self.assertGreaterEqual(len(case.get("prompt", "").strip()), 12, case)
            assertions = case.get("assertions", [])
            self.assertGreaterEqual(len(assertions), 2, case)
            self.assertEqual(len({item.get("id") for item in assertions}), len(assertions), case)
            encoded = json.dumps(assertions, sort_keys=True).lower()
            self.assertNotIn("with_skill", encoded, case)
            self.assertNotIn("baseline", encoded, case)
            for assertion in assertions:
                self.assertIn(assertion.get("kind"), {"contains_all", "contains_any", "excludes_all", "json_fields"})
                self.assertTrue(assertion.get("values"), assertion)

    def test_product_catalog_matches_the_baseline_revision(self):
        data = load_json(PRODUCT_CATALOG)
        self.assertEqual(data.get("version"), 1)
        revision = data.get("captured_revision", "")
        self.assertRegex(revision, r"^[0-9a-f]{40}$")
        self.assertEqual({item.get("id") for item in data.get("skills", [])}, PRODUCT_SKILLS)
        for item in data["skills"]:
            rel = "skills/%s/SKILL.md" % item["id"]
            self.assertEqual(item.get("source_path"), rel)
            result = subprocess.run(
                ["git", "-C", str(ROOT), "show", "%s:%s" % (revision, rel)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
            assert_sha256(self, item.get("source_sha256", ""), rel)
            self.assertEqual(item["source_sha256"], sha256_bytes(result.stdout))
            text = result.stdout.decode("utf-8")
            match = re.match(r'^---\nname: (\S+)\ndescription: "(.*)"\n---\n', text, re.S)
            self.assertIsNotNone(match, rel)
            self.assertEqual((match.group(1), match.group(2)), (item["id"], item["description"]))

    def test_external_catalog_is_pinned_attributed_data(self):
        data = load_json(EXTERNAL_CATALOG)
        self.assertEqual(data.get("version"), 1)
        skills = data.get("skills", [])
        self.assertGreaterEqual(len(skills), 2)
        self.assertEqual({item.get("family") for item in skills}, {"OpenSpec", "Superpowers"})
        self.assertEqual(len({item.get("id") for item in skills}), len(skills))
        for item in skills:
            self.assertRegex(item.get("id", ""), r"^(openspec|superpowers)/[a-z0-9-]+$")
            self.assertTrue(item.get("description"))
            self.assertLessEqual(len(item["description"]), 1024)
            self.assertRegex(item.get("source_url", ""), r"^https://")
            self.assertNotIn(item.get("source_revision", "").lower(), {"", "head", "main", "master", "latest"})
            self.assertTrue(item.get("license"))
            assert_sha256(self, item.get("description_sha256", ""), item["id"])
            self.assertEqual(item["description_sha256"], sha256_bytes(item["description"].encode("utf-8")))
            self.assertNotIn("source_path", item, "external catalog entries must not look installed")

    def test_validator_accepts_the_registered_artifacts(self):
        self.assertTrue(MODEL_EVAL.is_file(), "expected registration validator at %s" % MODEL_EVAL)
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(MODEL_EVAL), "validate", "--root", str(ROOT), "--json"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout).get("status"), "valid")

    def test_any_transcript_registration_precedes_its_recorded_revision(self):
        if not TRANSCRIPTS.is_dir():
            return
        for path in sorted(TRANSCRIPTS.glob("*.json")):
            data = load_json(path)
            registration = data.get("registration_commit", "")
            recorded = data.get("recorded_revision", "")
            self.assertRegex(registration, r"^[0-9a-f]{40}$", str(path))
            self.assertRegex(recorded, r"^[0-9a-f]{40}$", str(path))
            result = subprocess.run(
                ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", registration, recorded],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, "%s does not descend from its registration" % path)


if __name__ == "__main__":
    unittest.main()
