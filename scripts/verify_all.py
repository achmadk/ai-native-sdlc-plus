"""Run fixed repository verification stages and emit a revision-bound receipt."""

import sys

if sys.version_info < (3, 8):
    sys.exit("verify_all requires Python >= 3.8")
sys.dont_write_bytecode = True

import argparse
import datetime
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import tempfile
import time


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(HERE)
SKILL_IDS = {
    "ai-readiness-and-metrics", "ai-sdlc", "autonomy-policy", "context-pack",
    "decision-trace", "learning-mode", "review-by-intent", "ship-and-observe",
    "spec-first", "verify-and-evals",
}
MAX_JSON_BYTES = 4 * 1024 * 1024
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class VerificationError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise VerificationError(message)


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _bytes(value):
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8", "replace")


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _git(root, args, check=True):
    result = subprocess.run(
        ["git", "-C", root] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if check and result.returncode != 0:
        raise VerificationError("git %s failed: %s" % (
            " ".join(args), result.stderr.decode("utf-8", "replace").strip()))
    return result


def fixed_plan(root, python, loader_record):
    root = os.path.realpath(os.path.abspath(root))
    return [
        {
            "name": "unit",
            "kind": "subprocess",
            "command": [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
            "timeout": 1800,
        },
        {
            "name": "mutation",
            "kind": "subprocess",
            "command": [python, "-B", os.path.join(root, "tests", "mutate.py")],
            "timeout": 7200,
        },
        {
            "name": "doctor",
            "kind": "subprocess",
            "command": [python, "-I", "-B", os.path.join(root, "scripts", "doctor.py"),
                        "--root", root, "--json"],
            "timeout": 300,
        },
        {
            "name": "footprint",
            "kind": "footprint",
            "loader_record": os.path.realpath(os.path.abspath(loader_record)),
            "timeout": 60,
        },
    ]


def parse_counts(name, stdout, stderr):
    stdout_text = _bytes(stdout).decode("utf-8", "replace")
    stderr_text = _bytes(stderr).decode("utf-8", "replace")
    combined = stdout_text + "\n" + stderr_text
    if name == "unit":
        ran = re.search(r"Ran\s+(\d+)\s+tests?", combined)
        skipped = re.search(r"skipped=(\d+)", combined)
        failures = re.search(r"failures=(\d+)", combined)
        errors = re.search(r"errors=(\d+)", combined)
        return {
            "tests": int(ran.group(1)) if ran else 0,
            "skipped": int(skipped.group(1)) if skipped else 0,
            "failures": int(failures.group(1)) if failures else 0,
            "errors": int(errors.group(1)) if errors else 0,
        }
    if name == "mutation":
        match = re.search(
            r"Mutation score:\s*(\d+)/(\d+) killed,\s*(\d+) survived,\s*"
            r"(\d+) infrastructure error\(s\),\s*(\d+) equivalent", combined)
        if match:
            values = [int(value) for value in match.groups()]
            return dict(zip(("killed", "total", "survived", "infrastructure_errors", "equivalent"), values))
        current = re.search(
            r"killed\s+(\d+)\s*/\s*(\d+)\s+non-equivalent mutants;\s*"
            r"(\d+)\s+equivalent survivor\(s\) documented", combined)
        if current:
            killed, total, equivalent = [int(value) for value in current.groups()]
            return {"killed": killed, "total": total, "survived": total - killed,
                    "infrastructure_errors": 0, "equivalent": equivalent}
        return {"killed": 0, "total": 0, "survived": 0,
                "infrastructure_errors": 0, "equivalent": 0}
    if name == "doctor":
        try:
            data = json.loads(stdout_text)
        except ValueError:
            return {"OK": 0, "WARN": 0, "FAIL": 0}
        if isinstance(data, dict) and isinstance(data.get("summary"), dict):
            summary = data["summary"]
            _require(all(isinstance(value, int) and value >= 0 for value in summary.values()),
                     "doctor summary counts must be nonnegative integers")
            return dict(sorted(summary.items()))
        if isinstance(data, dict):
            data = data.get("results", data.get("checks", []))
        counts = {"OK": 0, "WARN": 0, "FAIL": 0}
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("status") in counts:
                    counts[item["status"]] += 1
        return counts
    return {}


def run_subprocess_stage(stage, root, env, run=subprocess.run):
    started = time.monotonic()
    stdout = stderr = b""
    limitations = []
    try:
        result = run(
            stage["command"], cwd=root, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=stage["timeout"], shell=False,
        )
        stdout = _bytes(result.stdout)
        stderr = _bytes(result.stderr)
        exit_code = result.returncode
        status = "pass" if exit_code == 0 else "fail"
        if status == "fail":
            limitations.append("command exited with status %d" % exit_code)
    except subprocess.TimeoutExpired as exc:
        stdout = _bytes(exc.output)
        stderr = _bytes(exc.stderr)
        exit_code = 124
        status = "fail"
        limitations.append("stage timeout after %d seconds" % stage["timeout"])
    except OSError as exc:
        exit_code = 127
        status = "fail"
        limitations.append("stage could not start: %s" % exc)
    return {
        "name": stage["name"],
        "kind": stage["kind"],
        "command": list(stage["command"]),
        "timeout_seconds": stage["timeout"],
        "status": status,
        "exit_code": exit_code,
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
        "stdout_sha256": _sha256(stdout),
        "stderr_sha256": _sha256(stderr),
        "counts": parse_counts(stage["name"], stdout, stderr),
        "limitations": limitations,
    }


def execute_plan(plan, runner):
    results = []
    blocker = None
    for stage in plan:
        if blocker:
            results.append({
                "name": stage["name"],
                "kind": stage["kind"],
                "command": list(stage.get("command", [])),
                "timeout_seconds": stage["timeout"],
                "status": "skipped",
                "exit_code": None,
                "duration_ms": 0,
                "counts": {},
                "limitations": ["not run after nonpassing %s stage" % blocker],
            })
            continue
        result = runner(stage)
        results.append(result)
        if result["status"] != "pass":
            blocker = stage["name"]
    return results


def git_provenance(root, excluded_paths=None):
    root = os.path.realpath(os.path.abspath(root))
    excluded = {path.replace("\\", "/") for path in (excluded_paths or [])}
    tested_sha = _git(root, ["rev-parse", "HEAD"]).stdout.decode("ascii").strip()
    result = _git(root, ["status", "--porcelain=v1", "--untracked-files=all", "-z"])
    changed = []
    for entry in result.stdout.decode("utf-8", "replace").split("\0"):
        if not entry:
            continue
        path = entry[3:].replace("\\", "/")
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path not in excluded:
            changed.append(path)
    changed = sorted(set(changed))
    return {
        "tested_sha": tested_sha,
        "state": "dirty" if changed else "clean",
        "changed_paths": changed,
    }


def _frontmatter(text, path):
    match = re.match(r'^---\nname: (\S+)\ndescription: "(.*)"\n---\n', text, re.S)
    _require(match is not None, "%s frontmatter is invalid" % path)
    return match.group(1), match.group(2), text[match.end():]


def footprint_inputs(root):
    root = os.path.realpath(os.path.abspath(root))
    skills_root = os.path.join(root, "skills")
    found = sorted(name for name in os.listdir(skills_root)
                   if os.path.isfile(os.path.join(skills_root, name, "SKILL.md")))
    _require(set(found) == SKILL_IDS, "footprint requires the ten product skills")
    catalog = []
    bodies = {}
    description_bytes = body_bytes = 0
    for skill_id in found:
        relative = "skills/%s/SKILL.md" % skill_id
        path = os.path.join(root, relative.replace("/", os.sep))
        with open(path, "rb") as handle:
            normalized = handle.read().replace(b"\r\n", b"\n")
        try:
            text = normalized.decode("utf-8")
        except UnicodeError as exc:
            raise VerificationError("%s is not UTF-8: %s" % (relative, exc))
        name, description, body = _frontmatter(text, relative)
        _require(name == skill_id, "%s name does not match directory" % relative)
        catalog.append({"id": skill_id, "description": description})
        description_bytes += len(description.encode("utf-8"))
        body_size = len(body.encode("utf-8"))
        body_bytes += body_size
        bodies[relative] = {"sha256": _sha256(normalized), "bytes": body_size}
    return {
        "catalog_sha256": _sha256(_canonical(catalog)),
        "descriptions_bytes": description_bytes,
        "bodies_bytes": body_bytes,
        "bodies": bodies,
    }


def _read_json(path, label):
    if not os.path.isfile(path):
        raise VerificationError("%s not found: %s" % (label, path))
    size = os.path.getsize(path)
    _require(0 < size <= MAX_JSON_BYTES, "%s size must be 1..%d bytes" % (label, MAX_JSON_BYTES))
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle, parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError("non-finite JSON number: %s" % value)))
    except (OSError, UnicodeError, ValueError) as exc:
        raise VerificationError("cannot read %s: %s" % (label, exc))
    _require(isinstance(data, dict), "%s root must be an object" % label)
    return data


