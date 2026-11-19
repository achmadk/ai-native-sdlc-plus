"""Validate and replay independent native-agent support evidence offline."""

import sys

if sys.version_info < (3, 8):
    sys.exit("agent_reach requires Python >= 3.8")
sys.dont_write_bytecode = True

import argparse
import datetime
from decimal import Decimal
import hashlib
import importlib.util
import json
import math
import os
import re
import stat
import subprocess
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_ROOT = os.path.dirname(HERE)
MAX_JSON_BYTES = 4 * 1024 * 1024
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
CONTROLS = ("isolated_home", "updates_disabled", "plugins_disabled", "hooks_disabled",
            "mcp_disabled", "unrelated_tools_denied")
CLIENTS = {
    "claude": ("claude-code", "claude-code-cli"),
    "cursor": ("cursor", "cursor-project"),
    "copilot": ("github-copilot", "vscode-copilot"),
    "codex": ("codex", "codex-cli"),
    "gemini": ("gemini-cli", "gemini-cli"),
    "opencode": ("opencode", "opencode-v2"),
    "kilo": ("kilo", "kilo-cli"),
}
SECRET_PATTERNS = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"://[^/\s:@]+:[^/\s@]+@"),
)


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("duplicate JSON key: %s" % key)
        result[key] = value
    return result


def _constant(value):
    raise EvidenceError("non-finite JSON number: %s" % value)


def parse_json(text):
    try:
        return json.loads(text, object_pairs_hook=_object, parse_constant=_constant)
    except (ValueError, TypeError, RecursionError) as exc:
        raise EvidenceError("invalid evidence JSON: %s" % exc) from exc


