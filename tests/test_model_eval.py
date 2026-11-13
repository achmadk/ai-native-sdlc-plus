"""Contracts for preregistered model-selection and paired task evaluations."""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
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
REGISTRATION_COMMIT = "569eec7a51e8b8f7ee78c26601560dfd15d3b866"
CURRENT_HEAD = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


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


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes().replace(b"\r\n", b"\n"))


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
        self.assertEqual(catalogs["product"].get("sha256"), sha256_file(PRODUCT_CATALOG))
        self.assertEqual(catalogs["external"].get("sha256"), sha256_file(EXTERNAL_CATALOG))
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


class EvalGuidanceContract(unittest.TestCase):
    def test_provider_record_and_replay_boundary_is_documented(self):
        guidance = (ROOT / "skills/verify-and-evals/SKILL.md").read_text(encoding="utf-8")
        plan = (ROOT / "skills/verify-and-evals/assets/eval-plan-template.md").read_text(encoding="utf-8")
        for fragment in (
            "SDLC_EVAL_PROVIDER_CMD",
            "SDLC_EVAL_PROVIDER_ENV",
            "scripts/model_eval.py record",
            "scripts/model_eval.py replay",
            "--max-request-cost",
            "shell=False",
            "never invokes the provider",
            "Catalog selection is not loader discovery",
        ):
            self.assertIn(fragment, guidance)
        for fragment in (
            "Provider command JSON argv:",
            "Allowed provider environment names:",
            "Maximum request cost:",
            "Replay transcript:",
            "Selection, discovery, or invocation claim:",
        ):
            self.assertIn(fragment, plan)
        self.assertLessEqual(len(guidance.splitlines()), 120)