def measure_footprint(root, loader_record):
    inputs = footprint_inputs(root)
    result = {
        "status": "unverified",
        "recorded_revision": None,
        "descriptions": {
            "bytes": inputs["descriptions_bytes"],
            "tokens": None,
            "sha256": inputs["catalog_sha256"],
        },
        "bodies": {
            "bytes": inputs["bodies_bytes"],
            "tokens": None,
            "source_count": len(inputs["bodies"]),
        },
        "max_lane_tokens": None,
        "lanes": {},
        "limitations": ["actual loader token record unavailable"],
    }
    if not os.path.isfile(loader_record):
        return result
    record = _read_json(loader_record, "loader record")
    _require(record.get("version") == 1, "loader record version must be 1")
    revision = record.get("recorded_revision", "")
    _require(bool(GIT_SHA.fullmatch(revision)), "loader recorded_revision must be a full Git SHA")
    _git(root, ["rev-parse", "--verify", "%s^{commit}" % revision])
    accounting = record.get("accounting")
    _require(isinstance(accounting, dict) and
             accounting.get("method") == "kilo-skill-tool-step-token-delta",
             "loader accounting method is missing or unsupported")
    _require(isinstance(accounting.get("provider"), str) and accounting["provider"],
             "loader accounting provider is missing")
    _require(isinstance(accounting.get("model"), str) and accounting["model"],
             "loader accounting model is missing")
    _require(bool(SHA256.fullmatch(accounting.get("probe_evidence_sha256", ""))),
             "loader probe evidence hash is invalid")
    catalog = record.get("catalog")
    _require(isinstance(catalog, dict), "loader catalog must be an object")
    _require(catalog.get("sha256") == inputs["catalog_sha256"], "loader catalog hash mismatch")
    catalog_tokens = catalog.get("tokens")
    _require(isinstance(catalog_tokens, int) and catalog_tokens >= 0,
             "loader catalog tokens must be a nonnegative integer")
    body_records = record.get("skill_bodies")
    _require(isinstance(body_records, list), "loader skill_bodies must be an array")
    _require(len(body_records) == len(inputs["bodies"]), "loader must account for all skill bodies")
    token_by_path = {}
    for item in body_records:
        _require(isinstance(item, dict), "loader body records must be objects")
        path = item.get("path")
        _require(path in inputs["bodies"] and path not in token_by_path,
                 "loader body path is unknown or repeated")
        _require(item.get("sha256") == inputs["bodies"][path]["sha256"],
                 "loader body hash mismatch for %s" % path)
        tokens = item.get("tokens")
        _require(isinstance(tokens, int) and tokens >= 0,
                 "loader body tokens must be nonnegative for %s" % path)
        blob = _git(root, ["show", "%s:%s" % (revision, path)]).stdout.replace(b"\r\n", b"\n")
        _require(_sha256(blob) == item["sha256"],
                 "loader body does not match recorded revision for %s" % path)
        token_by_path[path] = tokens
    lanes = record.get("lanes")
    _require(isinstance(lanes, dict) and set(lanes) == {"Lite", "Standard", "Critical"},
             "loader lanes must be Lite, Standard, and Critical")
    normalized_lanes = {}
    for lane in ("Lite", "Standard", "Critical"):
        item = lanes[lane]
        _require(isinstance(item, dict), "%s loader lane must be an object" % lane)
        loaded = item.get("loaded_paths")
        unexpected = item.get("unexpected_paths")
        repeated = item.get("repeated_paths")
        _require(isinstance(loaded, list) and len(loaded) == len(set(loaded)) and
                 all(path in token_by_path for path in loaded),
                 "%s loaded_paths are invalid" % lane)
        _require(isinstance(unexpected, list) and isinstance(repeated, list),
                 "%s unexpected/repeated paths must be arrays" % lane)
        _require(not unexpected, "%s loader record contains unexpected content" % lane)
        _require(not repeated, "%s loader record contains repeated content" % lane)
        loaded_tokens = item.get("loaded_tokens")
        if loaded_tokens is None:
            loaded_tokens = sum(token_by_path[path] for path in loaded)
        _require(isinstance(loaded_tokens, int) and loaded_tokens >= 0,
                 "%s loaded token count must be a nonnegative integer" % lane)
        expected_total = catalog_tokens + loaded_tokens
        _require(item.get("total_tokens") == expected_total,
                 "%s loader total does not match accounted sources" % lane)
        normalized_lanes[lane] = {
            "loaded_paths": loaded,
            "unexpected_paths": unexpected,
            "repeated_paths": repeated,
            "loaded_tokens": loaded_tokens,
            "total_tokens": expected_total,
        }
    result.update({
        "status": "verified",
        "recorded_revision": revision,
        "accounting": accounting,
        "descriptions": {
            "bytes": inputs["descriptions_bytes"],
            "tokens": catalog_tokens,
            "sha256": inputs["catalog_sha256"],
        },
        "bodies": {
            "bytes": inputs["bodies_bytes"],
            "tokens": sum(token_by_path.values()),
            "source_count": len(token_by_path),
        },
        "max_lane_tokens": max(item["total_tokens"] for item in normalized_lanes.values()),
        "lanes": normalized_lanes,
        "limitations": [],
    })
    return result


