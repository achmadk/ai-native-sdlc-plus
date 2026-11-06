"""Install the explicit foundation payload without overwriting local work.

Ownership state is a recovery aid, not a security attestation. Publication is
atomic per file, not across the payload. No destination Python code is executed.
Python >= 3.8; standard library only.
"""

import sys

if sys.version_info < (3, 8):
    sys.exit("installer requires Python >= 3.8")
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile


STATE = ".sdlc-install.json"
MANIFEST = "scripts/install-manifest.json"
MODES = ("0644", "0755")
HASH = re.compile(r"[0-9a-f]{64}\Z")
RESERVED = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z", re.I)


class InstallError(Exception):
    def __init__(self, message, changed=()):
        super().__init__(message)
        self.changed = tuple(changed)


def safe_relative(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise InstallError("invalid manifest/state path %r" % value)
    parts = value.split("/")
    if (any(c in value for c in '\\:*?"<>|') or any(part in ("", ".", "..") for part in parts)
            or any(part.casefold() == ".git" or part.endswith((" ", ".")) or RESERVED.fullmatch(part)
                   for part in parts)):
        raise InstallError("unsafe manifest/state path %r" % value)
    return parts


def linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0)
                                             & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def checked_path(root, relative):
    """Refuse links/reparse points rather than relying on a lexical prefix check."""
    parts = safe_relative(relative)
    path = root
    for index, component in enumerate([None] + parts):
        if component is not None:
            path = os.path.join(path, component)
        try:
            info = os.lstat(path)
        except FileNotFoundError:
            continue
        if linked(info):
            raise InstallError("symlink/reparse point is not an install destination or source: %r" % path)
        if index < len(parts) and not stat.S_ISDIR(info.st_mode):
            raise InstallError("parent is not a directory: %r" % path)
    if os.path.commonpath((os.path.realpath(root), os.path.realpath(path))) != os.path.realpath(root):
        raise InstallError("path escapes selected root: %r" % relative)
    return path


def effective_mode(mode):
    # Windows chmod exposes the read-only bit, not POSIX execute permissions.
    return "0644" if os.name == "nt" and int(mode, 8) & stat.S_IWUSR else mode


def record(data, mode):
    return {"sha256": hashlib.sha256(data).hexdigest(), "mode": mode,
            "mode_sha256": hashlib.sha256(mode.encode("ascii")).hexdigest()}


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, getattr(info, "st_file_attributes", 0))


def snapshot(root, relative):
    path = checked_path(root, relative)
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(before.st_mode) or linked(before):
        raise InstallError("expected a regular file: %r" % path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        if stamp(os.fstat(handle.fileno())) != stamp(before):
            raise InstallError("file changed while reading: %r" % path)
        data = handle.read()
        if stamp(os.fstat(handle.fileno())) != stamp(before):
            raise InstallError("file changed while reading: %r" % path)
    mode = "%04o" % stat.S_IMODE(before.st_mode)
    if os.name == "nt":
        mode = "0644" if before.st_mode & stat.S_IWUSR else "0444"
    return {"data": data, "record": record(data, mode), "stamp": stamp(before)}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_json(data, label):
    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InstallError("invalid %s: %s; reconcile it explicitly before retrying" % (label, exc))
    if not isinstance(result, dict) or type(result.get("version")) is not int or result["version"] != 1:
        raise InstallError("invalid or unsupported %s version; expected version 1" % label)
    return result


def read_payload(source_root):
    manifest = snapshot(source_root, MANIFEST)
    if manifest is None:
        raise InstallError("required source missing: %s" % MANIFEST)
    parsed = load_json(manifest["data"], MANIFEST)
    entries = parsed.get("files")
    if set(parsed) != {"version", "files"} or not isinstance(entries, list) or not entries:
        raise InstallError("invalid %s: expected a nonempty explicit files list" % MANIFEST)
    payload, destinations = [], set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"source", "destination", "mode"}:
            raise InstallError("invalid %s file entry" % MANIFEST)
        safe_relative(entry["source"])
        safe_relative(entry["destination"])
        destination = entry["destination"].casefold()
        if (destination == STATE or destination.startswith(STATE + "/")
                or destination in destinations or entry["mode"] not in MODES):
            raise InstallError("invalid/duplicate manifest destination or mode: %r" % entry["destination"])
        if any(destination.startswith(other + "/") or other.startswith(destination + "/") for other in destinations):
            raise InstallError("overlapping manifest destinations: %r" % entry["destination"])
        destinations.add(destination)
        incoming = snapshot(source_root, entry["source"])
        if incoming is None:
            raise InstallError("required source missing: %s" % entry["source"])
        payload.append({"relative": entry["destination"], "data": incoming["data"],
                        "record": record(incoming["data"], effective_mode(entry["mode"]))})
    return payload, "sha256:" + hashlib.sha256(manifest["data"]).hexdigest()


