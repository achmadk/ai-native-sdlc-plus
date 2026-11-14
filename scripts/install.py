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
import importlib.util
import json
import os
import re
import stat
import subprocess
import tempfile
import types


STATE = ".sdlc-install.json"
MANIFEST = "scripts/install-manifest.json"
CANONICAL_POLICY = "AGENTS.md"
MODES = ("0644", "0755")
HASH = re.compile(r"[0-9a-f]{64}\Z")
RESERVED = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z", re.I)

STATIC_PROFILE_PATHS = frozenset((
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
))

STARTER_AGENTS_MD = """\
# Project Agent Guidelines (AI-native SDLC)

<!-- User-owned canonical project policy. Edit freely; `sdlc` preserves this file across init, update, and uninstall. -->

This repository uses an evidence-based, risk-proportional SDLC gate (`sdlc`).

## 1. Classify Before Coding
Run the lane classifier on the paths you intend to touch:
```bash
sdlc lane --paths <files...>
```
- **Lite:** Docs, comments, low-risk test tweaks. Requires `## Intent`, test changes (unless non-executable), and `## Trace`.
- **Standard:** Normal feature/bugfix work. Requires an approved `Spec: path/to/spec.md`, test changes, `## Trace`, and `## Review notes`.
- **Critical:** Security, auth, migrations, workflows, hooks, or agent-control files. Requires `Intent link:`, `Spec:`, `## Threat note`, failing-first test verification, `## Trace`, 2-reviewer `## Review notes`, and `## Rollout plan`.

## 2. Verify Locally
- Validate specs and context briefs with `sdlc check spec <path>` and `sdlc check brief <path>`.
- Check installation health with `sdlc doctor --root .` and inspect check details with `sdlc explain <check-id> --root .`.
- Verify PR evidence locally before opening or updating a pull request with `sdlc check evidence ...`.
"""


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
    # Windows reports a different creation time for a path query than for a handle
    # query on the same file, so creation time only joins fingerprints where those agree.
    fields = [info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns]
    if os.name != "nt":
        fields.append(info.st_ctime_ns)
    fields.append(getattr(info, "st_file_attributes", 0))
    return tuple(fields)


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


def load_agent_profiles(source_root):
    rel = "scripts/agent_profiles.py"
    snap = snapshot(source_root, rel)
    if snap is None:
        return None
    full = checked_path(source_root, rel)
    spec = importlib.util.spec_from_file_location("_sdlc_trusted_agent_profiles", full)
    if spec is None or spec.loader is None:
        raise InstallError("cannot load trusted profile registry: %s" % rel)
    mod = importlib.util.module_from_spec(spec)
    host_install = sys.modules.get(__name__) or types.SimpleNamespace(**globals())
    mod.install_lib = host_install
    spec.loader.exec_module(mod)
    mod.install_lib = host_install
    return mod


def recognized_managed_paths(source_root, core_payload=None):
    if core_payload is None:
        core_payload, _ = read_payload(source_root)
    recognized = {item["relative"] for item in core_payload} | set(STATIC_PROFILE_PATHS)
    ap_mod = load_agent_profiles(source_root)
    if ap_mod is not None:
        recognized |= set(ap_mod.recognized_profile_paths(source_root))
    recognized.discard(CANONICAL_POLICY)
    recognized.discard(STATE)
    return recognized


def validate_recognized_ownership(owned, recognized):
    unrecognized = sorted(rel for rel in owned if rel not in recognized)
    if unrecognized:
        raise InstallError(
            "unrecognized or unmanageable paths in %s: %s; reconcile state explicitly before retrying"
            % (STATE, ", ".join(unrecognized))
        )


def inspect_canonical_policy(root):
    snap = snapshot(root, CANONICAL_POLICY)
    if snap is None:
        return {
            "path": CANONICAL_POLICY,
            "ownership": "user-owned",
            "status": "missing",
            "sha256": None,
            "snapshot": None,
            "text": None,
        }
    try:
        text = snap["data"].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InstallError(
            "canonical policy %s is not valid UTF-8 text: %s" % (CANONICAL_POLICY, exc)
        ) from exc
    return {
        "path": CANONICAL_POLICY,
        "ownership": "user-owned",
        "status": "present",
        "sha256": snap["record"]["sha256"],
        "snapshot": snap,
        "text": text,
    }