def run_footprint_stage(stage, root):
    started = time.monotonic()
    try:
        footprint = measure_footprint(root, stage["loader_record"])
        status = footprint["status"]
        exit_code = 0 if status == "verified" else 4
        limitations = list(footprint["limitations"])
    except VerificationError as exc:
        footprint = None
        status = "fail"
        exit_code = 1
        limitations = [str(exc)]
    counts = {}
    if footprint:
        counts = {
            "description_bytes": footprint["descriptions"]["bytes"],
            "body_bytes": footprint["bodies"]["bytes"],
            "description_tokens": footprint["descriptions"]["tokens"],
            "body_tokens": footprint["bodies"]["tokens"],
            "max_lane_tokens": footprint["max_lane_tokens"],
        }
    return {
        "name": stage["name"],
        "kind": stage["kind"],
        "command": [],
        "timeout_seconds": stage["timeout"],
        "status": status,
        "exit_code": exit_code,
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
        "counts": counts,
        "limitations": limitations,
        "footprint": footprint,
    }


def input_hashes(root):
    root = os.path.realpath(os.path.abspath(root))
    relative_paths = []
    for directory, suffix in (("scripts", ".py"), ("tests", ".py")):
        base = os.path.join(root, directory)
        relative_paths.extend(
            "%s/%s" % (directory, name)
            for name in sorted(os.listdir(base))
            if name.endswith(suffix) and os.path.isfile(os.path.join(base, name)))
    relative_paths.extend(
        "skills/%s/SKILL.md" % skill_id for skill_id in sorted(SKILL_IDS))
    hashes = {}
    for relative in relative_paths:
        with open(os.path.join(root, relative.replace("/", os.sep)), "rb") as handle:
            hashes[relative] = _sha256(handle.read().replace(b"\r\n", b"\n"))
    return hashes