def read_json(path):
    try:
        info = os.lstat(path)
        require(stat.S_ISREG(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                "evidence must be a regular unlinked file: %s" % path)
        require(0 < info.st_size <= MAX_JSON_BYTES, "evidence JSON size is outside its limit")
        with open(path, "r", encoding="utf-8") as handle:
            return parse_json(handle.read())
    except (OSError, UnicodeError) as exc:
        raise EvidenceError("cannot read evidence: %s" % exc) from exc


def atomic_json(path, value):
    path = os.path.abspath(path)
    parent = os.path.dirname(path)
    require(os.path.isdir(parent), "evidence output parent does not exist")
    require(not os.path.islink(path), "evidence output must not be linked")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=parent,
                                         prefix=".agent-reach-", suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except (OSError, ValueError) as exc:
        raise EvidenceError("cannot publish evidence atomically: %s" % exc) from exc
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def _runtime():
    path = os.path.join(HERE, "install.py")
    require(os.path.isfile(path) and not os.path.islink(path), "trusted installer runtime is missing or linked")
    spec = importlib.util.spec_from_file_location("_agent_reach_install", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, module.load_agent_profiles(SOURCE_ROOT)


INSTALL, PROFILES = _runtime()


def required_levels(profile):
    return [1, 2, 3] if profile in ("claude", "opencode") else [1, 2]


def _git(root, args):
    result = subprocess.run(["git", "-C", root] + list(args), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30)
    require(result.returncode == 0, "candidate Git verification failed: %s" % result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def _positive(value, label, integer=False):
    kind = isinstance(value, int) if integer else isinstance(value, (int, float))
    require(kind and not isinstance(value, bool) and math.isfinite(value) and value > 0,
            "%s must be positive and finite" % label)


def validate_limits(limits):
    require(isinstance(limits, dict), "capture limits must be an object")
    for key in ("attempts", "timeout_seconds", "response_bytes", "input_tokens", "max_input_tokens_per_attempt"):
        _positive(limits.get(key), key, integer=True)
    for key in ("cost_usd", "max_cost_per_attempt"):
        _positive(limits.get(key), key)
    require(limits["timeout_seconds"] <= 600, "capture timeout exceeds 600 seconds")
    require(limits["response_bytes"] <= MAX_JSON_BYTES, "capture byte limit exceeds maximum")
    require(limits["max_input_tokens_per_attempt"] <= limits["input_tokens"], "per-attempt tokens exceed total cap")
    require(limits["max_cost_per_attempt"] <= limits["cost_usd"], "per-attempt cost exceeds total cap")


def source_hashes(root):
    root = os.path.abspath(root)
    manifest_snapshot = INSTALL.snapshot(SOURCE_ROOT, INSTALL.MANIFEST)
    require(manifest_snapshot is not None, "trusted runtime manifest is missing")
    manifest = INSTALL.load_json(manifest_snapshot["data"], INSTALL.MANIFEST)
    result = {}
    for item in manifest["files"]:
        relative = item["source"]
        snapshot = INSTALL.snapshot(root, relative)
        require(snapshot is not None, "required candidate source is missing: %s" % relative)
        result[relative] = digest(snapshot["data"].replace(b"\r\n", b"\n"))
    policy = INSTALL.snapshot(root, "AGENTS.md")
    require(policy is not None, "candidate AGENTS.md is missing")
    result["AGENTS.md"] = digest(policy["data"].replace(b"\r\n", b"\n"))
    return result


def validate_registration(registration, root):
    require(isinstance(registration, dict) and registration.get("version") == 1, "registration version must be 1")
    require(isinstance(registration.get("registration_id"), str) and registration["registration_id"].startswith("agent-reach-"),
            "registration identity is invalid")
    root = os.path.abspath(root)
    revision = registration.get("candidate_sha", "")
    require(isinstance(revision, str) and GIT_SHA.fullmatch(revision), "candidate must be a full Git commit SHA")
    resolved = _git(root, ["rev-parse", "--verify", revision + "^{commit}"]).decode("ascii").strip()
    require(resolved == revision, "candidate SHA must resolve exactly")
    expected_hashes = source_hashes(root)
    require(registration.get("source_hashes") == expected_hashes, "registration source hashes are incomplete or stale")
    tracked = set(_git(root, ["ls-tree", "-r", "--name-only", revision]).decode("utf-8").splitlines())
    require(set(expected_hashes) <= tracked, "registration sources must already be committed")
    _git(root, ["diff", "--exit-code", revision, "--"] + sorted(expected_hashes))
    require(registration.get("registry_sha256") == digest(canonical(PROFILES.PROFILE_CONTRACT)),
            "trusted profile registry hash mismatch")
    profiles = registration.get("profiles")
    require(isinstance(profiles, dict) and set(profiles) == set(PROFILES.PROFILE_CONTRACT), "registration must include all seven profiles")
    for profile, identity in profiles.items():
        require(isinstance(identity, dict), "profile identity must be an object")
        require((identity.get("client_id"), identity.get("surface")) == CLIENTS[profile],
                "profile client or surface is not the declared target: %s" % profile)
        require(identity.get("required_levels") == required_levels(profile), "required evidence levels cannot be weakened")
        for key in ("version", "platform"):
            value = identity.get(key)
            require(isinstance(value, str) and value.strip() and value.casefold() not in ("unknown", "pending", "latest"),
                    "profile %s must identify %s" % (profile, key))
    validate_limits(registration.get("limits"))
    cases = registration.get("cases")
    require(isinstance(cases, list) and cases, "registration must include cases")
    ids = set()
    targets = set()
    for case in cases:
        require(isinstance(case, dict), "registered cases must be objects")
        case_id = case.get("id")
        require(isinstance(case_id, str) and case_id and case_id not in ids, "case IDs must be unique")
        ids.add(case_id)
        profile, level = case.get("profile"), case.get("level")
        require(profile in profiles and isinstance(level, int) and not isinstance(level, bool)
                and level in required_levels(profile), "case profile or level is invalid")
        targets.add((profile, level))
        name = case.get("probe_name", "")
        require(isinstance(name, str) and re.fullmatch(r"[a-z0-9-]+", name) and name not in PROFILES.PRODUCT_SKILLS,
                "probe must have a unique non-product skill name")
        nonce, prompt = case.get("nonce"), case.get("prompt")
        require(isinstance(nonce, str) and len(nonce) >= 12 and isinstance(prompt, str) and prompt,
                "case nonce and prompt are required")
        require(nonce not in prompt, "skill-only nonce must not leak into the prompt")
        repetitions = case.get("repetitions")
        require(isinstance(repetitions, int) and not isinstance(repetitions, bool) and repetitions >= (3 if level == 3 else 1),
                "case has insufficient repetitions")
        require(isinstance(case.get("expected_text"), list) and all(isinstance(value, str) and value for value in case["expected_text"]),
                "case expected text is invalid")
        require(isinstance(case.get("permitted_tools"), list) and all(isinstance(value, str) for value in case["permitted_tools"]),
                "case permitted tools are invalid")
    require(targets == {(profile, level) for profile in profiles for level in required_levels(profile)},
            "registration must cover every required profile level")
    return registration


def _scan(text, credentials=()):
    for credential in credentials:
        require(not credential or credential not in text, "capture contains configured credential material")
    require(not any(pattern.search(text) for pattern in SECRET_PATTERNS), "capture contains possible secret material")


def _observation(text):
    value = parse_json(text)
    require(isinstance(value, dict), "capture observation must be a reviewed JSON object")
    return value


def _safe_discovered_path(root, path):
    require(isinstance(path, str) and os.path.isabs(path), "discovered skill path must be absolute")
    for candidate in (root, path):
        current = os.path.abspath(candidate)
        while True:
            try:
                info = os.lstat(current)
            except OSError as exc:
                raise EvidenceError("discovered skill path is unavailable: %s" % exc) from exc
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                    "linked discovered skill paths are not trusted")
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
    root = os.path.realpath(root)
    path = os.path.realpath(path)
    relative = os.path.relpath(path, root).replace(os.sep, "/")
    try:
        return INSTALL.checked_path(root, relative)
    except INSTALL.InstallError as exc:
        raise EvidenceError("unsafe discovered skill path: %s" % exc) from exc


def _generation_outcome(positive, negative, cwd, registration, profile, root):
    expected, _ = INSTALL.read_payload(root)
    policy = INSTALL.inspect_canonical_policy(root)
    expected += PROFILES.render_profiles(root, [profile], policy["text"])
    files = positive.get("files")
    if not isinstance(files, dict) or set(files) != {item["relative"] for item in expected}:
        return False
    for item in expected:
        try:
            snapshot = INSTALL.snapshot(cwd, item["relative"])
        except INSTALL.InstallError:
            return False
        if snapshot is None or snapshot["record"]["sha256"] != item["record"]["sha256"] or files[item["relative"]] != item["record"]["sha256"]:
            return False
    policy_hash = registration["source_hashes"]["AGENTS.md"]
    actual_policy = INSTALL.snapshot(cwd, "AGENTS.md")
    return (actual_policy is not None and digest(actual_policy["data"].replace(b"\r\n", b"\n")) == policy_hash
            and positive.get("policy_before_sha256") == policy_hash and positive.get("policy_after_sha256") == policy_hash
            and not negative.get("files"))


def _discovery_outcome(positive, negative, cwd, profile, case, registration):
    skills = positive.get("skills")
    absent = negative.get("skills", [])
    if not isinstance(skills, list) or not isinstance(absent, list):
        return False
    prefix = PROFILES.PROFILE_CONTRACT[profile]["skill_prefix"]
    expected_names = set(PROFILES.PRODUCT_SKILLS) | {case["probe_name"]}
    found = {}
    for skill in skills:
        if not isinstance(skill, dict) or skill.get("name") in found:
            return False
        name = skill.get("name")
        if name not in expected_names:
            continue
        path = _safe_discovered_path(cwd, skill.get("path"))
        expected_path = INSTALL.checked_path(os.path.realpath(cwd), prefix + "/" + name + "/SKILL.md")
        if path != expected_path:
            return False
        snapshot = INSTALL.snapshot(cwd, prefix + "/" + name + "/SKILL.md")
        if snapshot is None:
            return False
        if name in PROFILES.PRODUCT_SKILLS:
            if digest(snapshot["data"].replace(b"\r\n", b"\n")) != registration["source_hashes"]["skills/%s/SKILL.md" % name]:
                return False
        elif case["nonce"] not in snapshot["data"].decode("utf-8", "replace"):
            return False
        found[name] = path
    if set(found) != expected_names:
        return False
    return not any(isinstance(skill, dict) and skill.get("name") == case["probe_name"] for skill in absent)


def _validate_record(record, registration, root):
    require(isinstance(record, dict) and record.get("version") == 1, "record version must be 1")
    record_id = record.get("id")
    require(isinstance(record_id, str) and record_id, "record ID is required")
    profile, level = record.get("profile"), record.get("level")
    require(profile in registration["profiles"] and isinstance(level, int) and not isinstance(level, bool)
            and level in required_levels(profile), "record profile or level is invalid")
    require(record.get("candidate_sha") == registration["candidate_sha"], "record candidate identity mismatch")
    require(record.get("registration_sha256") == digest(canonical(registration)), "record registration hash mismatch")
    require(record.get("source_hashes") == registration["source_hashes"], "record source hash mismatch")
    require(record.get("client") == registration["profiles"][profile], "record client/version/surface/platform mismatch")
    case = next((item for item in registration["cases"] if item["id"] == record.get("case_id")), None)
    require(case is not None and (case["profile"], case["level"]) == (profile, level), "record case identity mismatch")
    kind = record.get("capture_kind")
    require(kind in ("generated", "native", "synthetic"), "record capture kind is invalid")
    require(level == 1 or kind != "generated", "generated files cannot establish native discovery or behavior")
    controls = record.get("controls")
    require(isinstance(controls, dict) and all(controls.get(name) is True for name in CONTROLS), "capture isolation controls are incomplete")
    captures = record.get("captures")
    require(isinstance(captures, list) and len(captures) == case["repetitions"], "record repeat coverage is incomplete")
    seen = set()
    outcomes = []
    for pair in captures:
        require(isinstance(pair, dict) and pair.get("repeat") not in seen, "duplicate capture repeat")
        repeat = pair.get("repeat")
        require(isinstance(repeat, int) and not isinstance(repeat, bool) and 1 <= repeat <= case["repetitions"], "capture repeat is invalid")
        seen.add(repeat)
        observations = []
        roots = []
        successful = True
        for control in ("positive", "negative"):
            capture = pair.get(control)
            require(isinstance(capture, dict), "capture control is missing")
            code = capture.get("exit_code")
            require(isinstance(code, int) and not isinstance(code, bool), "capture has no terminal exit outcome")
            successful = successful and code == 0
            cwd = capture.get("cwd")
            require(isinstance(cwd, str) and os.path.isabs(cwd) and os.path.isdir(cwd), "capture working directory is invalid")
            roots.append(os.path.abspath(cwd))
            for stream in ("stdout", "stderr"):
                text = capture.get(stream)
                require(isinstance(text, str) and len(text.encode("utf-8")) <= registration["limits"]["response_bytes"], "capture stream exceeds its limit")
                require(capture.get(stream + "_sha256") == digest(text.encode("utf-8")), "capture stream hash mismatch")
                _scan(text)
            observations.append(_observation(capture["stdout"]))
        require(os.path.realpath(roots[0]) != os.path.realpath(roots[1]),
                "positive and negative controls must use distinct projects")
        positive, negative = observations
        if level == 1:
            passed = successful and _generation_outcome(positive, negative, roots[0], registration, profile, root)
        else:
            passed = successful and _discovery_outcome(positive, negative, roots[0], profile, case, registration)
            if level == 3:
                response = positive.get("response", "")
                negative_response = negative.get("response", "")
                tools = positive.get("tools", [])
                loaded = positive.get("loaded_skills", [])
                require(isinstance(response, str) and isinstance(negative_response, str) and isinstance(tools, list)
                        and isinstance(loaded, list), "behavior observations are invalid")
                passed = (passed and case["nonce"] in response and case["nonce"] not in negative_response
                          and all(value.casefold() in response.casefold() for value in case["expected_text"])
                          and case["probe_name"] in loaded and set(tools) <= set(case["permitted_tools"]))
        outcomes.append({"repeat": repeat, "status": "pass" if passed else "fail"})
    require(seen == set(range(1, case["repetitions"] + 1)), "record repeat coverage is incomplete")
    reviewer = record.get("reviewed_by")
    reviewed = isinstance(reviewer, str) and reviewer.strip() and reviewer.casefold() not in ("pending", "unknown")
    status = "pass" if all(item["status"] == "pass" for item in outcomes) else "fail"
    if kind == "synthetic" or not reviewed:
        status = "unverified"
    return {"id": record_id, "profile": profile, "level": level, "case_id": case["id"], "status": status,
            "capture_kind": kind, "reviewed_by": reviewer, "outcomes": outcomes}


def validate_record(record, registration, root):
    validate_registration(registration, root)
    return _validate_record(record, registration, root)


def replay(registration, records, root):
    validate_registration(registration, root)
    require(isinstance(records, list), "result ledger must be an array")
    results = []
    seen = set()
    for record in records:
        result = _validate_record(record, registration, root)
        require(result["id"] not in seen, "duplicate evidence result ID")
        seen.add(result["id"])
        results.append(result)
    profiles = {}
    for profile in PROFILES.PROFILE_CONTRACT:
        levels = {}
        for level in (1, 2, 3):
            scoped = [item for item in results if item["profile"] == profile and item["level"] == level]
            status = "unverified"
            if any(item["status"] == "fail" for item in scoped):
                status = "fail"
            elif scoped:
                expected_cases = {case["id"] for case in registration["cases"] if case["profile"] == profile and case["level"] == level}
                passed_cases = {item["case_id"] for item in scoped if item["status"] == "pass"}
                if expected_cases and passed_cases == expected_cases:
                    status = "pass"
            levels[str(level)] = {"status": status, "evidence_ids": sorted(item["id"] for item in scoped)}
        profiles[profile] = {"required_levels": required_levels(profile), "identity": registration["profiles"][profile], "levels": levels}
    complete = all(profiles[profile]["levels"][str(level)]["status"] == "pass"
                   for profile in profiles for level in required_levels(profile))
    return {"version": 1, "registration_id": registration["registration_id"], "candidate_sha": registration["candidate_sha"],
            "registry_sha256": registration["registry_sha256"], "profiles": profiles,
            "results": sorted(results, key=lambda item: item["id"]), "complete": complete,
            "limitations": ["Replay checks retained evidence; it does not authenticate native clients or human reviewers and makes no live calls."]}


def _matrix_cell(value):
    require(isinstance(value, str), "matrix values must be strings")
    require("\n" not in value and "|" not in value and "`" not in value, "matrix value contains unsafe Markdown")
    return value


def render_support_matrix(registration, replayed):
    require(isinstance(replayed, dict) and replayed.get("version") == 1, "matrix replay result is invalid")
    require(replayed.get("registration_id") == registration.get("registration_id"), "matrix registration identity is stale")
    require(replayed.get("candidate_sha") == registration.get("candidate_sha"), "matrix candidate identity is stale")
    require(replayed.get("registry_sha256") == registration.get("registry_sha256"), "matrix profile registry is stale")
    profiles = replayed.get("profiles")
    require(isinstance(profiles, dict) and set(profiles) == set(PROFILES.PROFILE_CONTRACT),
            "matrix must contain exactly the seven profiles")
    results = replayed.get("results")
    require(isinstance(results, list), "matrix replay results must be an array")
    evidence_ids = [item.get("id") for item in results]
    require(all(isinstance(value, str) and value for value in evidence_ids)
            and len(evidence_ids) == len(set(evidence_ids)), "matrix evidence IDs must be unique")
    known_ids = set(evidence_ids)
    lines = [
        "### Generated native profile evidence",
        "",
        "| Profile | Native surface | Client / version / platform | Required | Level 1 | Level 2 | Level 3 | Evidence IDs | Tested SHA |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for profile, descriptor in PROFILES.PROFILE_CONTRACT.items():
        row = profiles[profile]
        require(row.get("required_levels") == required_levels(profile), "matrix required levels differ from registration")
        require(row.get("identity") == registration["profiles"][profile], "matrix client identity differs from registration")
        levels = row.get("levels")
        require(isinstance(levels, dict) and set(levels) == {"1", "2", "3"}, "matrix must report three independent levels")
        ids = []
        statuses = []
        for level in ("1", "2", "3"):
            item = levels[level]
            require(isinstance(item, dict) and item.get("status") in ("pass", "fail", "unverified"),
                    "matrix level status is invalid")
            scoped = item.get("evidence_ids")
            require(isinstance(scoped, list) and len(scoped) == len(set(scoped)) and set(scoped) <= known_ids,
                    "matrix level evidence references are invalid")
            ids.extend(scoped)
            statuses.append(item["status"])
        require(len(ids) == len(set(ids)), "matrix evidence cannot satisfy more than one level")
        identity = row["identity"]
        identity_text = "%s / %s / %s" % (identity["client_id"], identity["version"], identity["platform"])
        required_text = ",".join("L%d" % level for level in row["required_levels"])
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s | %s | `%s` |" % (
            profile, _matrix_cell(descriptor["surface"]), _matrix_cell(identity_text), required_text,
            statuses[0], statuses[1], statuses[2], "<br>".join(sorted(ids)) or "none",
            replayed["candidate_sha"],
        ))
    lines.extend([
        "",
        "Level 1 is generated-file evidence, Level 2 is native-loader discovery, and Level 3 is reviewed native behavior. Each level is independent.",
        "Synthetic fixtures and metadata-only records remain `unverified`. Missing clients or unsafe startup remain blockers, not implicit support.",
        "The archived `one-front-door` committed-candidate proof task was incomplete and is not supplied by this matrix.",
    ])
    return "\n".join(lines) + "\n"


def _matrix_document(path, section=None):
    try:
        info = os.lstat(path)
        require(stat.S_ISREG(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                "matrix document must be a regular unlinked file")
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeError) as exc:
        raise EvidenceError("cannot read matrix document: %s" % exc) from exc
    start_marker = "<!-- agent-reach:start -->"
    end_marker = "<!-- agent-reach:end -->"
    require(text.count(start_marker) == 1 and text.count(end_marker) == 1,
            "matrix document must contain one bounded agent-reach section")
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker)
    require(start <= end, "matrix markers are out of order")
    if section is None:
        return text[start:end].strip() + "\n"
    return text[:start] + "\n" + section.rstrip() + "\n" + text[end:]