def _merge_payloads(core_payload, extra_payload):
    merged = []
    seen_casefold = {}
    for item in list(core_payload) + list(extra_payload):
        rel = item["relative"]
        safe_relative(rel)
        key = rel.casefold()
        if key in (STATE.casefold(), CANONICAL_POLICY.casefold()) or key.startswith(STATE.casefold() + "/"):
            raise InstallError("invalid managed destination: %r" % rel)
        if key in seen_casefold:
            existing = seen_casefold[key]
            if existing["relative"] == rel and existing["record"] == item["record"]:
                continue
            raise InstallError("conflicting or case-colliding managed destination: %r vs %r" % (existing["relative"], rel))
        if any(key.startswith(other + "/") or other.startswith(key + "/") for other in seen_casefold):
            raise InstallError("overlapping managed destinations: %r" % rel)
        copied = {"relative": rel, "data": item["data"], "record": dict(item["record"])}
        seen_casefold[key] = copied
        merged.append(copied)
    return merged


def plan_install(root, source_root, extra_payload=(), create_starter_policy=False, selected_agents=(), additive=True, policy_info=None):
    root, source_root = os.path.abspath(root), os.path.abspath(source_root)
    core_payload, identity = read_payload(source_root)
    recognized = recognized_managed_paths(source_root, core_payload=core_payload)
    old_state = snapshot(root, STATE)
    owned = read_ownership(old_state)
    validate_recognized_ownership(owned, recognized)

    if policy_info is None:
        policy_info = inspect_canonical_policy(root)
    starter_item = None
    if create_starter_policy:
        if policy_info["status"] == "missing":
            starter_bytes = STARTER_AGENTS_MD.encode("utf-8")
            starter_item = {
                "relative": CANONICAL_POLICY,
                "data": starter_bytes,
                "record": record(starter_bytes, effective_mode("0644")),
                "previous": None,
            }
            policy_action = "create-starter"
        else:
            policy_action = "preserve-existing"
    else:
        policy_action = "preserve-existing" if policy_info["status"] == "present" else "none"

    payload = _merge_payloads(core_payload, extra_payload)
    payload_rels = {item["relative"] for item in payload}

    conflicts = []
    for item in payload:
        relative = item["relative"]
        previous = snapshot(root, relative)
        item["previous"] = previous
        item["retained"] = previous is not None and previous["record"] == item["record"]
        if previous is not None and not item["retained"] and previous["record"] != owned.get(relative):
            conflicts.append(relative)

    preserved_records = {}
    preserved_snapshots = {}
    if additive:
        for rel, owned_rec in sorted(owned.items()):
            if rel in payload_rels:
                continue
            prev = snapshot(root, rel)
            if prev is None or prev["record"] != owned_rec:
                conflicts.append(rel)
            else:
                preserved_records[rel] = owned_rec
                preserved_snapshots[rel] = prev

    if conflicts:
        raise InstallError(
            "conflicts (unowned or locally modified); no payload writes:\n"
            + "\n".join("  %s" % path for path in conflicts)
            + "\nReconcile these files explicitly; the installer never forces replacement."
        )

    files_map = {item["relative"]: item["record"] for item in payload}
    files_map.update(preserved_records)
    state = {"version": 1, "source_manifest": identity, "files": files_map}
    state_data = (json.dumps(state, sort_keys=True, indent=2) + "\n").encode("utf-8")
    state_item = {
        "relative": STATE,
        "data": state_data,
        "record": record(state_data, "0644"),
        "previous": old_state,
    }
    pending = [item for item in payload if not item["retained"]]
    state_changed = old_state is None or old_state["data"] != state_data

    return {
        "root": root,
        "source_root": source_root,
        "identity": identity,
        "old_state": old_state,
        "owned": owned,
        "policy_info": policy_info,
        "policy_action": policy_action,
        "starter_item": starter_item,
        "payload": payload,
        "pending": pending,
        "preserved_records": preserved_records,
        "preserved_snapshots": preserved_snapshots,
        "state_item": state_item,
        "state_changed": state_changed,
        "selected_agents": list(selected_agents),
    }