def environment_info():
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
    }


def build_receipt(provenance, stages, footprint, environment, hashes, generated_at):
    statuses = {stage["status"] for stage in stages}
    if "fail" in statuses:
        overall = "fail"
    elif "unverified" in statuses or "skipped" in statuses or provenance["state"] != "clean":
        overall = "unverified"
    else:
        overall = "pass"
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "tested_sha": provenance["tested_sha"],
        "tree_state": provenance["state"],
        "changed_paths": provenance["changed_paths"],
        "environment": environment,
        "input_hashes": dict(sorted(hashes.items())),
        "stages": stages,
        "footprint": footprint,
        "overall_status": overall,
    }


def _receipt_value(receipt, dotted):
    _require(isinstance(dotted, str) and dotted, "claim receipt path must be non-empty")
    current = receipt
    for part in dotted.split("."):
        if isinstance(current, list):
            matches = [item for item in current
                       if isinstance(item, dict) and item.get("name") == part]
            _require(len(matches) == 1, "claim receipt path not found: %s" % dotted)
            current = matches[0]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise VerificationError("claim receipt path not found: %s" % dotted)
    return current


def _claim_scalar(value):
    if value is None:
        return "unverified"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        _require(math.isfinite(value), "claim value must be finite")
        return ("%.6f" % value).rstrip("0").rstrip(".")
    _require(isinstance(value, (str, int)), "claim value must be scalar")
    return str(value)