def check_matrix(path, section):
    return _matrix_document(path) == section.strip() + "\n"


def update_matrix(path, section):
    updated = _matrix_document(path, section)
    with open(path, "r", encoding="utf-8") as handle:
        current = handle.read()
    if updated == current:
        return False
    path = os.path.abspath(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=os.path.dirname(path),
                                         prefix=".agent-reach-matrix-", suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise EvidenceError("cannot update matrix atomically: %s" % exc) from exc
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return True


def native_command(profile, operation, client_prefix, prompt=None):
    """Construct only documented candidate operations, never a substitute surface."""
    require(profile in CLIENTS, "unsupported native profile")
    require(isinstance(client_prefix, list) and client_prefix and
            all(isinstance(value, str) and value and "\x00" not in value for value in client_prefix),
            "client prefix must be an explicit argv list")
    require(os.path.isabs(client_prefix[0]) and os.path.isfile(client_prefix[0])
            and not os.path.islink(client_prefix[0]), "client executable must be an absolute unlinked path")
    if operation == "discovery":
        if profile == "kilo":
            return client_prefix + ["debug", "skill"]
        if profile == "gemini":
            return client_prefix + ["skills", "list"]
        raise EvidenceError("this surface requires a reviewed interactive or version-specific API capture; no universal discovery command")
    require(operation == "behavior" and isinstance(prompt, str) and prompt, "behavior capture requires a registered prompt")
    if profile == "claude":
        return client_prefix + ["-p", prompt, "--output-format", "stream-json", "--verbose"]
    if profile == "opencode":
        return client_prefix + ["run", "--format", "json", prompt]
    raise EvidenceError("this behavior surface is not a declared automated Level 3 target")


def run_capture(command, *, cwd, ledger_path, cache_dir, limits, context_id, capture_kind,
                env, approved=False, setup=None, credential_values=()):
    require(approved is True, "capture execution needs explicit approval")
    validate_limits(limits)
    require(capture_kind in ("synthetic", "native"), "capture kind is invalid")
    require(isinstance(command, list) and command and all(isinstance(arg, str) and arg and "\x00" not in arg for arg in command),
            "capture command must be an explicit non-empty argv list")
    require(os.path.isabs(command[0]) and os.path.isfile(command[0]) and not os.path.islink(command[0]),
            "capture executable must be an explicit unlinked absolute path")
    if capture_kind == "native":
        require(isinstance(setup, dict) and setup.get("verified") is True and setup.get("approved_by"), "native capture needs verified client-version setup")
        require(setup.get("argv") == command and all(setup.get("controls", {}).get(name) is True for name in CONTROLS),
                "native capture argv or isolation differs from approved setup")
    require(isinstance(context_id, str) and context_id, "capture context identity is required")
    require(isinstance(env, dict) and all(isinstance(key, str) and isinstance(value, str) for key, value in env.items()), "capture environment must be explicit")
    cwd = os.path.abspath(cwd)
    require(os.path.isdir(cwd), "capture directory is missing")
    with open(command[0], "rb") as handle:
        binary_sha = digest(handle.read())
    if capture_kind == "native":
        require(setup.get("binary_sha256") == binary_sha, "client binary hash differs from setup")
    key = digest(canonical({"argv": command, "cwd": cwd, "context_id": context_id, "capture_kind": capture_kind,
                            "binary_sha256": binary_sha, "environment_sha256": digest(canonical(env))}))
    cache_dir = os.path.abspath(cache_dir)
    ledger_path = os.path.abspath(ledger_path)
    os.makedirs(cache_dir, exist_ok=True)
    require(os.path.isdir(os.path.dirname(ledger_path)), "capture ledger parent is missing")
    cache_path = os.path.join(cache_dir, key + ".json")
    if os.path.isfile(cache_path):
        result = read_json(cache_path)
        require(result.get("request_sha256") == key, "capture cache identity mismatch")
        for stream in ("stdout", "stderr"):
            require(result.get(stream + "_sha256") == digest(result[stream].encode("utf-8")), "capture cache stream hash mismatch")
            _scan(result[stream], credential_values)
        result["cached"] = True
        return result
    require(not os.path.islink(ledger_path), "capture ledger must not be linked")
    lock_path = ledger_path + ".lock"
    try:
        lock = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError as exc:
        raise EvidenceError("capture ledger is locked or unavailable: %s" % exc) from exc
    os.close(lock)
    process = None
    try:
        ledger = read_json(ledger_path) if os.path.isfile(ledger_path) else {"attempts": 0, "reserved_input_tokens": 0, "reserved_cost_usd": 0}
        require(isinstance(ledger.get("attempts"), int) and ledger["attempts"] >= 0, "capture attempt ledger is invalid")
        cost = Decimal(str(ledger["reserved_cost_usd"])) + Decimal(str(limits["max_cost_per_attempt"]))
        tokens = ledger["reserved_input_tokens"] + limits["max_input_tokens_per_attempt"]
        require(ledger["attempts"] < limits["attempts"], "capture attempt cap is exhausted")
        require(tokens <= limits["input_tokens"] and cost <= Decimal(str(limits["cost_usd"])), "capture token or cost reservation cap is exhausted")
        ledger.update(attempts=ledger["attempts"] + 1, reserved_input_tokens=tokens, reserved_cost_usd=float(cost))
        atomic_json(ledger_path, ledger)
        started = time.monotonic()
        process = subprocess.Popen(command, cwd=cwd, env=env, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        oversized = threading.Event()

        def read_stream(name):
            stream = getattr(process, name)
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                remaining = limits["response_bytes"] - len(buffers[name])
                buffers[name].extend(chunk[:max(0, remaining)])
                if len(chunk) > remaining:
                    oversized.set()
                    process.kill()
                    break

        readers = [threading.Thread(target=read_stream, args=(name,), daemon=True) for name in buffers]
        for reader in readers:
            reader.start()
        try:
            code = process.wait(timeout=limits["timeout_seconds"])
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise EvidenceError("capture process timed out")
        for reader in readers:
            reader.join(timeout=1)
        require(not any(reader.is_alive() for reader in readers), "capture output pipes remained open")
        require(not oversized.is_set(), "capture output exceeds response byte cap")
        stdout = bytes(buffers["stdout"]).decode("utf-8")
        stderr = bytes(buffers["stderr"]).decode("utf-8")
        _scan(stdout + "\n" + stderr, credential_values)
        result = {"version": 1, "request_sha256": key, "argv": command, "cwd": cwd,
                  "binary_sha256": binary_sha, "capture_kind": capture_kind,
                  "evidence_eligible": capture_kind == "native", "cached": False,
                  "exit_code": code, "stdout": stdout, "stderr": stderr,
                  "stdout_sha256": digest(stdout.encode("utf-8")), "stderr_sha256": digest(stderr.encode("utf-8")),
                  "duration_ms": round((time.monotonic() - started) * 1000, 3),
                  "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                  "environment_names": sorted(env), "attempts": ledger["attempts"],
                  "reserved_input_tokens": tokens, "reserved_cost_usd": float(cost)}
        atomic_json(cache_path, result)
        return result
    except (OSError, UnicodeError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, EvidenceError):
            raise
        raise EvidenceError("capture failed: %s" % exc) from exc
    finally:
        if process is not None:
            for stream in (process.stdout, process.stderr):
                if stream:
                    stream.close()
        os.unlink(lock_path)


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command")
    for action in ("validate", "replay"):
        command = subcommands.add_parser(action)
        command.add_argument("--root", default=".")
        command.add_argument("--registration", required=True)
        command.add_argument("--records")
        command.add_argument("--out")
        command.add_argument("--json", action="store_true")
    capture = subcommands.add_parser("capture", help="collect one explicitly approved, setup-verified native attempt")
    capture.add_argument("--root", default=".")
    capture.add_argument("--registration", required=True)
    capture.add_argument("--case", required=True)
    capture.add_argument("--setup", required=True)
    capture.add_argument("--client-argv", required=True)
    capture.add_argument("--cwd", required=True)
    capture.add_argument("--ledger", required=True)
    capture.add_argument("--cache-dir", required=True)
    capture.add_argument("--out", required=True)
    capture.add_argument("--approved", action="store_true")
    capture.add_argument("--json", action="store_true")
    matrix = subcommands.add_parser("matrix", help="generate or check the bounded support matrix")
    matrix.add_argument("--root", default=".")
    matrix.add_argument("--registration", required=True)
    matrix.add_argument("--records", required=True)
    matrix.add_argument("--document", required=True)
    mode = matrix.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    matrix.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    try:
        registration = read_json(args.registration)
        if args.command == "matrix":
            validate_registration(registration, args.root)
            ledger = read_json(args.records)
            require(ledger.get("version") == 1, "result ledger version must be 1")
            replayed = replay(registration, ledger.get("records"), args.root)
            section = render_support_matrix(registration, replayed)
            matching = check_matrix(args.document, section)
            if args.write:
                changed = update_matrix(args.document, section)
                matching = check_matrix(args.document, section)
            else:
                changed = False
            result = {"version": 1, "status": "matching" if matching else "drift",
                      "changed": changed, "candidate_sha": registration["candidate_sha"]}
        elif args.command == "capture":
            validate_registration(registration, args.root)
            case = next((item for item in registration["cases"] if item["id"] == args.case), None)
            require(case is not None and case["level"] in (2, 3), "native capture case is missing or not native")
            setup = read_json(args.setup)
            require(setup.get("identity") == registration["profiles"][case["profile"]], "setup client identity differs from registration")
            prefix = parse_json(args.client_argv)
            operation = "discovery" if case["level"] == 2 else "behavior"
            command = native_command(case["profile"], operation, prefix, case["prompt"])
            names = setup.get("environment_names", [])
            require(isinstance(names, list) and len(names) == len(set(names)) and
                    all(isinstance(name, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in names),
                    "setup must list environment variable names, never credential values")
            environment = {name: os.environ[name] for name in names if name in os.environ}
            overrides = setup.get("environment_overrides", {})
            safe_overrides = {"HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_CONFIG_HOME",
                              "TEMP", "TMP", "TMPDIR", "PATH", "PYTHONDONTWRITEBYTECODE", "NO_COLOR"}
            require(isinstance(overrides, dict) and set(overrides) <= safe_overrides and
                    all(isinstance(value, str) for value in overrides.values()), "setup overrides must be nonsecret isolation settings")
            require("environment" not in setup, "setup must not persist credential environment values")
            environment.update(overrides)
            credentials = [environment[name] for name in names if name in environment and
                           re.search(r"credential|key|password|secret|token", name, re.I) and len(environment[name]) >= 8]
            result = run_capture(command, cwd=args.cwd, ledger_path=args.ledger, cache_dir=args.cache_dir,
                                 limits=registration["limits"], context_id=case["id"] + ":" + args.cwd,
                                 capture_kind="native", env=environment, approved=args.approved, setup=setup,
                                 credential_values=credentials)
            result["candidate_sha"] = registration["candidate_sha"]
            result["status"] = "captured-not-validated"
        elif args.command == "replay" or args.records:
            require(bool(args.records), "replay requires --records")
            ledger = read_json(args.records)
            require(ledger.get("version") == 1, "result ledger version must be 1")
            result = replay(registration, ledger.get("records"), args.root)
        else:
            validate_registration(registration, args.root)
            result = {"version": 1, "status": "valid", "registration_id": registration["registration_id"],
                      "candidate_sha": registration["candidate_sha"]}
        if args.out:
            atomic_json(args.out, result)
    except (EvidenceError, INSTALL.InstallError, OSError, UnicodeError) as exc:
        if args.json:
            print(json.dumps({"status": "invalid", "error": str(exc)}, sort_keys=True))
        else:
            sys.stderr.write("agent_reach: %s\n" % exc)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("agent reach %s for %s" % (result.get("status", "complete" if result.get("complete") else "incomplete"), result["candidate_sha"]))
    return 1 if result.get("status") == "drift" else 0


if __name__ == "__main__":
    sys.exit(run())