def read_ownership(previous):
    if previous is None:
        return {}
    state = load_json(previous["data"], STATE)
    files = state.get("files")
    identity = state.get("source_manifest")
    if (set(state) != {"version", "source_manifest", "files"} or not isinstance(files, dict)
            or not isinstance(identity, str) or not identity.startswith("sha256:") or not HASH.fullmatch(identity[7:])):
        raise InstallError("invalid %s ownership record; reconcile it explicitly before retrying" % STATE)
    seen = set()
    for relative, item in files.items():
        safe_relative(relative)
        if (relative.casefold() in seen or relative.casefold() == STATE or relative.casefold().startswith(STATE + "/")
                or not isinstance(item, dict)
                or set(item) != {"sha256", "mode", "mode_sha256"} or item.get("mode") not in MODES
                or not isinstance(item.get("sha256"), str) or not HASH.fullmatch(item["sha256"])
                or item.get("mode_sha256") != hashlib.sha256(item["mode"].encode("ascii")).hexdigest()):
            raise InstallError("invalid %s ownership entry for %r" % (STATE, relative))
        seen.add(relative.casefold())
    return files


def unchanged(root, relative, previous):
    if snapshot(root, relative) != previous:
        raise InstallError("destination changed after preflight; not replaced: %r" % relative)


def verify_payload(root, payload):
    # This source-side verifier reads bytes only. Never import or run a target tool.
    for item in payload:
        actual = snapshot(root, item["relative"])
        if actual is None or actual["record"] != item["record"]:
            raise InstallError("payload verification failed: %r" % item["relative"])


def verify_staged(path, item):
    actual = snapshot(os.path.dirname(path), os.path.basename(path))
    if actual is None or actual["record"] != item["record"]:
        raise InstallError("staged file verification failed: %r" % item["relative"])


def write_staged(descriptor, path, item):
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(item["data"])
        handle.flush()
        if hasattr(os, "fchmod"):
            os.fchmod(handle.fileno(), int(item["record"]["mode"], 8))
        else:
            os.chmod(checked_path(os.path.dirname(path), os.path.basename(path)), int(item["record"]["mode"], 8))
        os.fsync(handle.fileno())
    verify_staged(path, item)


