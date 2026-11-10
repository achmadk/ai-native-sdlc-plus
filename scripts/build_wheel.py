"""Build a local PEP 427 wheel from the explicit runtime allowlist.

Uses the Python standard library only (`zipfile`, `hashlib`, `base64`, `csv`).
Never packages `.git/`, `__pycache__/`, `openspec/`, `tests/`, or untracked files.
Never uploads, tags, or publishes a release.
Python >= 3.8; standard library only.
"""

import sys

if sys.version_info < (3, 8):
    sys.exit("build_wheel requires Python >= 3.8")
sys.dont_write_bytecode = True

import argparse
import base64
import csv
import hashlib
import importlib.util
import io
import os
import tempfile
import zipfile


DIST_NAME = "ai-native-sdlc-plus"
NORM_NAME = "ai_native_sdlc_plus"
VERSION = "0.0.0.dev0"
TAG = "py3-none-any"
RUNTIME_PKG = "_sdlc_runtime"
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)

PACKAGE_INIT_PY = '''\
"""Private namespaced runtime payload for the local sdlc wheel."""

import sys

if sys.version_info < (3, 8):
    sys.exit("sdlc requires Python >= 3.8")
sys.dont_write_bytecode = True
'''

PACKAGE_CLI_PY = '''\
"""Thin console_scripts launcher delegating to packaged _sdlc_runtime/scripts/sdlc.py."""

import sys

if sys.version_info < (3, 8):
    sys.exit("sdlc requires Python >= 3.8")
sys.dont_write_bytecode = True

import importlib.util
import os


def _load_canonical_sdlc():
    pkg_root = os.path.dirname(os.path.abspath(__file__))
    sdlc_path = os.path.join(pkg_root, "scripts", "sdlc.py")
    if not os.path.isfile(sdlc_path):
        sys.stderr.write("sdlc runtime integrity error: missing %s\\n" % sdlc_path)
        raise SystemExit(3)
    spec = importlib.util.spec_from_file_location("_sdlc_packaged_dispatcher", sdlc_path)
    if spec is None or spec.loader is None:
        sys.stderr.write("sdlc runtime integrity error: cannot load %s\\n" % sdlc_path)
        raise SystemExit(3)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_sdlc_packaged_dispatcher"] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    mod = _load_canonical_sdlc()
    return mod.main(argv=argv)


if __name__ == "__main__":
    sys.exit(main())
'''


def _load_install_module():
    existing = (
        sys.modules.get("_sdlc_wheel_install_helper")
        or sys.modules.get("scripts.install")
        or sys.modules.get("_sdlc_delegated_install")
        or sys.modules.get("install")
    )
    if existing is not None and hasattr(existing, "read_payload"):
        return existing
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "install.py")
    spec = importlib.util.spec_from_file_location("_sdlc_wheel_install_helper", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_sdlc_wheel_install_helper"] = mod
    spec.loader.exec_module(mod)
    return mod


def _urlsafe_sha256(data):
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _metadata_bytes():
    lines = [
        "Metadata-Version: 2.1",
        "Name: %s" % DIST_NAME,
        "Version: %s" % VERSION,
        "Summary: Risk-proportional AI-native SDLC gate, skills, and project-local agent bootstrap (local wheel)",
        "License: MIT",
        "Requires-Python: >=3.8",
        "",
        "Local standard-library wheel for the AI-native SDLC front door (`sdlc`).",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _wheel_bytes():
    lines = [
        "Wheel-Version: 1.0",
        "Generator: sdlc-stdlib-wheel-builder (1.0)",
        "Root-Is-Purelib: true",
        "Tag: %s" % TAG,
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _entry_points_bytes():
    lines = [
        "[console_scripts]",
        "sdlc = %s.cli:main" % RUNTIME_PKG,
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def build_wheel(source_root, out_dir):
    install_mod = _load_install_module()
    source_root = os.path.abspath(source_root)
    out_dir = os.path.abspath(out_dir)

    payload, _ = install_mod.read_payload(source_root)
    license_snap = install_mod.snapshot(source_root, "LICENSE")
    if license_snap is None:
        raise install_mod.InstallError("required source missing: LICENSE")

    # Verify required runtime scripts are in the allowlist payload.
    rels = {item["relative"] for item in payload}
    for req in (
        "scripts/sdlc.py",
        "scripts/agent_profiles.py",
        "scripts/install.py",
        "scripts/install-manifest.json",
        "scripts/lane.py",
        "scripts/lite.py",
        "scripts/evidence_check.py",
        "scripts/doctor.py",
        "scripts/scanner-profiles.json",
    ):
        if req not in rels:
            raise install_mod.InstallError("required runtime file missing from manifest: %s" % req)

    dist_info = "%s-%s.dist-info" % (NORM_NAME, VERSION)
    wheel_filename = "%s-%s-%s.whl" % (NORM_NAME, VERSION, TAG)

    members = []
    members.append(("%s/__init__.py" % RUNTIME_PKG, PACKAGE_INIT_PY.encode("utf-8"), 0o644))
    members.append(("%s/cli.py" % RUNTIME_PKG, PACKAGE_CLI_PY.encode("utf-8"), 0o644))
    for item in payload:
        arcname = "%s/%s" % (RUNTIME_PKG, item["relative"])
        mode = int(item["record"]["mode"], 8)
        members.append((arcname, item["data"], mode))

    members.append(("%s/METADATA" % dist_info, _metadata_bytes(), 0o644))
    members.append(("%s/WHEEL" % dist_info, _wheel_bytes(), 0o644))
    members.append(("%s/entry_points.txt" % dist_info, _entry_points_bytes(), 0o644))
    members.append(("%s/LICENSE" % dist_info, license_snap["data"], 0o644))

    record_arcname = "%s/RECORD" % dist_info
    record_buf = io.StringIO()
    writer = csv.writer(record_buf, lineterminator="\n")
    for arcname, data, _ in members:
        writer.writerow([arcname, _urlsafe_sha256(data), str(len(data))])
    writer.writerow([record_arcname, "", ""])
    members.append((record_arcname, record_buf.getvalue().encode("utf-8"), 0o644))

    os.makedirs(out_dir, exist_ok=True)
    final_path = os.path.join(out_dir, wheel_filename)
    fd, temp_path = tempfile.mkstemp(prefix=".sdlc-wheel-", suffix=".whl", dir=out_dir)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for arcname, data, mode in members:
                zi = zipfile.ZipInfo(filename=arcname, date_time=FIXED_ZIP_TIME)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = (mode & 0xFFFF) << 16
                zf.writestr(zi, data)
        os.replace(temp_path, final_path)
        temp_path = None
    finally:
        if temp_path is not None and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    return final_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="build_wheel.py",
        description="Build a local stdlib wheel for sdlc to an explicit output directory.",
    )
    parser.add_argument(
        "--source-root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="toolkit source repository root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="explicit output directory for the built .whl archive",
    )
    args = parser.parse_args(argv)
    install_mod = _load_install_module()
    try:
        wheel_path = build_wheel(args.source_root, args.out_dir)
    except (OSError, ValueError, install_mod.InstallError) as exc:
        sys.stderr.write("build_wheel failed: %s\n" % exc)
        return 1
    print(wheel_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