class ProviderAndReplayContract(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sdlc-model-eval-")
        self.addCleanup(self.temp_dir.cleanup)
        self.work = Path(self.temp_dir.name)
        self.provider = self.work / "provider fixture.py"
        self.provider.write_text(
            """import json
import os
from pathlib import Path
import sys

request = json.loads(sys.stdin.readline())
mode = os.environ.get("PROVIDER_MODE", "ok")
counter = os.environ.get("PROVIDER_COUNT_FILE")
if counter:
    path = Path(counter)
    count = int(path.read_text(encoding="utf-8")) if path.exists() else 0
    path.write_text(str(count + 1), encoding="utf-8")
if mode == "malformed":
    print("not-json")
    raise SystemExit(0)
if mode == "oversized":
    print(json.dumps({"padding": "x" * 10000}))
    raise SystemExit(0)

selected = json.loads(os.environ.get("PROVIDER_SELECTION", '["ai-sdlc"]'))
if mode == "env_check":
    clean = os.environ.get("VISIBLE_TOKEN") == "visible-fixture-token" and "HIDDEN_TOKEN" not in os.environ
    selected = selected if clean else ["environment-leaked"]
usage = {"input_tokens": 10, "output_tokens": 2}
if mode != "missing_cost":
    usage["cost_usd"] = float(os.environ.get("PROVIDER_COST", "0.01"))
response = {
    "version": 1,
    "provider": "fixture-provider",
    "model": "fixture-model-v1",
    "selected": selected,
    "usage": usage,
}
if mode == "echo_secret":
    response["raw_text"] = os.environ.get("VISIBLE_TOKEN")
print(json.dumps(response))
""",
            encoding="utf-8",
        )

    def provider_env(self, mode="ok", selected=None, cost="0.01"):
        marker = self.work / "shell-marker"
        marker_code = "from pathlib import Path; Path(%r).touch()" % str(marker)
        command = [
            sys.executable, "-I", "-B", str(self.provider),
            "&", sys.executable, "-I", "-B", "-c", marker_code,
        ]
        env = dict(os.environ)
        env.update(
            PYTHONDONTWRITEBYTECODE="1",
            SDLC_EVAL_PROVIDER_CMD=json.dumps(command),
            SDLC_EVAL_PROVIDER_ENV=(
                "VISIBLE_TOKEN,PROVIDER_MODE,PROVIDER_SELECTION,PROVIDER_COST,PROVIDER_COUNT_FILE"
            ),
            VISIBLE_TOKEN="visible-fixture-token",
            HIDDEN_TOKEN="must-not-reach-provider",
            PROVIDER_MODE=mode,
            PROVIDER_SELECTION=json.dumps(["ai-sdlc"] if selected is None else selected),
            PROVIDER_COST=cost,
        )
        return env, marker

    def run_cli(self, *args, env=None):
        return subprocess.run(
            [sys.executable, "-I", "-B", str(MODEL_EVAL)] + list(args),
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

    def record(self, *extra, case_id="sel-ai-sdlc-s-d1", catalog="baseline",
               recorded_revision=CURRENT_HEAD, env=None):
        output = self.work / (case_id + ".json")
        result = self.run_cli(
            "record",
            "--root", str(ROOT),
            "--kind", "selection",
            "--case", case_id,
            "--catalog", catalog,
            "--registration-commit", REGISTRATION_COMMIT,
            "--recorded-revision", recorded_revision,
            "--out", str(output),
            "--max-response-bytes", "4096",
            "--max-request-cost", "0.10",
            "--json",
            *extra,
            env=env,
        )
        return result, output

    def assert_recorded(self, *extra, case_id="sel-ai-sdlc-s-d1", catalog="baseline",
                        recorded_revision=CURRENT_HEAD, env=None):
        result, output = self.record(
            *extra, case_id=case_id, catalog=catalog,
            recorded_revision=recorded_revision, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(output.is_file(), result.stdout + result.stderr)
        return json.loads(output.read_text(encoding="utf-8")), output

    def replay(self, transcript, env=None):
        return self.run_cli(
            "replay", "--root", str(ROOT), "--transcript", str(transcript), "--json", env=env
        )

    def test_record_uses_json_argv_full_catalog_and_explicit_environment(self):
        env, marker = self.provider_env(mode="env_check")
        transcript, _ = self.assert_recorded(env=env)
        self.assertFalse(marker.exists(), "provider argv must never be interpreted by a shell")
        self.assertEqual(transcript["catalog"]["skill_count"], 34)
        self.assertEqual(len(transcript["records"]), 3)
        self.assertTrue(all(record["selected"] == ["ai-sdlc"] for record in transcript["records"]))
        self.assertNotIn("visible-fixture-token", json.dumps(transcript))
        self.assertNotIn("must-not-reach-provider", json.dumps(transcript))

    def test_candidate_catalog_comes_from_the_recorded_revision(self):
        env, _ = self.provider_env()
        transcript, _ = self.assert_recorded(catalog="candidate", env=env)
        self.assertEqual(transcript["catalog"]["id"], "candidate")
        self.assertEqual(transcript["catalog"]["skill_count"], 34)
        self.assertEqual(transcript["recorded_revision"], CURRENT_HEAD)

    def test_invalid_provider_argv_is_rejected(self):
        env, _ = self.provider_env()
        env["SDLC_EVAL_PROVIDER_CMD"] = "not-json"
        result, output = self.record(env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("provider command", (result.stdout + result.stderr).lower())
        self.assertFalse(output.exists())

    def test_unknown_provider_selection_is_rejected(self):
        env, _ = self.provider_env(selected=["not-in-the-catalog"])
        result, output = self.record(env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown skill", (result.stdout + result.stderr).lower())
        self.assertFalse(output.exists())

    def test_malformed_and_oversized_provider_responses_are_rejected(self):
        for mode, expected in (("malformed", "json"), ("oversized", "response")):
            with self.subTest(mode=mode):
                env, _ = self.provider_env(mode=mode)
                result, output = self.record(env=env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, (result.stdout + result.stderr).lower())
                self.assertFalse(output.exists())

    def test_request_cap_stops_before_the_third_repeat(self):
        env, _ = self.provider_env()
        counter = self.work / "request-count"
        env["PROVIDER_COUNT_FILE"] = str(counter)
        result, output = self.record("--request-cap", "2", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(counter.is_file(), "provider should run exactly twice before request-cap refusal")
        self.assertEqual(counter.read_text(encoding="utf-8"), "2")
        self.assertFalse(output.exists())
        self.assertIn("request cap", (result.stdout + result.stderr).lower())

    def test_monetary_cap_stops_before_the_next_possible_charge(self):
        env, _ = self.provider_env(cost="0.02")
        counter = self.work / "cost-count"
        env["PROVIDER_COUNT_FILE"] = str(counter)
        result, output = self.record(
            "--cost-cap", "0.03", "--max-request-cost", "0.02", env=env
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(counter.is_file(), "provider should run once before cost-cap refusal")
        self.assertEqual(counter.read_text(encoding="utf-8"), "1")
        self.assertFalse(output.exists())
        self.assertIn("cost cap", (result.stdout + result.stderr).lower())

    def test_missing_cost_is_recorded_as_unverified_and_nonpassing(self):
        env, _ = self.provider_env(mode="missing_cost")
        result, output = self.record(env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(output.is_file(), result.stdout + result.stderr)
        transcript = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(transcript["cost_status"], "unverified")
        self.assertEqual(transcript["status"], "incomplete")
        self.assertTrue(all(record["usage"]["cost_usd"] is None for record in transcript["records"]))

    def test_zero_cost_provider_is_verified_not_treated_as_missing(self):
        env, _ = self.provider_env(cost="0")
        transcript, _ = self.assert_recorded(env=env)
        self.assertEqual(transcript["cost_status"], "verified")
        self.assertTrue(all(record["usage"]["cost_usd"] == 0 for record in transcript["records"]))

    def test_secret_echo_is_never_persisted(self):
        env, _ = self.provider_env(mode="echo_secret")
        result, output = self.record(env=env)
        self.assertNotEqual(result.returncode, 0)
        if output.exists():
            self.assertNotIn("visible-fixture-token", output.read_text(encoding="utf-8"))
        self.assertIn("secret", (result.stdout + result.stderr).lower())

    def test_forbidden_selection_is_preserved_as_a_negative_result(self):
        env, _ = self.provider_env(selected=["ai-sdlc"])
        transcript, _ = self.assert_recorded(case_id="sel-ai-sdlc-n-d1", env=env)
        self.assertEqual(transcript["status"], "complete")
        self.assertEqual(transcript["summary"]["verdict"], "fail")
        self.assertEqual(transcript["summary"]["forbidden_selections"], 3)
        self.assertTrue(all(record["outcome"]["forbidden_selected"] == ["ai-sdlc"]
                            for record in transcript["records"]))

    def test_replay_is_deterministic_and_never_invokes_provider(self):
        env, _ = self.provider_env()
        transcript, path = self.assert_recorded(env=env)
        counter = self.work / "replay-count"
        env["PROVIDER_COUNT_FILE"] = str(counter)
        env["SDLC_EVAL_PROVIDER_CMD"] = json.dumps(["command-that-must-not-run"])
        result = self.replay(path, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        replayed = json.loads(result.stdout)
        self.assertEqual(replayed["summary"], transcript["summary"])
        self.assertEqual(replayed["records"], transcript["records"])
        self.assertFalse(counter.exists(), "replay must not invoke the configured provider")

    def test_replay_rejects_missing_repeats(self):
        env, _ = self.provider_env()
        transcript, path = self.assert_recorded(env=env)
        transcript["records"].pop()
        path.write_text(json.dumps(transcript), encoding="utf-8")
        result = self.replay(path, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repeat", (result.stdout + result.stderr).lower())

    def test_replay_rejects_provenance_hash_tampering(self):
        env, _ = self.provider_env()
        original, path = self.assert_recorded(env=env)
        fields = (
            ("registration_sha256",),
            ("catalog", "sha256"),
            ("records", 0, "request_sha256"),
        )
        for field_path in fields:
            with self.subTest(field_path=field_path):
                transcript = json.loads(json.dumps(original))
                target = transcript
                for key in field_path[:-1]:
                    target = target[key]
                target[field_path[-1]] = "0" * 64
                path.write_text(json.dumps(transcript), encoding="utf-8")
                result = self.replay(path, env=env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("hash", (result.stdout + result.stderr).lower())


if __name__ == "__main__":
    unittest.main()