def _execute_planned_install(plan):
    root = plan["root"]
    payload = plan["payload"]
    pending = plan["pending"]
    old_state = plan["old_state"]
    state_item = plan["state_item"]
    state_changed = plan["state_changed"]
    starter_item = plan["starter_item"]
    policy_info = plan["policy_info"]
    preserved_snapshots = plan["preserved_snapshots"]

    changed = []
    current = "preflight"
    state_temp = None
    try:
        if not pending and not state_changed and starter_item is None:
            unchanged(root, CANONICAL_POLICY, policy_info["snapshot"])
            verify_payload(root, payload)
            for rel, snap in preserved_snapshots.items():
                unchanged(root, rel, snap)
            unchanged(root, STATE, old_state)
            return root, payload, changed

        checked_path(root, STATE)
        os.makedirs(root, exist_ok=True)
        checked_path(root, STATE)
        with tempfile.TemporaryDirectory(prefix=".sdlc-stage-", dir=root) as staging:
            staged_items = (
                ([starter_item] if starter_item is not None else [])
                + pending
                + ([state_item] if state_changed else [])
            )
            for index, item in enumerate(staged_items):
                current = "staging %r" % item["relative"]
                staged = checked_path(staging, str(index))
                descriptor = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
                write_staged(descriptor, staged, item)
                item["staged"] = staged

            if starter_item is not None:
                current = "publishing %r" % CANONICAL_POLICY
                destination = checked_path(root, CANONICAL_POLICY)
                verify_staged(starter_item["staged"], starter_item)
                unchanged(root, STATE, old_state)
                unchanged(root, CANONICAL_POLICY, None)
                os.replace(starter_item["staged"], destination)
                changed.append(CANONICAL_POLICY)
            else:
                unchanged(root, CANONICAL_POLICY, policy_info["snapshot"])

            for item in pending:
                relative = item["relative"]
                current = "publishing %r" % relative
                destination = checked_path(root, relative)
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                verify_staged(item["staged"], item)
                unchanged(root, STATE, old_state)
                if starter_item is None:
                    unchanged(root, CANONICAL_POLICY, policy_info["snapshot"])
                unchanged(root, relative, item["previous"])
                os.replace(item["staged"], destination)
                changed.append(relative)

            current = "payload verification"
            verify_payload(root, payload)
            for rel, snap in preserved_snapshots.items():
                unchanged(root, rel, snap)
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
            for rel, snap in preserved_snapshots.items():
                unchanged(root, rel, snap)
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


def install(root, source_root):
    root, source_root = os.path.abspath(root), os.path.abspath(source_root)
    try:
        plan = plan_install(root, source_root, extra_payload=(), create_starter_policy=False, selected_agents=())
    except (OSError, ValueError, InstallError) as exc:
        raise InstallError("preflight: %s" % exc, ()) from exc
    return _execute_planned_install(plan)


def _format_plan_summary(plan, dry_run, changed=()):
    setup_mode = "profiles:" + ",".join(plan["selected_agents"]) if plan["selected_agents"] else "core-only"
    return {
        "root": plan["root"],
        "dry_run": bool(dry_run),
        "setup_mode": setup_mode,
        "selected_agents": list(plan["selected_agents"]),
        "source_manifest": plan["identity"],
        "policy": {
            "path": CANONICAL_POLICY,
            "ownership": "user-owned",
            "status": plan["policy_info"]["status"],
            "action": plan["policy_action"],
        },
        "planned_writes": [item["relative"] for item in plan["pending"]],
        "retained_files": [item["relative"] for item in plan["payload"] if item["retained"]],
        "preserved_owned_files": sorted(plan["preserved_records"]),
        "owned_destinations": sorted(
            list({item["relative"] for item in plan["payload"]} | set(plan["preserved_records"]))
        ),
        "changed": list(changed),
    }


def init_project(root, source_root, agents=(), dry_run=False):
    root, source_root = os.path.abspath(root), os.path.abspath(source_root)
    try:
        policy_info = inspect_canonical_policy(root)
        extra_payload = []
        selected = list(agents or ())
        if selected:
            ap_mod = load_agent_profiles(source_root)
            if ap_mod is None:
                raise InstallError("agent profile renderer unavailable in runtime: scripts/agent_profiles.py")
            selected = ap_mod.parse_agent_selectors(selected)
            policy_text = (
                policy_info["text"]
                if policy_info["text"] is not None
                else STARTER_AGENTS_MD
            )
            extra_payload = ap_mod.render_profiles(source_root, selected, policy_text)

        plan = plan_install(
            root,
            source_root,
            extra_payload=extra_payload,
            create_starter_policy=True,
            selected_agents=selected,
            additive=True,
            policy_info=policy_info,
        )
    except (OSError, ValueError, InstallError) as exc:
        raise InstallError("preflight: %s" % exc, ()) from exc

    if dry_run:
        return _format_plan_summary(plan, dry_run=True, changed=())

    _, _, changed = _execute_planned_install(plan)
    return _format_plan_summary(plan, dry_run=False, changed=changed)


