"""Tests for upstream governance adapters: OpenSpec schema package and Spec Kit extension/preset."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ADAPTERS = ROOT / "adapters"


class OpenSpecGovernancePackageContract(unittest.TestCase):
    """Contract tests for OpenSpec sdlc-governed schema and operation guidance."""

    def test_schema_files_exist_and_are_valid(self):
        schema_path = ADAPTERS / "openspec" / "sdlc-governed" / "schema.yaml"
        self.assertTrue(schema_path.is_file(), f"missing {schema_path}")
        content = schema_path.read_text(encoding="utf-8")
        self.assertIn("sdlc-governed", content)
        self.assertIn("threat-note", content)
        self.assertIn("rollout-plan", content)

    def test_risk_templates_exist_with_substantive_guidance(self):
        threat_template = ADAPTERS / "openspec" / "sdlc-governed" / "templates" / "threat-note.md"
        rollout_template = ADAPTERS / "openspec" / "sdlc-governed" / "templates" / "rollout-plan.md"
        self.assertTrue(threat_template.is_file(), f"missing {threat_template}")
        self.assertTrue(rollout_template.is_file(), f"missing {rollout_template}")

        threat_content = threat_template.read_text(encoding="utf-8")
        self.assertIn("Critical", threat_content)
        self.assertIn("Threat", threat_content)

        rollout_content = rollout_template.read_text(encoding="utf-8")
        self.assertIn("Critical", rollout_content)
        self.assertIn("Rollout", rollout_content)

    def test_config_fragment_contains_additive_guidance(self):
        config_path = ADAPTERS / "openspec" / "config.fragment.yaml"
        self.assertTrue(config_path.is_file(), f"missing {config_path}")
        content = config_path.read_text(encoding="utf-8")
        self.assertIn("apply", content)
        self.assertIn("archive", content)
        self.assertIn("sdlc check evidence", content)

    def test_cleanroom_openspec_adoption_measured_steps_and_gate_outcome(self):
        """Execute measured clean-room adoption of OpenSpec governance package into an isolated project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            # Setup isolated repo with existing OpenSpec specs
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Adoption Tester"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "tester@example.invalid"], check=True)

            existing_config = repo / ".openspec" / "config.yaml"
            existing_config.parent.mkdir(parents=True)
            existing_config.write_text("existing_key: preserved_value\n", encoding="utf-8")

            # Setup baseline commit
            test_file = repo / "tests" / "test_widget.py"
            test_file.parent.mkdir(parents=True)
            test_file.write_text("def test_create(): pass\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "initial baseline"], cwd=repo, check=True)
            base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()

            # Predeclared measurement boundary begins here
            adoption_steps = []

            # Step 1: Install gate runtime payload
            step1_cmd = [sys.executable, "-B", str(ROOT / "scripts" / "install.py"), str(repo)]
            res1 = subprocess.run(step1_cmd, capture_output=True, text=True)
            self.assertEqual(res1.returncode, 0, res1.stderr)
            adoption_steps.append("install_gate_runtime")

            # Step 2: Copy sdlc-governed schema into project openspec/schemas/
            schema_target = repo / "openspec" / "schemas" / "sdlc-governed"
            shutil.copytree(ADAPTERS / "openspec" / "sdlc-governed", schema_target)
            adoption_steps.append("copy_sdlc_governed_schema")

            # Step 3: Additive merge of operation guidance into .openspec/config.yaml
            fragment_text = (ADAPTERS / "openspec" / "config.fragment.yaml").read_text(encoding="utf-8")
            with open(existing_config, "a", encoding="utf-8") as f:
                f.write("\n" + fragment_text)
            adoption_steps.append("merge_config_fragment")

            # Commit the baseline configuration on main
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "adopt gate and schema on main"], cwd=repo, check=True)
            base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()

            # Switch to feature branch for the change
            subprocess.run(["git", "checkout", "-q", "-b", "feature-widget"], cwd=repo, check=True)

            # Step 4: Add an authored Standard change bundle using sdlc-governed
            change_dir = repo / "openspec" / "changes" / "widget-feature"
            shutil.copytree(ROOT / "tests" / "fixtures" / "interop" / "openspec_standard", change_dir)
            (change_dir / ".openspec.yaml").write_text("schema: sdlc-governed\ncreated: 2026-11-11\n", encoding="utf-8")
            (repo / "tests" / "test_widget.py").write_text("def test_create():\n    assert True\n", encoding="utf-8")
            adoption_steps.append("create_sdlc_governed_change")

            # Step 5: Run gate verification on the change
            pr_body = repo / "pr_body.md"
            pr_body.write_text(
                "## Intent\n"
                "Add widget feature to system.\n\n"
                "Spec: openspec/changes/widget-feature\n\n"
                "## Trace\n"
                "Tools: manual verification with pytest\n"
                "Decisions: followed sdlc-governed pattern\n\n"
                "## Review notes\n"
                "Verified all widget criteria locally against test_widget.py.\n",
                encoding="utf-8"
            )
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "add widget feature"], cwd=repo, check=True)
            head_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()

            gate_cmd = [
                sys.executable, "-B", str(repo / "scripts" / "sdlc.py"),
                "check", "evidence",
                "--repo-root", str(repo),
                "--base", base_sha,
                "--head", head_sha,
                "--pr-body-file", str(pr_body),
            ]
            res_gate = subprocess.run(gate_cmd, capture_output=True, text=True)
            adoption_steps.append("execute_gate_check")
            # Predeclared measurement boundary ends here

            self.assertEqual(len(adoption_steps), 5)
            self.assertEqual(res_gate.returncode, 0, res_gate.stdout + res_gate.stderr)
            self.assertIn("Standard", res_gate.stdout)

            # Verify original configuration survived intact
            updated_config_text = existing_config.read_text(encoding="utf-8")
            self.assertIn("existing_key: preserved_value", updated_config_text)
            self.assertIn("operations:", updated_config_text)