def render_claim_block(config, receipt):
    _require(isinstance(config, dict), "claim marker config must be an object")
    claim_id = config.get("id", "")
    label = config.get("label", "")
    unit = config.get("unit", "")
    _require(bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", claim_id)), "claim id is invalid")
    for field, value in (("label", label), ("unit", unit)):
        _require(isinstance(value, str) and value and "`" not in value and "\n" not in value,
                 "claim %s is invalid" % field)
    value = _receipt_value(receipt, config.get("value_path"))
    status = _receipt_value(receipt, config.get("status_path"))
    revision = receipt.get("tested_sha")
    _require(isinstance(status, str) and status in ("pass", "fail", "unverified", "skipped"),
             "claim status is invalid")
    _require(isinstance(revision, str) and bool(GIT_SHA.fullmatch(revision)),
             "claim tested revision is invalid")
    marker = json.dumps(config, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    rendered = "%s %s" % (_claim_scalar(value), unit)
    return (
        "<!-- verify-all:start %s -->\n"
        "Current measured %s: `%s`; status `%s`; tested revision `%s`.\n"
        "<!-- verify-all:end %s -->\n"
    ) % (marker, label, rendered, status, revision, claim_id)


def validate_claims(root, receipt_path, documents, require_each=False):
    root = os.path.realpath(os.path.abspath(root))
    receipt = _read_json(os.path.realpath(os.path.abspath(receipt_path)), "verification receipt")
    _require(receipt.get("schema_version") == 1, "verification receipt schema_version must be 1")
    _require(bool(GIT_SHA.fullmatch(receipt.get("tested_sha", ""))),
             "verification receipt tested_sha is invalid")
    hashes = receipt.get("input_hashes")
    _require(isinstance(hashes, dict), "verification receipt input_hashes must be an object")
    for relative, expected in hashes.items():
        _require(isinstance(relative, str) and isinstance(expected, str) and SHA256.fullmatch(expected),
                 "verification receipt input hash entry is invalid")
        path = os.path.realpath(os.path.abspath(os.path.join(root, relative.replace("/", os.sep))))
        try:
            inside = os.path.commonpath([root, path]) == root
        except ValueError:
            inside = False
        _require(inside and os.path.isfile(path), "verification input is missing or outside root: %s" % relative)
        with open(path, "rb") as handle:
            actual = _sha256(handle.read().replace(b"\r\n", b"\n"))
        _require(actual == expected, "verification input hash is stale: %s" % relative)

    claims = []
    seen = set()
    for document in documents:
        document = os.path.realpath(os.path.abspath(document))
        _require(os.path.isfile(document), "claim document not found: %s" % document)
        try:
            with open(document, "r", encoding="utf-8") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeError) as exc:
            raise VerificationError("cannot read claim document %s: %s" % (document, exc))
        document_claims = 0
        index = 0
        while index < len(lines):
            line = lines[index]
            match = re.fullmatch(r"<!-- verify-all:start (\{.*\}) -->", line)
            if not match:
                _require(not line.startswith("<!-- verify-all:end "),
                         "claim end marker has no matching start in %s" % document)
                index += 1
                continue
            try:
                config = json.loads(match.group(1))
            except ValueError as exc:
                raise VerificationError("claim marker JSON is invalid in %s: %s" % (document, exc))
            claim_id = config.get("id") if isinstance(config, dict) else None
            _require(claim_id not in seen, "duplicate claim id: %s" % claim_id)
            _require(index + 2 < len(lines), "claim block is incomplete in %s" % document)
            expected = render_claim_block(config, receipt).splitlines()
            actual = lines[index:index + 3]
            _require(actual == expected, "claim block is stale or malformed: %s" % claim_id)
            seen.add(claim_id)
            document_claims += 1
            claims.append({
                "id": claim_id,
                "document": os.path.relpath(document, root).replace(os.sep, "/"),
                "value": _receipt_value(receipt, config["value_path"]),
                "status": _receipt_value(receipt, config["status_path"]),
                "revision": receipt["tested_sha"],
            })
            index += 3
        if require_each:
            _require(document_claims > 0, "claim document has no current marker: %s" % document)
    _require(bool(claims), "no current claim markers found")
    return claims


def atomic_json(path, value, replace=os.replace):
    path = os.path.abspath(path)
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        raise VerificationError("receipt output parent does not exist: %s" % parent)
    if os.path.islink(path):
        raise VerificationError("receipt output must not be a symlink")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="\n", dir=parent,
                prefix=".%s." % os.path.basename(path), suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        replace(temporary, path)
    except OSError as exc:
        raise VerificationError("cannot replace receipt atomically: %s" % exc)
    finally:
        if temporary and os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except OSError:
                pass


def run_verification(root, output, loader_record):
    root = os.path.realpath(os.path.abspath(root))
    output = os.path.realpath(os.path.abspath(output))
    relative_output = os.path.relpath(output, root).replace(os.sep, "/")
    provenance = git_provenance(root, [relative_output])
    plan = fixed_plan(root, sys.executable, loader_record)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["VERIFY_ALL_UPDATING_RECEIPT"] = "1"

    def runner(stage):
        if stage["kind"] == "footprint":
            return run_footprint_stage(stage, root)
        result = run_subprocess_stage(stage, root, env)
        if stage["name"] == "unit":
            result["limitations"].append(
                "real latest.json marker integration skipped during receipt replacement; rerun after publication")
        return result

    stages = execute_plan(plan, runner)
    footprint = next((stage.get("footprint") for stage in stages if stage["name"] == "footprint"), None)
    if footprint is None:
        inputs = footprint_inputs(root)
        footprint = {
            "status": "skipped",
            "recorded_revision": None,
            "descriptions": {"bytes": inputs["descriptions_bytes"], "tokens": None,
                             "sha256": inputs["catalog_sha256"]},
            "bodies": {"bytes": inputs["bodies_bytes"], "tokens": None,
                       "source_count": len(inputs["bodies"])},
            "max_lane_tokens": None,
            "lanes": {},
            "limitations": ["footprint stage was not run"],
        }
    receipt = build_receipt(
        provenance, stages, footprint, environment_info(), input_hashes(root), _utc_now())
    atomic_json(output, receipt)
    return receipt


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--out")
    parser.add_argument("--loader-record")
    parser.add_argument("--json", action="store_true")
    return parser


def run(argv=None):
    args = build_parser().parse_args(argv)
    root = os.path.realpath(os.path.abspath(args.root))
    output = args.out or os.path.join(root, "evals", "results", "latest.json")
    loader_record = args.loader_record or os.path.join(root, "evals", "loader-record.json")
    try:
        receipt = run_verification(root, output, loader_record)
    except VerificationError as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
        else:
            sys.stderr.write("verify_all: %s\n" % exc)
        return 2
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print("verification %s for %s; receipt: %s" % (
            receipt["overall_status"], receipt["tested_sha"], output))
    return {"pass": 0, "fail": 3, "unverified": 4}[receipt["overall_status"]]


if __name__ == "__main__":
    sys.exit(run())