def update_project(root, source_root, dry_run=False):
    root, source_root = os.path.abspath(root), os.path.abspath(source_root)
    try:
        old_state = snapshot(root, STATE)
        if old_state is None:
            raise InstallError("no %s found in %r; run 'sdlc init' before 'sdlc update'" % (STATE, root))
        core_payload, _ = read_payload(source_root)
        recognized = recognized_managed_paths(source_root, core_payload=core_payload)
        owned = read_ownership(old_state)
        validate_recognized_ownership(owned, recognized)
        policy_info = inspect_canonical_policy(root)

        ap_mod = load_agent_profiles(source_root)
        installed_profiles = []
        extra_payload = []
        if ap_mod is not None:
            installed_profiles = ap_mod.recover_installed_profiles(owned, source_root)
            if installed_profiles:
                policy_text = (
                    policy_info["text"]
                    if policy_info["text"] is not None
                    else STARTER_AGENTS_MD
                )
                extra_payload = ap_mod.render_profiles(source_root, installed_profiles, policy_text)

        plan = plan_install(
            root,
            source_root,
            extra_payload=extra_payload,
            create_starter_policy=False,
            selected_agents=installed_profiles,
            additive=True,
            policy_info=policy_info,
        )
    except (OSError, ValueError, InstallError) as exc:
        raise InstallError("preflight: %s" % exc, ()) from exc

    if dry_run:
        return _format_plan_summary(plan, dry_run=True, changed=())

    _, _, changed = _execute_planned_install(plan)
    return _format_plan_summary(plan, dry_run=False, changed=changed)


def _managed_parent_dirs(owned_rels):
    parents = set()
    for rel in owned_rels:
        parts = rel.split("/")[:-1]
        while parts:
            parents.add("/".join(parts))
            parts = parts[:-1]
    return sorted(parents, key=lambda p: (-p.count("/"), p))


def uninstall_project(root, source_root, dry_run=False):
    root, source_root = os.path.abspath(root), os.path.abspath(source_root)
    removed = []
    current = "preflight"
    try:
        old_state = snapshot(root, STATE)
        if old_state is None:
            raise InstallError("no %s found in %r; nothing owned to uninstall" % (STATE, root))
        core_payload, _ = read_payload(source_root)
        recognized = recognized_managed_paths(source_root, core_payload=core_payload)
        owned = read_ownership(old_state)
        validate_recognized_ownership(owned, recognized)
        policy_info = inspect_canonical_policy(root)
        policy_action = "retained-user-owned" if policy_info["status"] == "present" else "none"

        eligible = []
        already_missing = []
        conflicts = []
        for rel, owned_rec in sorted(owned.items()):
            snap = snapshot(root, rel)
            if snap is None:
                already_missing.append(rel)
            elif snap["record"] != owned_rec:
                conflicts.append(rel)
            else:
                eligible.append((rel, snap))

        if conflicts:
            raise InstallError(
                "conflicts (locally modified owned files); no files removed:\n"
                + "\n".join("  %s" % path for path in conflicts)
                + "\nReconcile or remove edited files explicitly; uninstall never deletes modified content."
            )

        if dry_run:
            return {
                "root": root,
                "dry_run": True,
                "policy": {
                    "path": CANONICAL_POLICY,
                    "ownership": "user-owned",
                    "status": policy_info["status"],
                    "action": policy_action,
                },
                "planned_removals": [rel for rel, _ in eligible],
                "already_missing": already_missing,
                "removed": [],
                "state_removed": False,
            }

        for rel, expected_snap in eligible:
            current = "removing %r" % rel
            target = checked_path(root, rel)
            unchanged(root, STATE, old_state)
            unchanged(root, rel, expected_snap)
            os.unlink(target)
            removed.append(rel)

        current = "removal verification"
        for rel in sorted(owned):
            if snapshot(root, rel) is not None:
                raise InstallError("uninstall verification failed: %r still present" % rel)

        # Prune only empty directories that were parents of managed owned files.
        for parent_rel in _managed_parent_dirs(owned):
            try:
                parent_path = checked_path(root, parent_rel)
                if os.path.isdir(parent_path):
                    os.rmdir(parent_path)
            except (OSError, InstallError):
                continue

        current = "removing %r" % STATE
        state_path = checked_path(root, STATE)
        unchanged(root, STATE, old_state)
        os.unlink(state_path)
        if snapshot(root, STATE) is not None:
            raise InstallError("uninstall verification failed: %s still present" % STATE)
        removed.append(STATE)

        return {
            "root": root,
            "dry_run": False,
            "policy": {
                "path": CANONICAL_POLICY,
                "ownership": "user-owned",
                "status": policy_info["status"],
                "action": policy_action,
            },
            "planned_removals": [rel for rel, _ in eligible],
            "already_missing": already_missing,
            "removed": removed,
            "state_removed": True,
        }
    except (OSError, ValueError, InstallError) as exc:
        raise InstallError("%s: %s" % (current, exc), removed) from exc


