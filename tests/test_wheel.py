"""Contract tests for the standard-library local wheel builder and installed console entry point."""

import sys

sys.dont_write_bytecode = True

import base64
import csv
import email
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD_WHEEL = ROOT / "scripts" / "build_wheel.py"
MANIFEST = ROOT / "scripts" / "install-manifest.json"


def _urlsafe_sha256(data):
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class WheelPackagingContract(unittest.TestCase):
    """Tasks 5.1 & 5.2: allowlisted stdlib wheel contents, metadata, RECORD hashes, and missing-resource failures."""

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="sdlc-wheel-test-"))

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_wheel_builder_cli_and_allowlisted_archive_contract(self):
        self.assertTrue(
            BUILD_WHEEL.is_file(),
            "expected standard-library wheel builder at scripts/build_wheel.py",
        )

        # Build from a copy of the source tree polluted with untracked secrets, .git, __pycache__, openspec, tests.
        dirty_src = self.temp / "dirty-source"
        dirty_src.mkdir()
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            rel = entry["source"]
            dst = dirty_src / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
        shutil.copy2(ROOT / "LICENSE", dirty_src / "LICENSE")
        if BUILD_WHEEL.is_file():
            shutil.copy2(BUILD_WHEEL, dirty_src / "scripts" / "build_wheel.py")

        # Inject forbidden checkout/cache/secret files that must never enter the wheel.
        for forbidden_rel, body in (
            (".git/config", "[core]\nrepositoryformatversion = 0\n"),
            ("__pycache__/poison.cpython-315.pyc", "bytecode"),
            ("scripts/__pycache__/lane.cpython-315.pyc", "bytecode"),
            ("openspec/changes/one-front-door/proposal.md", "# planning"),
            ("tests/test_secret.py", "raise RuntimeError('test file packaged')"),
            (".env", "AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE"),
            ("credentials.pem", "-----BEGIN PRIVATE KEY-----"),
            (".sdlc-install.json", "{}"),
        ):
            p = dirty_src / forbidden_rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")

        out_dir = self.temp / "dist-out"
        res = subprocess.run(
            [
                sys.executable,
                "-B",
                str(BUILD_WHEEL),
                "--source-root",
                str(dirty_src),
                "--out-dir",
                str(out_dir),
            ],
            cwd=str(self.temp),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))

        wheels = list(out_dir.glob("*.whl"))
        self.assertEqual(len(wheels), 1, f"expected 1 wheel in {out_dir}, got {wheels}")
        wheel_path = wheels[0]
        self.assertTrue(wheel_path.name.endswith("-py3-none-any.whl"), wheel_path.name)

        with zipfile.ZipFile(wheel_path, "r") as zf:
            names = set(zf.namelist())
            # No forbidden paths may appear anywhere in the wheel.
            for name in names:
                self.assertFalse(name.startswith(".git/"), name)
                self.assertNotIn("__pycache__", name)
                self.assertFalse(name.endswith(".pyc"), name)
                self.assertFalse(name.startswith("openspec/"), name)
                self.assertFalse(name.startswith("tests/"), name)
                self.assertNotIn(".env", name)
                self.assertNotIn("credentials.pem", name)

            dist_infos = {n.split("/")[0] for n in names if ".dist-info/" in n}
            self.assertEqual(len(dist_infos), 1)
            dist_info = next(iter(dist_infos))

            for required_meta in ("METADATA", "WHEEL", "entry_points.txt", "LICENSE", "RECORD"):
                self.assertIn(f"{dist_info}/{required_meta}", names)

            # Every manifest file must be packaged inside _sdlc_runtime/<source>.
            expected_runtime_files = {f"_sdlc_runtime/{entry['source']}" for entry in manifest["files"]}
            expected_runtime_files.update({"_sdlc_runtime/__init__.py", "_sdlc_runtime/cli.py"})
            expected_dist_info_files = {
                f"{dist_info}/METADATA",
                f"{dist_info}/WHEEL",
                f"{dist_info}/entry_points.txt",
                f"{dist_info}/LICENSE",
                f"{dist_info}/RECORD",
            }
            self.assertEqual(names, expected_runtime_files | expected_dist_info_files)

            # Validate METADATA: Python floor >=3.8 and zero Requires-Dist runtime dependencies.
            meta_bytes = zf.read(f"{dist_info}/METADATA")
            msg = email.message_from_bytes(meta_bytes)
            self.assertEqual(msg.get("Requires-Python"), ">=3.8")
            self.assertEqual(msg.get_all("Requires-Dist", []), [])

            # Validate WHEEL tags.
            wheel_meta = email.message_from_bytes(zf.read(f"{dist_info}/WHEEL"))
            self.assertEqual(wheel_meta.get("Wheel-Version"), "1.0")
            self.assertEqual(wheel_meta.get("Root-Is-Purelib"), "true")
            self.assertEqual(wheel_meta.get("Tag"), "py3-none-any")

            # Validate console_scripts entry point.
            ep_text = zf.read(f"{dist_info}/entry_points.txt").decode("utf-8")
            self.assertIn("[console_scripts]", ep_text)
            self.assertIn("sdlc = _sdlc_runtime.cli:main", ep_text)

            # Validate LICENSE matches root LICENSE.
            self.assertEqual(zf.read(f"{dist_info}/LICENSE"), (ROOT / "LICENSE").read_bytes())

            # Validate RECORD digests and sizes for every archive member.
            record_text = zf.read(f"{dist_info}/RECORD").decode("utf-8")
            rows = list(csv.reader(io.StringIO(record_text)))
            recorded = {}
            for row in rows:
                self.assertEqual(len(row), 3, row)
                recorded[row[0]] = (row[1], row[2])
            self.assertEqual(set(recorded), names)
            for member in sorted(names):
                if member == f"{dist_info}/RECORD":
                    self.assertEqual(recorded[member], ("", ""))
                else:
                    raw = zf.read(member)
                    self.assertEqual(recorded[member], (_urlsafe_sha256(raw), str(len(raw))), member)

    def test_missing_required_resource_or_license_fails_wheel_build(self):
        self.assertTrue(
            BUILD_WHEEL.is_file(),
            "expected standard-library wheel builder at scripts/build_wheel.py",
        )
        incomplete_src = self.temp / "incomplete-source"
        incomplete_src.mkdir()
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            rel = entry["source"]
            if rel == "scripts/scanner-profiles.json":
                continue  # omit a required resource
            dst = incomplete_src / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
        shutil.copy2(ROOT / "LICENSE", incomplete_src / "LICENSE")

        out_dir = self.temp / "failed-dist"
        res = subprocess.run(
            [
                sys.executable,
                "-B",
                str(BUILD_WHEEL),
                "--source-root",
                str(incomplete_src),
                "--out-dir",
                str(out_dir),
            ],
            cwd=str(self.temp),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("scanner-profiles.json", res.stderr.decode("utf-8", "replace"))
        self.assertNotIn("Traceback", res.stderr.decode("utf-8", "replace"))
        self.assertEqual(list(out_dir.glob("*.whl")) if out_dir.exists() else [], [])

        # Missing LICENSE also fails cleanly without a traceback.
        shutil.copy2(ROOT / "scripts/scanner-profiles.json", incomplete_src / "scripts/scanner-profiles.json")
        (incomplete_src / "LICENSE").unlink()
        res_no_lic = subprocess.run(
            [
                sys.executable,
                "-B",
                str(BUILD_WHEEL),
                "--source-root",
                str(incomplete_src),
                "--out-dir",
                str(out_dir),
            ],
            cwd=str(self.temp),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(res_no_lic.returncode, 1)
        self.assertIn("LICENSE", res_no_lic.stderr.decode("utf-8", "replace"))
        self.assertNotIn("Traceback", res_no_lic.stderr.decode("utf-8", "replace"))


class InstalledWheelExecutionContract(unittest.TestCase):
    """Tasks 5.2 & 5.3: isolated venv wheel install, source-vs-wheel parity, and execution without Node or source checkout."""

    def setUp(self):
        self.temp = Path(os.path.realpath(tempfile.mkdtemp(prefix="sdlc-wheel-venv-")))

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_installed_wheel_console_script_works_without_source_checkout_or_node(self):
        # 1. Copy allowlisted source to a disposable directory, build wheel, then delete source copy.
        src_copy = self.temp / "disposable-source"
        src_copy.mkdir()
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            rel = entry["source"]
            dst = src_copy / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
        shutil.copy2(ROOT / "LICENSE", src_copy / "LICENSE")
        shutil.copy2(BUILD_WHEEL, src_copy / "scripts" / "build_wheel.py")

        wheel_dir = self.temp / "wheelhouse"
        res_build = subprocess.run(
            [
                sys.executable,
                "-B",
                str(src_copy / "scripts" / "build_wheel.py"),
                "--source-root",
                str(src_copy),
                "--out-dir",
                str(wheel_dir),
            ],
            cwd=str(self.temp),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(res_build.returncode, 0, res_build.stderr.decode("utf-8", "replace"))
        wheel_path = Path(res_build.stdout.decode("utf-8").strip())
        self.assertTrue(wheel_path.is_file())

        # Remove disposable source checkout completely so installed wheel cannot fall back to it.
        shutil.rmtree(src_copy)
        self.assertFalse(src_copy.exists())

        # 2. Create isolated venv and install local wheel offline (--no-index --no-deps).
        venv_dir = self.temp / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
        venv_python = bin_dir / ("python.exe" if os.name == "nt" else "python")
        sdlc_bin = bin_dir / ("sdlc.exe" if os.name == "nt" else "sdlc")

        res_pip = subprocess.run(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                str(wheel_path),
            ],
            cwd=str(self.temp),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(res_pip.returncode, 0, res_pip.stderr.decode("utf-8", "replace"))
        self.assertTrue(sdlc_bin.is_file(), f"console_scripts entry point not created at {sdlc_bin}")

        # 3. Build environment without Node/npx on PATH and without PYTHONPATH.
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        git_bin = shutil.which("git")
        clean_path_parts = [str(bin_dir)]
        if git_bin:
            clean_path_parts.append(os.path.dirname(git_bin))
        if os.name == "nt":
            sys_root = os.environ.get("SystemRoot", r"C:\Windows")
            clean_path_parts.append(os.path.join(sys_root, "System32"))
        env["PATH"] = os.pathsep.join(clean_path_parts)

        outside_cwd = self.temp / "unrelated-cwd"
        outside_cwd.mkdir()

        def run_wheel(args):
            try:
                return subprocess.run(
                    [str(sdlc_bin)] + list(args),
                    cwd=str(outside_cwd),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except OSError as exc:
                if getattr(exc, "winerror", None) != 4551:
                    raise
                # Windows Application Control blocks unsigned pip distlib launcher .exe files in %TEMP%;
                # load the installed console_scripts entry point via the signed venv Python interpreter.
                ep_runner = (
                    "import sys; "
                    "from importlib.metadata import entry_points; "
                    "eps = entry_points(); "
                    "group = eps.select(group='console_scripts') if hasattr(eps, 'select') else eps.get('console_scripts', ()); "
                    "ep = [e for e in group if e.name == 'sdlc'][0]; "
                    "sys.argv = ['sdlc'] + sys.argv[1:]; "
                    "sys.exit(ep.load()())"
                )
                return subprocess.run(
                    [str(venv_python), "-B", "-c", ep_runner] + list(args),
                    cwd=str(outside_cwd),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

        def run_source(args):
            return subprocess.run(
                [sys.executable, "-B", str(ROOT / "scripts" / "sdlc.py")] + list(args),
                cwd=str(outside_cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        # Verify source-vs-wheel parity on --help, lane, check evidence, and explain.
        for parity_args in (
            ["--help"],
            ["lane", "--paths", "scripts/lane.py", "README.md"],
            ["check", "evidence", "--lane", "Lite", "--present", "intent_block", "test_changes", "trace_block"],
            ["explain", "codeowners", "--root", ".", "--json"],
        ):
            w_res = run_wheel(parity_args)
            s_res = run_source(parity_args)
            self.assertEqual(w_res.returncode, 0, w_res.stderr.decode("utf-8", "replace"))
            self.assertEqual(w_res.returncode, s_res.returncode, parity_args)
            self.assertEqual(w_res.stdout, s_res.stdout, parity_args)

        # Exercise full lifecycle (init --agents -> status -> doctor -> update -> uninstall) from unrelated CWD.
        target = self.temp / "target-project"
        target.mkdir()
        res_init = run_wheel(["init", "--root", str(target), "--agents", "claude,cursor,gemini", "--json"])
        self.assertEqual(res_init.returncode, 0, res_init.stderr.decode("utf-8", "replace"))
        init_json = json.loads(res_init.stdout.decode("utf-8"))
        self.assertEqual(init_json["selected_agents"], ["claude", "cursor", "gemini"])
        self.assertTrue((target / "AGENTS.md").is_file())
        self.assertTrue((target / "CLAUDE.md").is_file())
        self.assertTrue((target / "GEMINI.md").is_file())

        res_status = run_wheel(["status", "--root", str(target), "--json"])
        self.assertEqual(res_status.returncode, 0, res_status.stderr.decode("utf-8", "replace"))
        st_json = json.loads(res_status.stdout.decode("utf-8"))
        self.assertEqual(st_json["installed_profiles"], ["claude", "cursor", "gemini"])
        self.assertEqual(st_json["files"]["missing"], [])

        res_doc = run_wheel(["doctor", "--root", str(target), "--json"])
        self.assertEqual(res_doc.returncode, 0, res_doc.stderr.decode("utf-8", "replace"))
        doc_json = json.loads(res_doc.stdout.decode("utf-8"))
        self.assertEqual(doc_json["summary"]["FAIL"], 0)

        res_upd = run_wheel(["update", "--root", str(target), "--json"])
        self.assertEqual(res_upd.returncode, 0, res_upd.stderr.decode("utf-8", "replace"))

        res_uninst = run_wheel(["uninstall", "--root", str(target), "--json"])
        self.assertEqual(res_uninst.returncode, 0, res_uninst.stderr.decode("utf-8", "replace"))
        self.assertTrue((target / "AGENTS.md").is_file())
        self.assertFalse((target / ".sdlc-install.json").exists())


if __name__ == "__main__":
    unittest.main()