class SpecKitGovernancePackageContract(unittest.TestCase):
    """Contract tests for Spec Kit extension and preset."""

    def test_extension_manifest_and_delegate_exist(self):
        ext_manifest = ADAPTERS / "spec-kit" / "extension" / "extension.yml"
        delegate = ADAPTERS / "spec-kit" / "extension" / "bin" / "speckit-sdlc-gate"
        self.assertTrue(ext_manifest.is_file(), f"missing {ext_manifest}")
        self.assertTrue(delegate.is_file(), f"missing {delegate}")

        manifest_text = ext_manifest.read_text(encoding="utf-8")
        self.assertIn("speckit.sdlc.gate", manifest_text)
        self.assertIn("before-implement", manifest_text)

    def test_preset_manifest_and_append_templates_exist(self):
        preset_manifest = ADAPTERS / "spec-kit" / "preset" / "preset.yml"
        plan_template = ADAPTERS / "spec-kit" / "preset" / "templates" / "plan-additions.md"
        tasks_template = ADAPTERS / "spec-kit" / "preset" / "templates" / "tasks-additions.md"

        self.assertTrue(preset_manifest.is_file(), f"missing {preset_manifest}")
        self.assertTrue(plan_template.is_file(), f"missing {plan_template}")
        self.assertTrue(tasks_template.is_file(), f"missing {tasks_template}")

        manifest_text = preset_manifest.read_text(encoding="utf-8")
        self.assertIn("strategy: append", manifest_text)
        self.assertIn("plan-template", manifest_text)
        self.assertIn("tasks-template", manifest_text)

    def test_delegate_fails_when_runtime_missing_without_fallback(self):
        delegate = ADAPTERS / "spec-kit" / "extension" / "bin" / "speckit-sdlc-gate"
        with tempfile.TemporaryDirectory() as tmpdir:
            res = subprocess.run(
                [sys.executable, "-B", str(delegate), "--base", "abc", "--head", "def", "--pr-body-file", "body.md"],
                cwd=tmpdir, capture_output=True, text=True
            )
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("runtime is not installed", res.stderr + res.stdout)

    def test_delegate_propagates_exit_and_output_on_gate_failure(self):
        delegate = ADAPTERS / "spec-kit" / "extension" / "bin" / "speckit-sdlc-gate"
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            # Install runtime into repo
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "install.py"), str(repo)], check=True)
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
            sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()

            pr_body = repo / "body.md"
            pr_body.write_text("empty pr body\n", encoding="utf-8")

            # Missing evidence causes gate in CI mode to fail with exit code 1
            res = subprocess.run(
                [sys.executable, "-B", str(delegate), "--ci", "--base", sha, "--head", sha, "--pr-body-file", str(pr_body)],
                cwd=repo, capture_output=True, text=True
            )
            self.assertEqual(res.returncode, 1)
            self.assertIn("missing evidence", res.stdout + res.stderr)

    def test_cleanroom_speckit_adoption_measured_steps_and_gate_outcome(self):
        """Execute measured clean-room adoption of Spec Kit governance into an isolated project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Adoption Tester"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "tester@example.invalid"], check=True)

            existing_template = repo / ".speckit" / "templates" / "existing-custom.md"
            existing_template.parent.mkdir(parents=True)
            existing_template.write_text("preserved upstream template\n", encoding="utf-8")

            test_file = repo / "tests" / "test_user_profile.py"
            test_file.parent.mkdir(parents=True)
            test_file.write_text("def test_update_display_name(): pass\n", encoding="utf-8")

            # Predeclared measurement boundary begins here
            adoption_steps = []

            # Step 1: Install gate runtime payload
            res1 = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "install.py"), str(repo)], capture_output=True, text=True)
            self.assertEqual(res1.returncode, 0, res1.stderr)
            adoption_steps.append("install_gate_runtime")

            # Step 2: Install Spec Kit extension
            ext_target = repo / ".speckit" / "extensions" / "speckit-sdlc-gate"
            shutil.copytree(ADAPTERS / "spec-kit" / "extension", ext_target)
            adoption_steps.append("install_speckit_extension")

            # Step 3: Install Spec Kit preset
            preset_target = repo / ".speckit" / "presets" / "sdlc-governed"
            shutil.copytree(ADAPTERS / "spec-kit" / "preset", preset_target)
            adoption_steps.append("install_speckit_preset")

            # Commit baseline on main
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "adopt gate runtime and speckit adapters"], cwd=repo, check=True)
            base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()

            # Switch to feature branch
            subprocess.run(["git", "checkout", "-q", "-b", "feature-profile"], cwd=repo, check=True)

            # Step 4: Add an authored Standard Spec Kit feature bundle
            feat_dir = repo / "specs" / "user-profile"
            shutil.copytree(ROOT / "tests" / "fixtures" / "interop" / "speckit_standard", feat_dir)
            (repo / "tests" / "test_user_profile.py").write_text("def test_update_display_name():\n    assert True\n", encoding="utf-8")
            adoption_steps.append("create_speckit_feature_bundle")

            # Step 5: Run delegate / gate verification on the change
            pr_body = repo / "pr_body.md"
            pr_body.write_text(
                "## Intent\n"
                "Add user profile editing capability.\n\n"
                "Spec: specs/user-profile\n\n"
                "## Trace\n"
                "Tools: speckit compose and pytest\n"
                "Decisions: followed speckit preset\n\n"
                "## Review notes\n"
                "Verified scenarios against tests/test_user_profile.py.\n",
                encoding="utf-8"
            )
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "add user profile feature"], cwd=repo, check=True)
            head_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()

            delegate_bin = ext_target / "bin" / "speckit-sdlc-gate"
            gate_cmd = [
                sys.executable, "-B", str(delegate_bin),
                "--repo-root", str(repo),
                "--base", base_sha,
                "--head", head_sha,
                "--pr-body-file", str(pr_body),
            ]
            res_gate = subprocess.run(gate_cmd, capture_output=True, text=True)
            adoption_steps.append("execute_delegate_gate_check")
            # Predeclared measurement boundary ends here

            self.assertEqual(len(adoption_steps), 5)
            self.assertEqual(res_gate.returncode, 0, res_gate.stdout + res_gate.stderr)
            self.assertIn("Standard", res_gate.stdout)

            # Verify surviving existing template
            self.assertTrue(existing_template.is_file())
            self.assertEqual(existing_template.read_text(encoding="utf-8"), "preserved upstream template\n")


if __name__ == "__main__":
    unittest.main()
