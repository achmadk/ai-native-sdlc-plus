"""Lifecycle, ownership-state, and dry-run/update/uninstall tests (WS3 Section 3)."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import unittest
from unittest import mock

if __package__:
    from . import support
else:
    import support


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SDLC = SCRIPTS / "sdlc.py"
STATE = ".sdlc-install.json"


def clean_env(**extra):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key != "GITHUB_STEP_SUMMARY"
    }
    env.update(PYTHONDONTWRITEBYTECODE="1", **extra)
    return env


class LifecycleTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = support.TemporaryDirectory(prefix="sdlc-lifecycle-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.elsewhere = self.work / "unrelated-cwd"
        self.elsewhere.mkdir()

    def copy_distribution(self, name="dist"):
        dest = self.work / name
        dest.mkdir()
        for folder in ("scripts", "skills", "adapters", ".github", "hooks"):
            shutil.copytree(
                ROOT / folder,
                dest / folder,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        for filename in ("install.sh", "install.ps1", ".gitattributes", "AGENTS.md", "LICENSE"):
            src = ROOT / filename
            if src.is_file():
                shutil.copy2(src, dest / filename)
        return dest

    def run_python(self, script_path, *args, cwd=None, env=None):
        return subprocess.run(
            [sys.executable, "-I", "-B", str(script_path)] + [str(a) for a in args],
            cwd=str(cwd or self.elsewhere),
            env=clean_env(**(env or {})),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

    def run_sdlc(self, *args, dist=None, cwd=None, env=None):
        entry = (Path(dist) / "scripts" / "sdlc.py") if dist else SDLC
        return self.run_python(entry, *args, cwd=cwd, env=env)

    def snapshot_tree(self, root):
        root = Path(root)
        if not root.exists():
            return None
        snap = {}
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root).as_posix()
            if ".git" in path.relative_to(root).parts:
                continue
            if path.is_symlink():
                snap[rel] = ("symlink", os.readlink(path))
            elif path.is_file():
                st = path.stat()
                snap[rel] = ("file", path.read_bytes(), stat.S_IMODE(st.st_mode), st.st_mtime_ns)
            elif path.is_dir():
                snap[rel] = ("dir",)
        return snap

    def file_record(self, data, mode="0644"):
        if isinstance(data, str):
            data = data.encode("utf-8")
        if os.name == "nt" and int(mode, 8) & stat.S_IWUSR:
            mode = "0644"
        return {
            "sha256": hashlib.sha256(data).hexdigest(),
            "mode": mode,
            "mode_sha256": hashlib.sha256(mode.encode("ascii")).hexdigest(),
        }


class StatusAndDryRunPlanningContract(LifecycleTestCase):
    def test_status_and_init_dry_run_create_no_directories_or_files(self):
        missing_parent = self.work / "nonexistent-parent"
        missing_target = missing_parent / "project"

        status_json = self.run_sdlc("status", "--root", missing_target, "--json")
        self.assertEqual(status_json.returncode, 0, status_json.stderr)
        self.assertFalse(missing_parent.exists(), "status must not create target directories")
        doc = json.loads(status_json.stdout)
        self.assertFalse(doc["installed"])
        self.assertEqual(doc["policy"]["path"], "AGENTS.md")
        self.assertEqual(doc["policy"]["ownership"], "user-owned")
        self.assertEqual(doc["policy"]["status"], "missing")
        self.assertIn("scripts/lane.py", doc["files"]["missing"])

        status_txt = self.run_sdlc("status", "--root", missing_target)
        self.assertEqual(status_txt.returncode, 0, status_txt.stderr)
        self.assertFalse(missing_parent.exists())

        dry_json = self.run_sdlc("init", "--root", missing_target, "--dry-run", "--json")
        self.assertEqual(dry_json.returncode, 0, dry_json.stderr)
        self.assertFalse(missing_parent.exists(), "init --dry-run must not create target directories")
        plan = json.loads(dry_json.stdout)
        self.assertTrue(plan["dry_run"])
        self.assertEqual(plan["selected_agents"], [])
        self.assertEqual(plan["setup_mode"], "core-only")
        self.assertEqual(plan["policy"]["action"], "create-starter")
        self.assertNotIn("AGENTS.md", plan["owned_destinations"])

        dry_txt = self.run_sdlc("init", "--root", missing_target, "--dry-run")
        self.assertEqual(dry_txt.returncode, 0, dry_txt.stderr)
        self.assertIn("core-only", dry_txt.stdout.lower())
        self.assertFalse(missing_parent.exists())

    def test_adopt_legacy_v1_install_and_distinguish_file_states_without_mutation(self):
        dist_v1 = self.copy_distribution("dist-v1")
        dist_v2 = self.copy_distribution("dist-v2")
        target = self.work / "legacy-project"
        target.mkdir()

        legacy = self.run_python(dist_v1 / "scripts" / "install.py", target)
        self.assertEqual(legacy.returncode, 0, legacy.stderr)

        # Advance one file in dist_v2 so target has an unchanged owned file with an update available.
        upgraded_rel = "skills/ai-sdlc/references/onboarding.md"
        (dist_v2 / upgraded_rel).write_text("# Updated onboarding in dist_v2\n", encoding="utf-8")

        # Modify one owned file, delete one owned file, and add user-owned AGENTS.md + app code.
        modified_rel = "scripts/lane-config.yaml"
        missing_rel = "hooks/pre-push.ps1"
        (target / modified_rel).write_text("# Locally edited config\n", encoding="utf-8")
        (target / missing_rel).unlink()
        (target / "AGENTS.md").write_text("# Custom project policy\n", encoding="utf-8")
        (target / "src").mkdir()
        (target / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

        before = self.snapshot_tree(target)
        res = self.run_sdlc("status", "--root", target, "--json", dist=dist_v2)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.snapshot_tree(target), before, "status must be strictly read-only")

        status = json.loads(res.stdout)
        self.assertTrue(status["installed"])
        self.assertEqual(status["state_version"], 1)
        self.assertIn(upgraded_rel, status["files"]["update_available"])
        self.assertIn(modified_rel, status["files"]["modified"])
        self.assertIn(missing_rel, status["files"]["missing"])
        self.assertIn("scripts/lane.py", status["files"]["matching"])
        self.assertEqual(status["policy"]["status"], "present")
        self.assertEqual(status["policy"]["ownership"], "user-owned")

    def test_invalid_or_unrecognized_state_fails_before_mutation(self):
        valid_manifest_hash = "sha256:" + ("a" * 64)
        good_rec = self.file_record("ok\n")
        invalid_payloads = [
            "{not-json",
            '{"version": 1, "version": 1, "source_manifest": "%s", "files": {}}' % valid_manifest_hash,
            json.dumps({"version": 2, "source_manifest": valid_manifest_hash, "files": {}}),
            json.dumps({"version": 1, "source_manifest": "md5:1234", "files": {}}),
            json.dumps({"version": 1, "source_manifest": valid_manifest_hash, "extra": True, "files": {}}),
            json.dumps({"version": 1, "source_manifest": valid_manifest_hash, "files": {"../escape.py": good_rec}}),
            json.dumps({"version": 1, "source_manifest": valid_manifest_hash, "files": {"scripts\\lane.py": good_rec}}),
            json.dumps(
                {
                    "version": 1,
                    "source_manifest": valid_manifest_hash,
                    "files": {"scripts/lane.py": {"sha256": "bad", "mode": "0644", "mode_sha256": good_rec["mode_sha256"]}},
                }
            ),
            # Forged unrecognized path in .sdlc-install.json must not be trusted.
            json.dumps({"version": 1, "source_manifest": valid_manifest_hash, "files": {"README.md": good_rec}}),
            json.dumps({"version": 1, "source_manifest": valid_manifest_hash, "files": {"AGENTS.md": good_rec}}),
        ]
        for idx, raw_state in enumerate(invalid_payloads):
            with self.subTest(case=idx):
                target = self.work / ("bad-state-%d" % idx)
                target.mkdir()
                (target / "README.md").write_text("ok\n", encoding="utf-8")
                (target / "AGENTS.md").write_text("ok\n", encoding="utf-8")
                (target / STATE).write_text(raw_state, encoding="utf-8")
                before = self.snapshot_tree(target)

                st = self.run_sdlc("status", "--root", target)
                self.assertIn(st.returncode, (1, 3), (idx, st.stdout, st.stderr))
                self.assertNotIn("Traceback", st.stderr)
                self.assertEqual(self.snapshot_tree(target), before)

                init_dry = self.run_sdlc("init", "--root", target, "--dry-run")
                self.assertEqual(init_dry.returncode, 1, (idx, init_dry.stdout, init_dry.stderr))
                self.assertNotIn("Traceback", init_dry.stderr)
                self.assertEqual(self.snapshot_tree(target), before)

                init_real = self.run_sdlc("init", "--root", target)
                self.assertEqual(init_real.returncode, 1, (idx, init_real.stdout, init_real.stderr))
                self.assertEqual(self.snapshot_tree(target), before)

    def test_init_preserves_v1_schema_starter_policy_and_recognized_existing_ownership(self):
        target = self.work / "init-project"
        res = self.run_sdlc("init", "--root", target, "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)
        self.assertEqual(out["setup_mode"], "core-only")
        self.assertTrue((target / "AGENTS.md").is_file(), "starter AGENTS.md must be created when absent")

        state = json.loads((target / STATE).read_text(encoding="utf-8"))
        self.assertEqual(set(state), {"version", "source_manifest", "files"})
        self.assertEqual(state["version"], 1)
        self.assertNotIn("AGENTS.md", state["files"], "canonical AGENTS.md must never be tool-owned")
        for rec in state["files"].values():
            self.assertEqual(set(rec), {"sha256", "mode", "mode_sha256"})

        # Seed a recognized managed profile file in state and on disk, then re-run core-only init.
        claude_bytes = b"# Managed CLAUDE adapter\n"
        (target / "CLAUDE.md").write_bytes(claude_bytes)
        state["files"]["CLAUDE.md"] = self.file_record(claude_bytes, "0644")
        (target / STATE).write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        dry = self.run_sdlc("init", "--root", target, "--dry-run", "--json")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("CLAUDE.md", json.loads(dry.stdout)["preserved_owned_files"])

        rerun = self.run_sdlc("init", "--root", target, "--json")
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        state_after = json.loads((target / STATE).read_text(encoding="utf-8"))
        self.assertIn("CLAUDE.md", state_after["files"], "recognized existing owned records must not be dropped")
        self.assertEqual((target / "CLAUDE.md").read_bytes(), claude_bytes)


class UpdateReconciliationContract(LifecycleTestCase):
    def test_safe_update_reconciles_unchanged_owned_files_and_preserves_policy_and_unowned(self):
        dist_v1 = self.copy_distribution("update-dist-v1")
        dist_v2 = self.copy_distribution("update-dist-v2")
        target = self.work / "update-project"

        init_res = self.run_sdlc("init", "--root", target, dist=dist_v1)
        self.assertEqual(init_res.returncode, 0, init_res.stderr)

        custom_policy = b"# Team canonical policy\nNever overwrite me.\n"
        (target / "AGENTS.md").write_bytes(custom_policy)
        (target / "src").mkdir()
        (target / "src" / "main.py").write_text("VALUE = 42\n", encoding="utf-8")

        # Update two files in dist_v2 and delete one unmodified owned file in target to verify restoration.
        changed_a = "skills/ai-sdlc/references/onboarding.md"
        changed_b = "scripts/lane_backtest.py"
        restored_c = "hooks/pre-push.ps1"
        new_a = b"# Onboarding v2\n"
        new_b = (dist_v2 / changed_b).read_bytes() + b"\n# v2 marker\n"
        (dist_v2 / changed_a).write_bytes(new_a)
        (dist_v2 / changed_b).write_bytes(new_b)
        (target / restored_c).unlink()

        before_dry = self.snapshot_tree(target)
        dry = self.run_sdlc("update", "--root", target, "--dry-run", "--json", dist=dist_v2)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(self.snapshot_tree(target), before_dry, "update --dry-run must not mutate files")
        dry_doc = json.loads(dry.stdout)
        for rel in (changed_a, changed_b, restored_c):
            self.assertIn(rel, dry_doc["planned_writes"])

        upd = self.run_sdlc("update", "--root", target, "--json", dist=dist_v2)
        self.assertEqual(upd.returncode, 0, upd.stderr)
        self.assertEqual((target / changed_a).read_bytes(), new_a)
        self.assertEqual((target / changed_b).read_bytes(), new_b)
        self.assertEqual((target / restored_c).read_bytes(), (dist_v2 / restored_c).read_bytes())
        self.assertEqual((target / "AGENTS.md").read_bytes(), custom_policy)
        self.assertEqual((target / "src" / "main.py").read_text(encoding="utf-8"), "VALUE = 42\n")

        state = json.loads((target / STATE).read_text(encoding="utf-8"))
        self.assertNotIn("AGENTS.md", state["files"])
        self.assertEqual(state["files"][changed_a]["sha256"], hashlib.sha256(new_a).hexdigest())

    def test_update_blocks_on_user_edits_uninitialized_roots_unknown_state_and_rejects_force(self):
        # 1. --force is never supported (exit 2).
        force_res = self.run_sdlc("update", "--root", self.work, "--force")
        self.assertEqual(force_res.returncode, 2)

        # 2. Uninitialized directory fails without creating files.
        uninit = self.work / "uninitialized-dir"
        uninit_res = self.run_sdlc("update", "--root", uninit)
        self.assertEqual(uninit_res.returncode, 1, uninit_res.stderr)
        self.assertFalse(uninit.exists())

        # 3. Locally edited owned file blocks entire update preflight.
        dist_v1 = self.copy_distribution("conflict-v1")
        dist_v2 = self.copy_distribution("conflict-v2")
        target = self.work / "conflict-project"
        self.assertEqual(self.run_sdlc("init", "--root", target, dist=dist_v1).returncode, 0)
        (dist_v2 / "hooks" / "pre-push.sh").write_bytes(b"#!/bin/sh\n# v2\nexit 0\n")
        (target / "scripts" / "lane-config.yaml").write_text("# local edit\n", encoding="utf-8")

        before = self.snapshot_tree(target)
        conflict = self.run_sdlc("update", "--root", target, dist=dist_v2)
        self.assertEqual(conflict.returncode, 1)
        self.assertIn("scripts/lane-config.yaml", conflict.stderr)
        self.assertEqual(self.snapshot_tree(target), before)

        # 4. Unrecognized path in .sdlc-install.json blocks update preflight.
        state = json.loads((target / STATE).read_text(encoding="utf-8"))
        # Restore lane-config.yaml first so only the forged state path triggers failure.
        (target / "scripts" / "lane-config.yaml").write_bytes((dist_v1 / "scripts" / "lane-config.yaml").read_bytes())
        (target / "README.md").write_text("user readme\n", encoding="utf-8")
        state["files"]["README.md"] = self.file_record("user readme\n")
        (target / STATE).write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        before_forged = self.snapshot_tree(target)
        forged_res = self.run_sdlc("update", "--root", target, dist=dist_v2)
        self.assertEqual(forged_res.returncode, 1)
        self.assertIn("README.md", forged_res.stderr)
        self.assertEqual(self.snapshot_tree(target), before_forged)


class UninstallContract(LifecycleTestCase):
    def test_clean_uninstall_removes_owned_outputs_and_retains_starter_policy_and_unrelated_content(self):
        target = self.work / "uninstall-clean"
        target.mkdir()
        (target / "README.md").write_text("# App\n", encoding="utf-8")
        (target / "src").mkdir()
        (target / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
        (target / "unrelated-empty").mkdir()
        (target / ".github").mkdir()
        (target / ".github" / "CODEOWNERS").write_text("* @team\n", encoding="utf-8")

        init_res = self.run_sdlc("init", "--root", target)
        self.assertEqual(init_res.returncode, 0, init_res.stderr)
        self.assertTrue((target / "AGENTS.md").is_file())
        starter_bytes = (target / "AGENTS.md").read_bytes()

        before_dry = self.snapshot_tree(target)
        dry = self.run_sdlc("uninstall", "--root", target, "--dry-run", "--json")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(self.snapshot_tree(target), before_dry, "uninstall --dry-run must not delete anything")
        dry_doc = json.loads(dry.stdout)
        self.assertIn("scripts/lane.py", dry_doc["planned_removals"])
        self.assertNotIn("AGENTS.md", dry_doc["planned_removals"])

        rem = self.run_sdlc("uninstall", "--root", target, "--json")
        self.assertEqual(rem.returncode, 0, rem.stderr)
        rem_doc = json.loads(rem.stdout)
        self.assertEqual(rem_doc["policy"]["action"], "retained-user-owned")

        # State and owned files must be gone; starter AGENTS.md and unrelated files/dirs must remain!
        self.assertFalse((target / STATE).exists())
        self.assertFalse((target / "scripts" / "lane.py").exists())
        self.assertFalse((target / "scripts").exists(), "empty managed directory should be tidied")
        self.assertTrue((target / "AGENTS.md").is_file(), "starter AGENTS.md must survive uninstall")
        self.assertEqual((target / "AGENTS.md").read_bytes(), starter_bytes)
        self.assertTrue((target / "README.md").is_file())
        self.assertTrue((target / "src" / "app.py").is_file())
        self.assertTrue((target / "unrelated-empty").is_dir(), "unrelated empty directory must survive")
        self.assertTrue((target / ".github" / "CODEOWNERS").is_file(), "unowned file inside shared parent must survive")

    def test_uninstall_refuses_modified_files_forged_targets_uninitialized_roots_and_links(self):
        # 1. Uninitialized root fails without mutating anything.
        uninit = self.work / "uninstall-missing"
        res_missing = self.run_sdlc("uninstall", "--root", uninit)
        self.assertEqual(res_missing.returncode, 1)
        self.assertFalse(uninit.exists())

        # 2. Modified owned file blocks preflight without deleting any owned file.
        target = self.work / "uninstall-modified"
        self.assertEqual(self.run_sdlc("init", "--root", target).returncode, 0)
        (target / "scripts" / "lane-config.yaml").write_text("# user customized\n", encoding="utf-8")
        before_mod = self.snapshot_tree(target)
        res_mod = self.run_sdlc("uninstall", "--root", target)
        self.assertEqual(res_mod.returncode, 1)
        self.assertIn("scripts/lane-config.yaml", res_mod.stderr)
        self.assertEqual(self.snapshot_tree(target), before_mod)

        # 3. Forged unrelated target in .sdlc-install.json is refused without deleting it.
        target_forged = self.work / "uninstall-forged"
        self.assertEqual(self.run_sdlc("init", "--root", target_forged).returncode, 0)
        (target_forged / "important.txt").write_text("do not delete\n", encoding="utf-8")
        state = json.loads((target_forged / STATE).read_text(encoding="utf-8"))
        state["files"]["important.txt"] = self.file_record("do not delete\n")
        (target_forged / STATE).write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        before_forged = self.snapshot_tree(target_forged)
        res_forged = self.run_sdlc("uninstall", "--root", target_forged)
        self.assertEqual(res_forged.returncode, 1)
        self.assertIn("important.txt", res_forged.stderr)
        self.assertTrue((target_forged / "important.txt").is_file())
        self.assertEqual(self.snapshot_tree(target_forged), before_forged)

        # 4. Junction / symlink hazard blocks preflight without deleting outside target.
        if os.name == "nt":
            target_link = self.work / "uninstall-junction"
            self.assertEqual(self.run_sdlc("init", "--root", target_link).returncode, 0)
            outside = self.work / "outside-dir"
            outside.mkdir()
            shutil.copy2(target_link / "hooks" / "pre-push.ps1", outside / "pre-push.ps1")
            shutil.rmtree(target_link / "hooks")
            support.make_junction(target_link / "hooks", outside)
            res_junc = self.run_sdlc("uninstall", "--root", target_link)
            self.assertEqual(res_junc.returncode, 1)
            self.assertTrue((outside / "pre-push.ps1").is_file(), "external target behind junction must survive")
            self.assertTrue((target_link / STATE).is_file())


class LifecycleRaceAndFailureContract(LifecycleTestCase):
    def _load_install_mod(self):
        spec = importlib.util.spec_from_file_location("_test_install_mod", SCRIPTS / "install.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_init_and_update_partial_failures_and_post_preflight_races(self):
        mod = self._load_install_mod()
        dist = self.copy_distribution("race-dist")
        target = self.work / "partial-init"
        manifest = json.loads((dist / "scripts" / "install-manifest.json").read_text(encoding="utf-8"))
        first_rel = manifest["files"][0]["destination"]
        second_rel = manifest["files"][1]["destination"]

        real_replace = os.replace

        def fail_on_second(src, dst):
            if Path(dst) == target / second_rel:
                raise OSError("simulated disk write failure")
            return real_replace(src, dst)

        with mock.patch.object(mod.os, "replace", side_effect=fail_on_second):
            with self.assertRaises(mod.InstallError) as ctx:
                mod.init_project(str(target), str(dist))
        self.assertIn("AGENTS.md", ctx.exception.changed)
        self.assertIn(first_rel, ctx.exception.changed)
        self.assertFalse((target / STATE).exists(), "partial init must never publish completed ownership state")

        # If a concurrent user edit writes to second_rel before retry, retry must block rather than overwrite it.
        (target / second_rel).parent.mkdir(parents=True, exist_ok=True)
        (target / second_rel).write_text("concurrent user edit\n", encoding="utf-8")
        with self.assertRaises(mod.InstallError) as conflict_ctx:
            mod.init_project(str(target), str(dist))
        self.assertIn(second_rel, str(conflict_ctx.exception))
        self.assertEqual((target / second_rel).read_text(encoding="utf-8"), "concurrent user edit\n")

        # Once the user removes the conflicting file, conservative retry completes cleanly.
        (target / second_rel).unlink()
        summary = mod.init_project(str(target), str(dist))
        self.assertIn(first_rel, summary["retained_files"])
        self.assertTrue((target / STATE).is_file())

        # Now test post-preflight race during update_project.
        for rel in (first_rel, second_rel):
            with (dist / rel).open("ab") as handle:
                handle.write(b"\n# v2 update\n")
        old_state_bytes = (target / STATE).read_bytes()

        def racing_update_replace(src, dst):
            res = real_replace(src, dst)
            if Path(dst) == target / first_rel:
                (target / second_rel).write_text("mid-update user edit\n", encoding="utf-8")
            return res

        with mock.patch.object(mod.os, "replace", side_effect=racing_update_replace):
            with self.assertRaises(mod.InstallError) as race_ctx:
                mod.update_project(str(target), str(dist))
        self.assertIn("changed after preflight", str(race_ctx.exception))
        self.assertEqual((target / second_rel).read_text(encoding="utf-8"), "mid-update user edit\n")
        self.assertEqual((target / STATE).read_bytes(), old_state_bytes)

    def test_uninstall_partial_failure_retains_state_and_retry_respects_concurrent_edits(self):
        mod = self._load_install_mod()
        target = self.work / "partial-uninstall"
        mod.init_project(str(target), str(ROOT))
        state = json.loads((target / STATE).read_text(encoding="utf-8"))
        sorted_owned = sorted(state["files"])
        first_rel, second_rel, third_rel = sorted_owned[0], sorted_owned[1], sorted_owned[2]

        real_unlink = os.unlink

        def fail_on_third_unlink(path):
            if Path(path) == target / third_rel:
                raise OSError("simulated unlink failure")
            return real_unlink(path)

        with mock.patch.object(mod.os, "unlink", side_effect=fail_on_third_unlink):
            with self.assertRaises(mod.InstallError) as ctx:
                mod.uninstall_project(str(target), str(ROOT))
        self.assertEqual(list(ctx.exception.changed), [first_rel, second_rel])
        self.assertTrue((target / STATE).is_file(), "state must survive partial uninstall")
        self.assertTrue((target / third_rel).is_file())

        # Concurrent user edit on third_rel before retry must block uninstall rather than deleting the edit.
        original_third = (target / third_rel).read_bytes()
        (target / third_rel).write_bytes(b"user edited after partial uninstall\n")
        with self.assertRaises(mod.InstallError) as edit_ctx:
            mod.uninstall_project(str(target), str(ROOT))
        self.assertIn(third_rel, str(edit_ctx.exception))
        self.assertTrue((target / third_rel).is_file())

        # Restore third_rel to owned bytes and retry: already-removed files are skipped and state is removed at end.
        (target / third_rel).write_bytes(original_third)
        result = mod.uninstall_project(str(target), str(ROOT))
        self.assertIn(first_rel, result["already_missing"])
        self.assertIn(second_rel, result["already_missing"])
        self.assertTrue(result["state_removed"])
        self.assertFalse((target / STATE).exists())
        self.assertTrue((target / "AGENTS.md").is_file())

    def test_legacy_installation_lifecycle_end_to_end(self):
        dist_v1 = self.copy_distribution("legacy-e2e-v1")
        dist_v2 = self.copy_distribution("legacy-e2e-v2")
        target = self.work / "legacy-e2e-target"
        target.mkdir()

        # 1. Install with legacy scripts/install.py (no AGENTS.md created).
        res_legacy = self.run_python(dist_v1 / "scripts" / "install.py", target)
        self.assertEqual(res_legacy.returncode, 0, res_legacy.stderr)
        self.assertFalse((target / "AGENTS.md").exists())

        # 2. Update via sdlc update using dist_v2.
        (dist_v2 / "adapters" / "ci" / "README.md").write_text("# Updated CI adapter docs\n", encoding="utf-8")
        res_upd = self.run_sdlc("update", "--root", target, "--json", dist=dist_v2)
        self.assertEqual(res_upd.returncode, 0, res_upd.stderr)
        self.assertFalse((target / "AGENTS.md").exists(), "update must not invent AGENTS.md when absent")
        self.assertEqual(
            (target / "adapters" / "ci" / "README.md").read_text(encoding="utf-8"),
            "# Updated CI adapter docs\n",
        )

        # 3. Uninstall via sdlc uninstall.
        res_uninst = self.run_sdlc("uninstall", "--root", target, "--json", dist=dist_v2)
        self.assertEqual(res_uninst.returncode, 0, res_uninst.stderr)
        self.assertFalse((target / STATE).exists())
        self.assertEqual(list(target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