def install(root, source_root):
    root, source_root = os.path.abspath(root), os.path.abspath(source_root)
    changed = []
    current = "preflight"
    state_temp = None
    try:
        payload, identity = read_payload(source_root)
        old_state = snapshot(root, STATE)
        owned = read_ownership(old_state)
        conflicts = []
        for item in payload:
            relative = item["relative"]
            previous = snapshot(root, relative)
            item["previous"] = previous
            item["retained"] = previous is not None and previous["record"] == item["record"]
            if previous is not None and not item["retained"] and previous["record"] != owned.get(relative):
                conflicts.append(relative)
        if conflicts:
            raise InstallError("conflicts (unowned or locally modified); no payload writes:\n" +
                               "\n".join("  %s" % path for path in conflicts) +
                               "\nReconcile these files explicitly; the installer never forces replacement.")
        state = {"version": 1, "source_manifest": identity,
                 "files": {item["relative"]: item["record"] for item in payload}}
        state_data = (json.dumps(state, sort_keys=True, indent=2) + "\n").encode("utf-8")
        state_item = {"relative": STATE, "data": state_data, "record": record(state_data, "0644"),
                      "previous": old_state}
        pending = [item for item in payload if not item["retained"]]
        state_changed = old_state is None or old_state["data"] != state_data
        if not pending and not state_changed:
            verify_payload(root, payload)
            unchanged(root, STATE, old_state)
            return root, payload, changed

        checked_path(root, STATE)
        os.makedirs(root, exist_ok=True)
        checked_path(root, STATE)
        with tempfile.TemporaryDirectory(prefix=".sdlc-stage-", dir=root) as staging:
            staged_items = pending + ([state_item] if state_changed else [])
            for index, item in enumerate(staged_items):
                current = "staging %r" % item["relative"]
                staged = checked_path(staging, str(index))
                descriptor = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
                write_staged(descriptor, staged, item)
                item["staged"] = staged

            for item in pending:
                relative = item["relative"]
                current = "publishing %r" % relative
                destination = checked_path(root, relative)
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                verify_staged(item["staged"], item)
                unchanged(root, STATE, old_state)
                unchanged(root, relative, item["previous"])
                os.replace(item["staged"], destination)
                changed.append(relative)

            current = "payload verification"
            verify_payload(root, payload)
            unchanged(root, STATE, old_state)
            if state_changed:
                verify_staged(state_item["staged"], state_item)
            current = "staging cleanup"

        # Cleanup is fallible too. Complete it before the final ownership record.
        if state_changed:
            current = "publishing %r" % STATE
            checked_path(root, STATE)
            descriptor, state_temp = tempfile.mkstemp(prefix=".sdlc-state-", dir=root)
            write_staged(descriptor, state_temp, state_item)
            verify_payload(root, payload)
            destination = checked_path(root, STATE)
            verify_staged(state_temp, state_item)
            unchanged(root, STATE, old_state)
            os.replace(state_temp, destination)
            state_temp = None
            changed.append(STATE)
        return root, payload, changed
    except (OSError, ValueError, InstallError) as exc:
        raise InstallError("%s: %s" % (current, exc), changed) from exc
    finally:
        if state_temp is not None:
            try:
                os.unlink(checked_path(root, os.path.basename(state_temp)))
            except (OSError, InstallError) as exc:
                print("temporary state cleanup failed for %r: %s" % (state_temp, exc), file=sys.stderr)


def report_controls(root):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    try:
        result = subprocess.run(["git", "-C", root, "config", "--get", "core.hooksPath"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=5)
        hooks_path = result.stdout.decode("utf-8", "replace").strip() if result.returncode == 0 else ""
        if hooks_path:
            active = os.path.realpath(os.path.join(root, hooks_path)) == os.path.realpath(os.path.join(root, "hooks"))
            print("hook: pre-existing core.hooksPath=%r unchanged%s" %
                  (hooks_path, "; installed hook is advisory" if active else "; existing hook manager preserved"))
        else:
            print("hook: not activated by installer; existing Git hooks unchanged (advisory only)")
    except (OSError, subprocess.TimeoutExpired):
        print("hook: pre-existing activation unverified; no Git configuration or hooks changed")
    print("hosted merge enforcement: unverified; installation does not activate repository protections")
    print("Next: inspect installation with Python >= 3.8: scripts/doctor.py --root %r" % root)
    print("Hook activation, agent registration, and hosted protection require separate operator authorization.")


def main(argv=None, source_root=None):
    parser = argparse.ArgumentParser(description="Install the foundation; conflicting local files are never overwritten")
    parser.add_argument("root", nargs="?", default=".", help="destination project directory (default: current directory)")
    args = parser.parse_args(argv)
    source_root = source_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        root, payload, changed = install(args.root, source_root)
    except InstallError as exc:
        print("installation failed: %s" % exc, file=sys.stderr)
        if exc.changed:
            print("partial installation; changed paths (no completed state published for this attempt):", file=sys.stderr)
            for path in exc.changed:
                print("  %s" % path, file=sys.stderr)
            print("No rollback attempted. Reconcile local edits before retrying; identical files are retained.", file=sys.stderr)
        else:
            print("No payload files changed.", file=sys.stderr)
        return 1
    for item in payload:
        print("%s: %s" % ("retained" if item["retained"] else "installed", item["relative"]))
    print("installation complete: %d payload files verified; %s %s" %
          (len(payload), STATE, "published" if STATE in changed else "retained"))
    report_controls(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
