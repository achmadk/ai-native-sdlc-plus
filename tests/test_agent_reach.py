"""Contracts for independent, controlled native-agent support evidence."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts import install

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts/agent_reach.py"
PROFILES = install.load_agent_profiles(str(ROOT))
PYTHON_BINARY = str(Path(sys.executable).resolve())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class NativeEvidenceContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sdlc-agent-reach-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def module(self):
        self.assertTrue(HARNESS.is_file(), "native evidence harness is missing")
        spec = importlib.util.spec_from_file_location("agent_reach_under_test", str(HARNESS))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def fixture(self):
        root = self.work / "candidate"
        root.mkdir()
        manifest = json.loads((ROOT / "scripts/install-manifest.json").read_text(encoding="utf-8"))
        for item in manifest["files"]:
            destination = root / item["source"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / item["source"], destination)
        (root / "AGENTS.md").write_bytes(b"# Fixture policy\nPreserve user-owned policy.\n")
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-c", "core.autocrlf=input", "-c", "core.safecrlf=false", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-c", "core.autocrlf=input", "-c", "core.safecrlf=false", "-C", str(root),
                        "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "-q", "-m", "registered fixture"], check=True)
        revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        hashes = {item["source"]: digest((root / item["source"]).read_bytes().replace(b"\r\n", b"\n"))
                  for item in manifest["files"]}
        hashes["AGENTS.md"] = digest((root / "AGENTS.md").read_bytes())
        clients = {
            "claude": ("claude-code", "claude-code-cli"), "cursor": ("cursor", "cursor-project"),
            "copilot": ("github-copilot", "vscode-copilot"), "codex": ("codex", "codex-cli"),
            "gemini": ("gemini-cli", "gemini-cli"), "opencode": ("opencode", "opencode-v2"),
            "kilo": ("kilo", "kilo-cli"),
        }
        registration = {
            "version": 1, "registration_id": "agent-reach-fixture-v1", "candidate_sha": revision,
            "registry_sha256": digest(canonical(PROFILES.PROFILE_CONTRACT)), "source_hashes": hashes,
            "profiles": {profile: {"client_id": pair[0], "surface": pair[1], "version": "fixture-1.0",
                                   "platform": "fixture-linux", "required_levels": [1, 2, 3] if profile in
                                   ("claude", "opencode") else [1, 2]} for profile, pair in clients.items()},
            "limits": {"attempts": 3, "timeout_seconds": 5, "response_bytes": 65536,
                       "input_tokens": 3000, "max_input_tokens_per_attempt": 1000,
                       "cost_usd": 0.30, "max_cost_per_attempt": 0.10},
            "cases": [],
        }
        for profile, client in registration["profiles"].items():
            for level in client["required_levels"]:
                registration["cases"].append({
                    "id": "%s-level-%d" % (profile, level), "profile": profile, "level": level,
                    "probe_name": "agent-reach-fixture-probe", "nonce": "NONCE_SOURCE_ONLY_7421",
                    "prompt": "Follow the registered SDLC behavior using the selected skill.",
                    "expected_text": ["Lane: Critical", "threat note"] if level == 3 else [],
                    "repetitions": 3 if level == 3 else 1, "permitted_tools": ["skill"],
                })
        self.root = root
        self.registration = registration
        return registration

    def record(self, profile="kilo", level=2, origin="native"):
        registration = self.registration
        case = next(item for item in registration["cases"] if item["profile"] == profile and item["level"] == level)
        positive = self.work / (profile + "-positive")
        negative = self.work / (profile + "-negative")
        positive.mkdir(exist_ok=True)
        negative.mkdir(exist_ok=True)
        prefix = PROFILES.PROFILE_CONTRACT[profile]["skill_prefix"]
        skills = []
        for skill in PROFILES.PRODUCT_SKILLS:
            relative = prefix + "/" + skill + "/SKILL.md"
            destination = positive / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((self.root / "skills" / skill / "SKILL.md").read_bytes())
            skills.append({"name": skill, "path": str(destination)})
        probe = positive / prefix / case["probe_name"] / "SKILL.md"
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("# Probe\n" + case["nonce"] + "\n", encoding="utf-8")
        skills.append({"name": case["probe_name"], "path": str(probe)})
        positive_output = json.dumps({"skills": skills, "loaded_skills": [case["probe_name"]],
                                      "response": case["nonce"] + " Lane: Critical; threat note",
                                      "tools": ["skill"]})
        negative_output = json.dumps({"skills": [], "loaded_skills": [], "response": "no matching skill", "tools": []})
        captures = []
        for repeat in range(1, case["repetitions"] + 1):
            captures.append({"repeat": repeat, "positive": {
                "cwd": str(positive), "exit_code": 0, "stdout": positive_output, "stderr": "",
                "stdout_sha256": digest(positive_output.encode("utf-8")), "stderr_sha256": digest(b""),
            }, "negative": {
                "cwd": str(negative), "exit_code": 0, "stdout": negative_output, "stderr": "",
                "stdout_sha256": digest(negative_output.encode("utf-8")), "stderr_sha256": digest(b""),
            }})
        return {
            "version": 1, "id": "%s-result-%d" % (profile, level), "profile": profile, "level": level,
            "case_id": case["id"], "candidate_sha": registration["candidate_sha"],
            "registration_sha256": digest(canonical(registration)), "source_hashes": registration["source_hashes"],
            "client": registration["profiles"][profile], "capture_kind": origin, "reviewed_by": "Fixture Reviewer",
            "controls": {name: True for name in ("isolated_home", "updates_disabled", "plugins_disabled",
                                                "hooks_disabled", "mcp_disabled", "unrelated_tools_denied")},
            "captures": captures,
        }

    def test_registration_requires_all_targets_and_committed_matching_sources(self):
        module = self.module()
        registration = self.fixture()
        validated = module.validate_registration(registration, str(self.root))
        self.assertEqual(validated["candidate_sha"], registration["candidate_sha"])
        for mutation in ("missing_profile", "weakened_level", "duplicate_case", "stale_source"):
            changed = json.loads(json.dumps(registration))
            if mutation == "missing_profile":
                changed["profiles"].pop("claude")
            elif mutation == "weakened_level":
                changed["profiles"]["opencode"]["required_levels"] = [1, 2]
            elif mutation == "duplicate_case":
                changed["cases"].append(changed["cases"][0])
            else:
                changed["source_hashes"]["AGENTS.md"] = "0" * 64
            with self.subTest(mutation=mutation):
                with self.assertRaises(module.EvidenceError):
                    module.validate_registration(changed, str(self.root))

    def test_levels_are_independent_and_synthetic_records_never_certify_native_support(self):
        module = self.module()
        registration = self.fixture()
        record = self.record()
        result = module.replay(registration, [record], str(self.root))
        levels = result["profiles"]["kilo"]["levels"]
        self.assertEqual(levels["1"]["status"], "unverified")
        self.assertEqual(levels["2"]["status"], "pass")
        self.assertEqual(levels["3"]["status"], "unverified")
        record["capture_kind"] = "synthetic"
        result = module.replay(registration, [record], str(self.root))
        self.assertEqual(result["profiles"]["kilo"]["levels"]["2"]["status"], "unverified")

    def test_generation_evidence_checks_complete_files_and_preserved_policy(self):
        module = self.module()
        registration = self.fixture()
        positive = self.work / "generated-positive"
        negative = self.work / "generated-negative"
        positive.mkdir()
        negative.mkdir()
        policy = (self.root / "AGENTS.md").read_bytes()
        (positive / "AGENTS.md").write_bytes(policy)
        install.init_project(str(positive), source_root=str(self.root), agents=["kilo"])
        state = json.loads((positive / ".sdlc-install.json").read_text(encoding="utf-8"))
        case = next(item for item in registration["cases"] if item["id"] == "kilo-level-1")
        output = json.dumps({"files": {name: data["sha256"] for name, data in state["files"].items()},
                             "policy_before_sha256": digest(policy), "policy_after_sha256": digest(policy)})
        negative_output = "{}"
        record = {
            "version": 1, "id": "kilo-generated-result", "profile": "kilo", "level": 1,
            "case_id": case["id"], "candidate_sha": registration["candidate_sha"],
            "registration_sha256": digest(canonical(registration)), "source_hashes": registration["source_hashes"],
            "client": registration["profiles"]["kilo"], "capture_kind": "generated", "reviewed_by": "Fixture Reviewer",
            "controls": {name: True for name in ("isolated_home", "updates_disabled", "plugins_disabled",
                                                "hooks_disabled", "mcp_disabled", "unrelated_tools_denied")},
            "captures": [{"repeat": 1, "positive": {"cwd": str(positive), "exit_code": 0, "stdout": output,
                          "stderr": "", "stdout_sha256": digest(output.encode("utf-8")), "stderr_sha256": digest(b"")},
                          "negative": {"cwd": str(negative), "exit_code": 0, "stdout": negative_output, "stderr": "",
                                       "stdout_sha256": digest(negative_output.encode("utf-8")), "stderr_sha256": digest(b"")}}],
        }
        self.assertEqual(module.validate_record(record, registration, str(self.root))["status"], "pass")
        (positive / ".kilo/skills/ai-sdlc/SKILL.md").unlink()
        self.assertEqual(module.validate_record(record, registration, str(self.root))["status"], "fail")

    def test_client_surface_version_and_platform_substitutions_are_rejected(self):
        module = self.module()
        registration = self.fixture()
        original = self.record(profile="opencode", level=3)
        for field, value in (("client_id", "kilo"), ("surface", "kilo-cli"), ("version", "different-version"),
                             ("platform", "different-platform")):
            changed = json.loads(json.dumps(original))
            changed["client"][field] = value
            with self.subTest(field=field):
                with self.assertRaises(module.EvidenceError):
                    module.validate_record(changed, registration, str(self.root))

    def test_provenance_terminal_outcome_and_repeat_tampering_are_rejected(self):
        module = self.module()
        registration = self.fixture()
        original = self.record(profile="claude", level=3)
        for mutation in ("registration_hash", "source_hash", "stdout_hash", "nonterminal", "missing_repeat"):
            changed = json.loads(json.dumps(original))
            if mutation == "registration_hash":
                changed["registration_sha256"] = "0" * 64
            elif mutation == "source_hash":
                changed["source_hashes"]["AGENTS.md"] = "0" * 64
            elif mutation == "stdout_hash":
                changed["captures"][0]["positive"]["stdout_sha256"] = "0" * 64
            elif mutation == "nonterminal":
                changed["captures"][0]["positive"]["exit_code"] = None
            else:
                changed["captures"].pop()
            with self.subTest(mutation=mutation):
                with self.assertRaises(module.EvidenceError):
                    module.validate_record(changed, registration, str(self.root))

    def test_negative_control_false_positive_and_forbidden_tools_fail_behavior(self):
        module = self.module()
        registration = self.fixture()
        record = self.record(profile="claude", level=3)
        failed_output = json.dumps({"skills": [], "loaded_skills": [], "response": "NONCE_SOURCE_ONLY_7421", "tools": []})
        record["captures"][0]["negative"]["stdout"] = failed_output
        record["captures"][0]["negative"]["stdout_sha256"] = digest(failed_output.encode("utf-8"))
        self.assertEqual(module.validate_record(record, registration, str(self.root))["status"], "fail")
        record = self.record(profile="opencode", level=3)
        payload = json.loads(record["captures"][0]["positive"]["stdout"])
        payload["tools"] = ["bash"]
        output = json.dumps(payload)
        record["captures"][0]["positive"]["stdout"] = output
        record["captures"][0]["positive"]["stdout_sha256"] = digest(output.encode("utf-8"))
        self.assertEqual(module.validate_record(record, registration, str(self.root))["status"], "fail")

    def test_nonce_prompt_leak_and_secret_output_are_rejected(self):
        module = self.module()
        registration = self.fixture()
        changed = json.loads(json.dumps(registration))
        changed["cases"][0]["prompt"] += " NONCE_SOURCE_ONLY_7421"
        with self.assertRaises(module.EvidenceError):
            module.validate_registration(changed, str(self.root))
        record = self.record()
        record["captures"][0]["positive"]["stderr"] = "ghp_" + "a" * 40
        record["captures"][0]["positive"]["stderr_sha256"] = digest(record["captures"][0]["positive"]["stderr"].encode("utf-8"))
        with self.assertRaises(module.EvidenceError):
            module.validate_record(record, registration, str(self.root))

    def test_replay_is_deterministic_and_never_calls_a_client(self):
        module = self.module()
        registration = self.fixture()
        record = self.record()
        first = module.replay(registration, [record], str(self.root))
        from unittest import mock
        original = module.subprocess.Popen

        def git_only(argv, *args, **kwargs):
            self.assertIn(Path(argv[0]).name.casefold(), ("git", "git.exe"), "replay started a client")
            return original(argv, *args, **kwargs)

        with mock.patch.object(module.subprocess, "Popen", side_effect=git_only):
            second = module.replay(registration, [record], str(self.root))
        self.assertEqual(canonical(first), canonical(second))
        with self.assertRaises(module.EvidenceError):
            module.replay(registration, [record, record], str(self.root))

    def test_capture_requires_approval_and_enforces_attempt_caps_and_cache_identity(self):
        module = self.module()
        self.fixture()
        marker = self.work / "attempt-count"
        stub = self.work / "native-double.py"
        stub.write_text("from pathlib import Path\np=Path(%r)\np.write_text(str(int(p.read_text())+1) if p.exists() else '1')\nprint('{}')\n" % str(marker),
                        encoding="utf-8")
        command = [PYTHON_BINARY, "-I", "-B", str(stub)]
        limits = dict(self.registration["limits"], attempts=1)
        parameters = {"cwd": str(self.work), "ledger_path": str(self.work / "attempts.json"),
                      "cache_dir": str(self.work / "cache"), "limits": limits, "context_id": "fixture-case-1",
                      "capture_kind": "synthetic", "env": {"PATH": os.environ.get("PATH", "")}}
        with self.assertRaises(module.EvidenceError):
            module.run_capture(command, approved=False, **parameters)
        self.assertFalse(marker.exists())
        first = module.run_capture(command, approved=True, **parameters)
        second = module.run_capture(command, approved=True, **parameters)
        self.assertEqual(marker.read_text(), "1")
        self.assertEqual(first["stdout"], second["stdout"])
        self.assertFalse(first["evidence_eligible"])
        parameters["context_id"] = "fixture-case-2"
        with self.assertRaises(module.EvidenceError):
            module.run_capture(command, approved=True, **parameters)
        self.assertEqual(marker.read_text(), "1")

    def test_native_capture_refuses_unverified_client_setup_before_execution(self):
        module = self.module()
        registration = self.fixture()
        marker = self.work / "unverified-client-started"
        client = self.work / "client.py"
        client.write_text("from pathlib import Path\nPath(%r).touch()\n" % str(marker), encoding="utf-8")
        with self.assertRaises(module.EvidenceError):
            module.run_capture([PYTHON_BINARY, "-I", "-B", str(client)], cwd=str(self.work),
                               ledger_path=str(self.work / "native-attempts.json"),
                               cache_dir=str(self.work / "native-cache"), limits=registration["limits"],
                               context_id="unverified-native-setup", capture_kind="native", env={}, approved=True)
        self.assertFalse(marker.exists())

    def test_discovered_paths_accept_canonical_aliases_but_not_outside_files(self):
        module = self.module()
        registration = self.fixture()
        record = self.record()
        for pair in record["captures"]:
            for control in ("positive", "negative"):
                pair[control]["cwd"] = str(Path(pair[control]["cwd"]).resolve())
        try:
            result = module.validate_record(record, registration, str(self.root))
        except module.EvidenceError as exc:
            self.fail("a valid canonical path alias was rejected: %s" % exc)
        self.assertEqual(result["status"], "pass")
        payload = json.loads(record["captures"][0]["positive"]["stdout"])
        payload["skills"][0]["path"] = str(self.root / "skills" / payload["skills"][0]["name"] / "SKILL.md")
        output = json.dumps(payload)
        record["captures"][0]["positive"]["stdout"] = output
        record["captures"][0]["positive"]["stdout_sha256"] = digest(output.encode("utf-8"))
        with self.assertRaises(module.EvidenceError):
            module.validate_record(record, registration, str(self.root))

    def test_linked_discovered_skill_is_not_followed(self):
        module = self.module()
        registration = self.fixture()
        record = self.record()
        capture = record["captures"][0]["positive"]
        payload = json.loads(capture["stdout"])
        target = Path(payload["skills"][0]["path"])
        source = self.root / "skills" / payload["skills"][0]["name"] / "SKILL.md"
        target.unlink()
        try:
            target.symlink_to(source)
        except OSError as exc:
            self.skipTest("symlink creation unavailable: %s" % exc)
        with self.assertRaises(module.EvidenceError):
            module.validate_record(record, registration, str(self.root))

    def test_capture_is_shell_free_bounded_and_rejects_secret_material(self):
        module = self.module()
        registration = self.fixture()
        marker = self.work / "shell-interpreted"
        client = self.work / "capture.py"
        client.write_text("import sys\nprint(sys.argv[1])\n", encoding="utf-8")
        tail = ["&", PYTHON_BINARY, "-I", "-B", "-c", "from pathlib import Path; Path(%r).touch()" % str(marker)]
        limits = registration["limits"]
        parameters = {"cwd": str(self.work), "ledger_path": str(self.work / "bounded-attempts.json"),
                      "cache_dir": str(self.work / "bounded-cache"), "limits": limits,
                      "capture_kind": "synthetic", "env": {"PATH": os.environ.get("PATH", "")}, "approved": True}
        result = module.run_capture([PYTHON_BINARY, "-I", "-B", str(client), "{}"] + tail,
                                    context_id="shell-free", **parameters)
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(marker.exists())
        with self.assertRaises(module.EvidenceError):
            module.run_capture([PYTHON_BINARY, "-I", "-B", str(client), "ghp_" + "a" * 40],
                               context_id="secret-output", **parameters)
        bounded = dict(parameters)
        bounded["limits"] = dict(limits, response_bytes=32)
        with self.assertRaises(module.EvidenceError):
            module.run_capture([PYTHON_BINARY, "-I", "-B", str(client), "x" * 100],
                               context_id="oversized-output", **bounded)

    def test_native_command_boundary_never_substitutes_other_client_surfaces(self):
        module = self.module()
        self.assertTrue(hasattr(module, "native_command"), "fixed native command boundary is missing")
        prefix = [PYTHON_BINARY, "-I", "-B"]
        self.assertEqual(module.native_command("kilo", "discovery", prefix), prefix + ["debug", "skill"])
        self.assertEqual(module.native_command("gemini", "discovery", prefix), prefix + ["skills", "list"])
        for profile in ("claude", "cursor", "copilot", "codex", "opencode"):
            with self.subTest(profile=profile):
                with self.assertRaises(module.EvidenceError):
                    module.native_command(profile, "discovery", prefix)
        with self.assertRaises(module.EvidenceError):
            module.native_command("unknown-client", "discovery", prefix)

    def test_protocol_documentation_states_capture_and_replay_limits(self):
        guide = (ROOT / "adapters/README.md").read_text(encoding="utf-8")
        for fragment in ("scripts/agent_reach.py", "registration_sha256", "capture_kind", "run_capture",
                         "reviewed_by", "synthetic", "does not authenticate", "client-version setup"):
            self.assertIn(fragment, guide)

    def test_support_matrix_has_seven_rows_independent_levels_and_exact_surfaces(self):
        module = self.module()
        registration = self.fixture()
        native = self.record(profile="kilo", level=2)
        synthetic = self.record(profile="claude", level=3, origin="synthetic")
        replayed = module.replay(registration, [native, synthetic], str(self.root))
        self.assertTrue(hasattr(module, "render_support_matrix"), "support matrix renderer is missing")
        matrix = module.render_support_matrix(registration, replayed)
        self.assertEqual(sum(line.startswith("| `") for line in matrix.splitlines()), 7)
        for profile, descriptor in PROFILES.PROFILE_CONTRACT.items():
            self.assertIn("| `%s` | %s |" % (profile, descriptor["surface"]), matrix)
        self.assertIn("| `kilo` |", matrix)
        self.assertIn("| pass |", next(line for line in matrix.splitlines() if line.startswith("| `kilo`")))
        claude = next(line for line in matrix.splitlines() if line.startswith("| `claude`"))
        self.assertIn("unverified", claude)
        self.assertIn("L1,L2,L3", claude)
        self.assertNotIn("synthetic", claude.casefold())

    def test_matrix_rejects_stale_or_cross_registry_results(self):
        module = self.module()
        self.assertTrue(hasattr(module, "render_support_matrix"), "support matrix renderer is missing")
        registration = self.fixture()
        replayed = module.replay(registration, [self.record()], str(self.root))
        for key in ("candidate_sha", "registry_sha256", "registration_id"):
            changed = json.loads(json.dumps(replayed))
            changed[key] = "0" * 40 if key == "candidate_sha" else "stale-value"
            with self.subTest(key=key):
                with self.assertRaises(module.EvidenceError):
                    module.render_support_matrix(registration, changed)
        changed = json.loads(json.dumps(replayed))
        changed["profiles"]["extra-client"] = changed["profiles"]["kilo"]
        with self.assertRaises(module.EvidenceError):
            module.render_support_matrix(registration, changed)

    def test_matrix_update_is_bounded_deterministic_and_detects_manual_drift(self):
        module = self.module()
        registration = self.fixture()
        replayed = module.replay(registration, [self.record()], str(self.root))
        self.assertTrue(hasattr(module, "render_support_matrix"), "support matrix renderer is missing")
        self.assertTrue(hasattr(module, "update_matrix"), "bounded matrix updater is missing")
        self.assertTrue(hasattr(module, "check_matrix"), "matrix drift checker is missing")
        document = self.work / "COMPATIBILITY.md"
        document.write_text("# Compatibility\n\nKeep this authored preface.\n\n<!-- agent-reach:start -->\nold\n<!-- agent-reach:end -->\n",
                            encoding="utf-8")
        expected = module.render_support_matrix(registration, replayed)
        module.update_matrix(str(document), expected)
        first = document.read_bytes()
        self.assertIn(b"Keep this authored preface.", first)
        self.assertTrue(module.check_matrix(str(document), expected))
        module.update_matrix(str(document), expected)
        self.assertEqual(document.read_bytes(), first)
        document.write_text(document.read_text(encoding="utf-8").replace("unverified", "pass", 1),
                            encoding="utf-8")
        self.assertFalse(module.check_matrix(str(document), expected))
        with self.assertRaises(module.EvidenceError):
            module.update_matrix(str(self.work / "missing-markers.md"), expected)

    def test_current_documentation_has_one_matrix_source_and_bounded_section(self):
        compatibility = (ROOT / "docs/COMPATIBILITY.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        adapters = (ROOT / "adapters/README.md").read_text(encoding="utf-8")
        self.assertEqual(compatibility.count("<!-- agent-reach:start -->"), 1)
        self.assertEqual(compatibility.count("<!-- agent-reach:end -->"), 1)
        self.assertIn("not a current native loader or behavior matrix", compatibility)
        self.assertIn("native profile evidence matrix", readme)
        self.assertIn("native profile matrix", adapters)
        self.assertNotIn("| Agent / Tool | Config File | Integration Method |", readme)


if __name__ == "__main__":
    unittest.main()