def status_project(root, source_root):
    root, source_root = os.path.abspath(root), os.path.abspath(source_root)
    core_payload, identity = read_payload(source_root)
    recognized = recognized_managed_paths(source_root, core_payload=core_payload)
    policy_info = inspect_canonical_policy(root)
    old_state = snapshot(root, STATE)

    if old_state is None:
        matching, modified, missing = [], [], []
        for item in core_payload:
            rel = item["relative"]
            actual = snapshot(root, rel)
            if actual is None:
                missing.append(rel)
            elif actual["record"] == item["record"]:
                matching.append(rel)
            else:
                modified.append(rel)
        return {
            "root": root,
            "installed": False,
            "state_version": None,
            "recorded_source_manifest": None,
            "invoked_source_manifest": identity,
            "installed_profiles": [],
            "policy": {
                "path": CANONICAL_POLICY,
                "ownership": "user-owned",
                "status": policy_info["status"],
                "sha256": policy_info["sha256"],
            },
            "files": {
                "matching": sorted(matching),
                "update_available": [],
                "modified": sorted(modified),
                "missing": sorted(missing),
            },
        }

    owned = read_ownership(old_state)
    validate_recognized_ownership(owned, recognized)
    raw_state = load_json(old_state["data"], STATE)

    ap_mod = load_agent_profiles(source_root)
    installed_profiles = []
    extra_desired = []
    if ap_mod is not None:
        installed_profiles = ap_mod.recover_installed_profiles(owned, source_root)
        if installed_profiles and policy_info["snapshot"] is not None:
            extra_desired = ap_mod.render_profiles(
                source_root,
                installed_profiles,
                policy_info["snapshot"]["data"].decode("utf-8"),
            )
        elif installed_profiles:
            extra_desired = ap_mod.render_profiles(source_root, installed_profiles, STARTER_AGENTS_MD)

    desired_items = _merge_payloads(core_payload, extra_desired)
    desired_map = {item["relative"]: item["record"] for item in desired_items}

    matching, update_available, modified, missing = [], [], [], []
    for rel, owned_rec in sorted(owned.items()):
        actual = snapshot(root, rel)
        if actual is None:
            missing.append(rel)
        elif actual["record"] != owned_rec:
            modified.append(rel)
        elif rel in desired_map and desired_map[rel] != owned_rec:
            update_available.append(rel)
        else:
            matching.append(rel)

    for rel, desired_rec in sorted(desired_map.items()):
        if rel in owned:
            continue
        actual = snapshot(root, rel)
        if actual is None:
            update_available.append(rel)
        elif actual["record"] == desired_rec:
            matching.append(rel)
        else:
            modified.append(rel)

    return {
        "root": root,
        "installed": True,
        "state_version": raw_state["version"],
        "recorded_source_manifest": raw_state["source_manifest"],
        "invoked_source_manifest": identity,
        "installed_profiles": installed_profiles,
        "policy": {
            "path": CANONICAL_POLICY,
            "ownership": "user-owned",
            "status": policy_info["status"],
            "sha256": policy_info["sha256"],
        },
        "files": {
            "matching": sorted(matching),
            "update_available": sorted(update_available),
            "modified": sorted(modified),
            "missing": sorted(missing),
        },
    }


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
