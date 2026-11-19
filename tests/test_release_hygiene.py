"""Contracts for coherent product release identity and release preparation."""

import email
import datetime
import importlib.util
import json
import os
from pathlib import Path
import shutil
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "scripts" / "version.py"
BUILD_WHEEL = ROOT / "scripts" / "build_wheel.py"
EXPECTED_VERSION = "0.3.0"


class SharedVersionContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sdlc-release-version-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def version(self):
        self.assertTrue(VERSION_FILE.is_file(), "shared product version resource is missing")
        spec = importlib.util.spec_from_file_location("release_version_under_test", str(VERSION_FILE))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.VERSION, EXPECTED_VERSION)
        return module

    def command(self, script, *args, cwd=None):
        return subprocess.run(
            [sys.executable, "-I", "-B", str(script)] + [str(arg) for arg in args],
            cwd=str(cwd or self.work), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", timeout=60,
        )

    def copy_runtime(self, name):
        target = self.work / name
        target.mkdir()
        manifest = json.loads((ROOT / "scripts/install-manifest.json").read_text(encoding="utf-8"))
        for item in manifest["files"]:
            destination = target / item["source"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / item["source"], destination)
        shutil.copy2(ROOT / "LICENSE", target / "LICENSE")
        return target

    def test_shared_resource_is_the_single_doctor_and_wheel_identity(self):
        self.version()
        from scripts import build_wheel, doctor
        self.assertEqual(doctor.VERSION, EXPECTED_VERSION)
        self.assertEqual(build_wheel.VERSION, EXPECTED_VERSION)

    def test_wheel_filename_metadata_dist_info_and_resource_agree(self):
        output = self.work / "wheel"
        result = self.command(BUILD_WHEEL, "--source-root", ROOT, "--out-dir", output)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        wheels = list(output.glob("*.whl"))
        self.assertEqual(len(wheels), 1)
        wheel = wheels[0]
        self.assertEqual(wheel.name, "ai_native_sdlc_plus-0.3.0-py3-none-any.whl")
        with zipfile.ZipFile(wheel) as archive:
            dist_info = "ai_native_sdlc_plus-0.3.0.dist-info"
            self.assertEqual({name.split("/")[0] for name in archive.namelist() if ".dist-info/" in name},
                             {dist_info})
            metadata = email.message_from_bytes(archive.read(dist_info + "/METADATA"))
            self.assertEqual(metadata["Version"], EXPECTED_VERSION)
            self.assertEqual(metadata.get_all("Requires-Dist", []), [])
            self.assertIn("_sdlc_runtime/scripts/version.py", archive.namelist())
            self.assertEqual(archive.read("_sdlc_runtime/scripts/version.py"), VERSION_FILE.read_bytes())

    def test_installed_doctor_and_front_door_use_their_own_version_resource(self):
        self.version()
        installed = self.work / "installed"
        result = self.command(ROOT / "scripts/install.py", installed)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        resource = installed / "scripts/version.py"
        self.assertTrue(resource.is_file(), "shared version must be in the installed allowlist")
        self.assertEqual(resource.read_bytes(), VERSION_FILE.read_bytes())
        state = json.loads((installed / ".sdlc-install.json").read_text(encoding="utf-8"))
        self.assertEqual(state["version"], 1)
        self.assertIn("scripts/version.py", state["files"])
        trap = self.work / "unrelated-cwd"
        trap.mkdir()
        marker = self.work / "version-shadow-executed"
        poison = "from pathlib import Path\nPath(%r).touch()\nVERSION='9.9.9'\n" % str(marker)
        (trap / "version.py").write_text(poison, encoding="utf-8")
        hostile = installed / "hostile-target"
        (hostile / "scripts").mkdir(parents=True)
        (hostile / "scripts/version.py").write_text(poison, encoding="utf-8")
        for script, args in (
            (installed / "scripts/doctor.py", ("--root", hostile, "--json")),
            (installed / "scripts/sdlc.py", ("doctor", "--root", hostile, "--json")),
        ):
            with self.subTest(script=script.name):
                observed = self.command(script, *args, cwd=trap)
                self.assertTrue(observed.stdout.strip(), observed.stderr)
                self.assertEqual(json.loads(observed.stdout)["version"], EXPECTED_VERSION)
                self.assertFalse(marker.exists(), "target or CWD version code must not execute")

    def test_missing_version_resource_fails_cleanly_without_a_fallback(self):
        self.version()
        runtime = self.copy_runtime("missing-version-runtime")
        resource = runtime / "scripts/version.py"
        self.assertTrue(resource.is_file(), "runtime payload must include its version resource")
        resource.unlink()
        for script, args in (
            (runtime / "scripts/doctor.py", ("--root", runtime, "--json")),
            (runtime / "scripts/sdlc.py", ("doctor", "--root", runtime, "--json")),
        ):
            with self.subTest(script=script.name):
                observed = self.command(script, *args)
                self.assertNotEqual(observed.returncode, 0)
                self.assertIn("version", (observed.stdout + observed.stderr).casefold())
                self.assertNotIn("Traceback", observed.stdout + observed.stderr)
        output = self.work / "missing-version-wheel"
        built = self.command(BUILD_WHEEL, "--source-root", runtime, "--out-dir", output)
        self.assertNotEqual(built.returncode, 0)
        self.assertIn("scripts/version.py", built.stdout + built.stderr)
        self.assertEqual(list(output.glob("*.whl")), [])

    def test_mismatched_build_source_version_is_not_executed_or_packaged(self):
        self.version()
        runtime = self.copy_runtime("mismatched-version-source")
        marker = self.work / "source-version-executed"
        resource = runtime / "scripts/version.py"
        self.assertTrue(resource.is_file())
        resource.write_text("from pathlib import Path\nPath(%r).touch()\nVERSION='9.9.9'\n" % str(marker),
                            encoding="utf-8")
        output = self.work / "mismatched-version-wheel"
        result = self.command(BUILD_WHEEL, "--source-root", runtime, "--out-dir", output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version", (result.stdout + result.stderr).casefold())
        self.assertNotIn("Traceback", result.stdout + result.stderr)
        self.assertFalse(marker.exists(), "the wheel builder must treat selected source version as data")
        self.assertEqual(list(output.glob("*.whl")), [])

    def test_version_reader_rejects_duplicate_computed_or_invalid_identity(self):
        module = self.version()
        self.assertEqual(module.read_version(b'VERSION = "0.3.0"\n'), EXPECTED_VERSION)
        for source in ('VERSION="0.3.0"\nVERSION="0.4.0"\n',
                       'VERSION=str("0.3.0")\n', 'VERSION="0.0.0.dev0"\n', 'VERSION=None\n'):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    module.read_version(source)

    def test_linked_runtime_version_is_refused_without_executing_its_target(self):
        self.version()
        runtime = self.copy_runtime("linked-version-runtime")
        marker = self.work / "linked-version-executed"
        poison = self.work / "untrusted-version.py"
        poison.write_text("from pathlib import Path\nPath(%r).touch()\nVERSION='9.9.9'\n" % str(marker),
                          encoding="utf-8")
        resource = runtime / "scripts/version.py"
        resource.unlink()
        try:
            resource.symlink_to(poison)
        except OSError as exc:
            self.skipTest("symlink creation unavailable: %s" % exc)
        result = self.command(runtime / "scripts/doctor.py", "--root", runtime, "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version", (result.stdout + result.stderr).casefold())
        self.assertNotIn("Traceback", result.stdout + result.stderr)
        self.assertFalse(marker.exists())


class ChangelogContract(unittest.TestCase):
    def sections(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        headers = list(re.finditer(r"^## ([0-9]+\.[0-9]+\.[0-9]+)([^\n]*)$", text, re.M))
        self.assertTrue(headers, "changelog must contain release entries")
        return [(match.group(1), match.group(2).strip(),
                 text[match.end():headers[index + 1].start() if index + 1 < len(headers) else len(text)].strip())
                for index, match in enumerate(headers)]

    def test_candidate_release_is_first_and_has_no_unapproved_release_date(self):
        sections = self.sections()
        version, suffix, _ = sections[0]
        self.assertEqual(version, EXPECTED_VERSION)
        decision_path = ROOT / "evals/agent-reach/release-decision.json"
        if not decision_path.is_file():
            self.assertEqual(suffix, "(Unreleased)", "a dated release needs a recorded owner decision")
        else:
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
            self.assertEqual(decision["version"], EXPECTED_VERSION)
            self.assertTrue(decision["approved_by"].strip())
            self.assertRegex(decision["candidate_sha"], r"^[0-9a-f]{40}$")
            self.assertEqual(decision["tag_name"], "v" + EXPECTED_VERSION)
            datetime.date.fromisoformat(decision["release_date"])
            self.assertEqual(suffix, "(%s)" % decision["release_date"])

    def test_release_headers_are_unique_descending_and_preserve_history(self):
        sections = self.sections()
        versions = [version for version, _, _ in sections]
        self.assertEqual(len(versions), len(set(versions)), "duplicate release version")
        ordering = [tuple(int(part) for part in version.split(".")) for version in versions]
        self.assertEqual(ordering, sorted(ordering, reverse=True))
        history = {version: (suffix, body) for version, suffix, body in sections}
        self.assertEqual(history["0.1.1"], (
            "(2026-10-02)",
            "- Fix SKILL.md frontmatter: quote description strings so `npx skills add` YAML discovery parses all 10 skills (unquoted `Triggers: ...` broke parsing). Add SkillsLayoutTest regression test (17/17 green).",
        ))
        self.assertEqual(history["0.1.0"], (
            "(2026-10-02)",
            "- Initial suite: 10 skills, lane.py + evidence_check.py + doctor.py, hook and CI templates, eval battery with published negatives, README, LIMITATIONS.md, adapters, install.",
        ))

    def test_candidate_notes_do_not_backfill_tags_or_claim_native_coverage(self):
        candidates = [body for version, _, body in self.sections() if version == EXPECTED_VERSION]
        self.assertEqual(len(candidates), 1, "expected one 0.3.0 candidate entry")
        body = candidates[0].casefold()
        self.assertIn("native discovery", body)
        self.assertIn("separate evidence", body)
        self.assertIn("not tagged", body)
        self.assertIn("chronology", body)
        self.assertNotRegex(body, r"released\s+(?:on\s+)?20[0-9]{2}-[0-9]{2}-[0-9]{2}")

    def test_version_guidance_identifies_shared_source_and_tag_boundary(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8").casefold()
        self.assertIn("scripts/version.py", readme)
        self.assertIn("0.3.0", readme)
        self.assertIn("unreleased", readme)
        self.assertIn("explicit tag authorization", readme)

    def test_unmarked_patch_history_is_preserved(self):
        notes = (ROOT / "PATCH-NOTES.md").read_text(encoding="utf-8")
        for original in ("374 tests plus 2 overview tests", "175 of 175 non-equivalent mutants killed",
                         "368 tests (ResourceWarning as error)", "255 unit/integration tests",
                         "112 of 112 non-equivalent hand-picked mutants killed"):
            self.assertIn(original, notes)


if __name__ == "__main__":
    unittest.main()
