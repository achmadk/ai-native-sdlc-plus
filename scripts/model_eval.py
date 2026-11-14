"""Validate preregistered model-selection and paired task evaluation inputs."""

import sys

if sys.version_info < (3, 8):
    sys.exit("model_eval requires Python >= 3.8")
sys.dont_write_bytecode = True

import argparse
import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import time


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(HERE)
PRODUCT_SKILLS = {
    "ai-readiness-and-metrics",
    "ai-sdlc",
    "autonomy-policy",
    "context-pack",
    "decision-trace",
    "learning-mode",
    "review-by-intent",
    "ship-and-observe",
    "spec-first",
    "verify-and-evals",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_PROVIDER_ARGS = 64
MAX_PROVIDER_ARG_BYTES = 4096
DEFAULT_PROVIDER_TIMEOUT = 60
SAFE_ENV_NAMES = (
    "COMSPEC", "HOME", "LANG", "LC_ALL", "PATH", "PATHEXT", "SYSTEMROOT",
    "TEMP", "TMP", "TMPDIR", "WINDIR",
)
SECRET_NAME = re.compile(r"(?:credential|key|password|secret|token)", re.I)
SECRET_PATTERNS = (
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("URL with embedded credentials", re.compile(r"://[^/\s:@]+:[^/\s@]+@")),
    ("credential assignment", re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*[\"']?[^\s\"']{8,}")),
)


class RegistrationError(ValueError):
    pass


class EvaluationError(ValueError):
    pass


def _reject_constant(value):
    raise ValueError("non-finite JSON number: %s" % value)


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _file_sha256(path):
    with open(path, "rb") as handle:
        return _sha256(handle.read().replace(b"\r\n", b"\n"))


def _inside(root, path, label):
    root = os.path.realpath(os.path.abspath(root))
    path = os.path.realpath(os.path.abspath(path))
    try:
        inside = os.path.commonpath([root, path]) == root
    except ValueError:
        inside = False
    if not inside:
        raise RegistrationError("%s escapes repository root: %s" % (label, path))
    return path


def _load_json(root, path, label):
    path = _inside(root, path, label)
    if not os.path.isfile(path):
        raise RegistrationError("%s not found: %s" % (label, path))
    size = os.path.getsize(path)
    if size <= 0 or size > MAX_JSON_BYTES:
        raise RegistrationError("%s size must be 1..%d bytes" % (label, MAX_JSON_BYTES))
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle, parse_constant=_reject_constant)
    except (OSError, UnicodeError, ValueError) as exc:
        raise RegistrationError("cannot read %s: %s" % (label, exc))
    if not isinstance(data, dict):
        raise RegistrationError("%s root must be an object" % label)
    return data, path


def _require(condition, message):
    if not condition:
        raise RegistrationError(message)


def _positive_number(value, label, integer=False):
    valid_type = isinstance(value, int) if integer else isinstance(value, (int, float)) and not isinstance(value, bool)
    _require(valid_type and value > 0 and math.isfinite(value), "%s must be a positive finite number" % label)


def _unique_objects(items, label):
    _require(isinstance(items, list) and items, "%s must be a non-empty array" % label)
    ids = []
    for item in items:
        _require(isinstance(item, dict), "%s entries must be objects" % label)
        item_id = item.get("id")
        _require(isinstance(item_id, str) and item_id, "%s entries require an id" % label)
        ids.append(item_id)
    _require(len(ids) == len(set(ids)), "%s ids must be unique" % label)
    return items


def _git_blob(root, revision, path):
    _require(bool(GIT_SHA.fullmatch(revision or "")), "product catalog captured_revision must be a 40-character Git SHA")
    result = subprocess.run(
        ["git", "-C", root, "show", "%s:%s" % (revision, path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    if result.returncode != 0:
        raise RegistrationError("cannot resolve %s:%s: %s" % (
            revision,
            path,
            result.stderr.decode("utf-8", "replace").strip(),
        ))
    return result.stdout


def validate_product_catalog(root, data):
    _require(data.get("version") == 1, "product catalog version must be 1")
    revision = data.get("captured_revision")
    skills = _unique_objects(data.get("skills"), "product catalog skills")
    _require({item["id"] for item in skills} == PRODUCT_SKILLS, "product catalog must contain the ten product skills")
    for item in skills:
        skill = item["id"]
        path = "skills/%s/SKILL.md" % skill
        _require(item.get("source_path") == path, "%s source_path must be %s" % (skill, path))
        _require(isinstance(item.get("description"), str) and item["description"], "%s requires a description" % skill)
        _require(bool(SHA256.fullmatch(item.get("source_sha256", ""))), "%s source_sha256 is invalid" % skill)
        blob = _git_blob(root, revision, path)
        _require(_sha256(blob) == item["source_sha256"], "%s source hash does not match baseline revision" % skill)
        try:
            text = blob.decode("utf-8")
        except UnicodeError as exc:
            raise RegistrationError("%s is not UTF-8: %s" % (path, exc))
        match = re.match(r'^---\nname: (\S+)\ndescription: "(.*)"\n---\n', text, re.S)
        _require(match is not None, "%s frontmatter is invalid" % path)
        _require((match.group(1), match.group(2)) == (skill, item["description"]),
                 "%s snapshot does not match baseline frontmatter" % skill)
    return {item["id"] for item in skills}


def validate_external_catalog(data):
    _require(data.get("version") == 1, "external catalog version must be 1")
    skills = _unique_objects(data.get("skills"), "external catalog skills")
    _require({item.get("family") for item in skills} == {"OpenSpec", "Superpowers"},
             "external catalog must contain OpenSpec and Superpowers entries")
    for item in skills:
        item_id = item["id"]
        _require(bool(re.fullmatch(r"(?:openspec|superpowers)/[a-z0-9-]+", item_id)),
                 "%s must use a namespaced id" % item_id)
        description = item.get("description")
        _require(isinstance(description, str) and 0 < len(description) <= 1024,
                 "%s description must contain at most 1024 characters" % item_id)
        _require(isinstance(item.get("source_url"), str) and item["source_url"].startswith("https://"),
                 "%s source_url must use HTTPS" % item_id)
        revision = item.get("source_revision", "")
        _require(isinstance(revision, str) and revision.lower() not in ("", "head", "main", "master", "latest"),
                 "%s source_revision must be immutable" % item_id)
        _require(isinstance(item.get("license"), str) and item["license"], "%s requires license provenance" % item_id)
        _require(_sha256(description.encode("utf-8")) == item.get("description_sha256"),
                 "%s description hash does not match" % item_id)
        _require("source_path" not in item, "%s must remain external catalog data" % item_id)
    return {item["id"] for item in skills}


def _limits(protocol, label):
    _require(isinstance(protocol, dict), "%s protocol must be an object" % label)
    _positive_number(protocol.get("repetitions"), "%s repetitions" % label, integer=True)
    _require(protocol["repetitions"] >= 3, "%s repetitions must be at least 3" % label)
    limits = protocol.get("limits")
    _require(isinstance(limits, dict), "%s limits must be an object" % label)
    _positive_number(limits.get("requests"), "%s request limit" % label, integer=True)
    _positive_number(limits.get("input_tokens"), "%s input token limit" % label, integer=True)
    _positive_number(limits.get("cost_usd"), "%s cost limit" % label)


def validate_selection(root, data, path, product_path, external_path, catalog_ids):
    _require(data.get("version") == 1, "selection registration version must be 1")
    _require(bool(re.fullmatch(r"real-evals-selection-v[0-9]+", data.get("registration_id", ""))),
             "selection registration_id is invalid")
    _limits(data.get("protocol"), "selection")
    criteria = data.get("pass_criteria")
    _require(isinstance(criteria, dict), "selection pass_criteria must be an object")
    for key in ("precision_min", "recall_min"):
        value = criteria.get(key)
        _require(isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1,
                 "selection %s must be between 0 and 1" % key)
    catalogs = data.get("catalogs")
    _require(isinstance(catalogs, dict), "selection catalogs must be an object")
    for name, expected_path, actual_path in (
        ("product", "evals/catalogs/product-baseline.json", product_path),
        ("external", "evals/catalogs/external-distractors.json", external_path),
    ):
        ref = catalogs.get(name)
        _require(isinstance(ref, dict) and ref.get("path") == expected_path,
                 "selection %s catalog path is invalid" % name)
        actual_hash = _file_sha256(actual_path)
        _require(ref.get("sha256") == actual_hash,
                 "selection %s catalog hash does not match" % name)

    cases = _unique_objects(data.get("cases"), "selection cases")
    _require(len(cases) >= 60, "selection registration requires at least 60 cases")
    prompts = [item.get("prompt", "").strip().casefold() for item in cases]
    _require(all(len(prompt) >= 12 for prompt in prompts), "selection prompts must contain at least 12 characters")
    _require(len(prompts) == len(set(prompts)), "selection prompts must be unique")
    for skill in PRODUCT_SKILLS:
        for kind in ("should_trigger", "near_miss"):
            scoped = [item for item in cases if item.get("target_skill") == skill and item.get("kind") == kind]
            _require(len(scoped) >= 3, "%s requires three %s cases" % (skill, kind))
            _require({item.get("split") for item in scoped} == {"development", "held_out"},
                     "%s %s cases must cover both splits" % (skill, kind))
    for item in cases:
        _require(item.get("target_skill") in PRODUCT_SKILLS, "%s target_skill is invalid" % item["id"])
        _require(item.get("kind") in ("should_trigger", "near_miss"), "%s kind is invalid" % item["id"])
        _require(item.get("split") in ("development", "held_out"), "%s split is invalid" % item["id"])
        labels = []
        for key in ("expected", "allowed", "forbidden"):
            value = item.get(key)
            _require(isinstance(value, list) and len(value) == len(set(value)), "%s %s labels are invalid" % (item["id"], key))
            _require(set(value) <= catalog_ids, "%s %s labels reference unknown skills" % (item["id"], key))
            labels.append(set(value))
        _require(not (labels[0] & labels[1] or labels[0] & labels[2] or labels[1] & labels[2]),
                 "%s label sets must be disjoint" % item["id"])
        _require(any(labels), "%s must have at least one selection label" % item["id"])
        if item["kind"] == "should_trigger":
            _require(item["target_skill"] in labels[0], "%s must expect its target skill" % item["id"])
        else:
            _require(item["target_skill"] in labels[2], "%s must forbid its target skill" % item["id"])


def validate_tasks(data):
    _require(data.get("version") == 1, "task registration version must be 1")
    _require(bool(re.fullmatch(r"real-evals-tasks-v[0-9]+", data.get("registration_id", ""))),
             "task registration_id is invalid")
    protocol = data.get("protocol")
    _limits(protocol, "task")
    _require(set(protocol.get("conditions", [])) == {"baseline", "with_skill"},
             "task conditions must be baseline and with_skill")
    _require(protocol.get("randomize_condition_order") is True, "task condition order must be randomized")
    cases = _unique_objects(data.get("cases"), "task cases")
    _require(len(cases) == 30, "task registration requires exactly 30 cases")
    _require({item.get("skill") for item in cases} == PRODUCT_SKILLS, "task cases must cover every product skill")
    for skill in PRODUCT_SKILLS:
        roles = {item.get("role") for item in cases if item.get("skill") == skill}
        _require(roles == {"leader", "ic", "edge"}, "%s task cases must cover leader, ic, and edge" % skill)
    for item in cases:
        _require(isinstance(item.get("prompt"), str) and len(item["prompt"].strip()) >= 12,
                 "%s prompt is too short" % item["id"])
        assertions = _unique_objects(item.get("assertions"), "%s assertions" % item["id"])
        _require(len(assertions) >= 2, "%s requires at least two assertions" % item["id"])
        encoded = json.dumps(assertions, sort_keys=True).lower()
        _require("baseline" not in encoded and "with_skill" not in encoded,
                 "%s assertions must be condition-independent" % item["id"])
        for assertion in assertions:
            _require(assertion.get("kind") in ("contains_all", "contains_any", "excludes_all", "json_fields"),
                     "%s assertion %s kind is invalid" % (item["id"], assertion["id"]))
            _require(isinstance(assertion.get("values"), list) and assertion["values"],
                     "%s assertion %s requires values" % (item["id"], assertion["id"]))


def _load_bundle(root, args):
    root = os.path.realpath(os.path.abspath(root))
    product, product_path = _load_json(root, args.product_catalog, "product catalog")
    external, external_path = _load_json(root, args.external_catalog, "external catalog")
    product_ids = validate_product_catalog(root, product)
    external_ids = validate_external_catalog(external)
    selection, selection_path = _load_json(root, args.selection, "selection registration")
    tasks, tasks_path = _load_json(root, args.tasks, "task registration")
    validate_selection(root, selection, selection_path, product_path, external_path, product_ids | external_ids)
    validate_tasks(tasks)
    return {
        "root": root,
        "product": product,
        "product_path": product_path,
        "external": external,
        "external_path": external_path,
        "selection": selection,
        "selection_path": selection_path,
        "tasks": tasks,
        "tasks_path": tasks_path,
        "product_ids": product_ids,
        "external_ids": external_ids,
    }


def validate_all(root, args):
    bundle = _load_bundle(root, args)
    return {
        "status": "valid",
        "registration_ids": [bundle["selection"]["registration_id"], bundle["tasks"]["registration_id"]],
        "selection_cases": len(bundle["selection"]["cases"]),
        "task_cases": len(bundle["tasks"]["cases"]),
        "product_skills": len(bundle["product_ids"]),
        "external_skills": len(bundle["external_ids"]),
    }


def _eval_require(condition, message):
    if not condition:
        raise EvaluationError(message)


def _utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json_path(path, label, max_bytes=MAX_JSON_BYTES):
    path = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(path):
        raise EvaluationError("%s not found: %s" % (label, path))
    size = os.path.getsize(path)
    if size <= 0 or size > max_bytes:
        raise EvaluationError("%s size must be 1..%d bytes" % (label, max_bytes))
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle, parse_constant=_reject_constant)
    except (OSError, UnicodeError, ValueError) as exc:
        raise EvaluationError("cannot read %s JSON: %s" % (label, exc))
    if not isinstance(data, dict):
        raise EvaluationError("%s root must be an object" % label)
    return data


def _git_command(root, argv, label):
    result = subprocess.run(
        ["git", "-C", root] + list(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    )
    if result.returncode != 0:
        raise EvaluationError("%s: %s" % (label, result.stderr.decode("utf-8", "replace").strip()))
    return result.stdout


def _resolve_commit(root, value, label):
    _eval_require(bool(GIT_SHA.fullmatch(value or "")), "%s must be a full 40-character Git SHA" % label)
    resolved = _git_command(root, ["rev-parse", "--verify", "%s^{commit}" % value], label).decode("ascii").strip()
    _eval_require(resolved == value, "%s must resolve exactly" % label)
    return resolved


def _verify_frozen_inputs(bundle, registration_commit, recorded_revision):
    root = bundle["root"]
    registration_commit = _resolve_commit(root, registration_commit, "registration commit")
    recorded_revision = _resolve_commit(root, recorded_revision, "recorded revision")
    ancestor = subprocess.run(
        ["git", "-C", root, "merge-base", "--is-ancestor", registration_commit, recorded_revision],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    )
    _eval_require(ancestor.returncode == 0, "recorded revision does not descend from registration commit")
    blobs = {}
    for label, path in (
        ("selection registration", bundle["selection_path"]),
        ("task registration", bundle["tasks_path"]),
        ("product catalog", bundle["product_path"]),
        ("external catalog", bundle["external_path"]),
    ):
        relative = os.path.relpath(path, root).replace(os.sep, "/")
        blob = _git_command(root, ["show", "%s:%s" % (registration_commit, relative)],
                            "cannot resolve frozen %s" % label)
        current_hash = _file_sha256(path)
        blob_hash = _sha256(blob.replace(b"\r\n", b"\n"))
        _eval_require(current_hash == blob_hash, "%s hash differs from registration commit" % label)
        blobs[label] = blob_hash
    return registration_commit, recorded_revision, blobs


def _skill_description(blob, path):
    try:
        text = blob.decode("utf-8")
    except UnicodeError as exc:
        raise EvaluationError("%s is not UTF-8: %s" % (path, exc))
    match = re.match(r'^---\nname: (\S+)\ndescription: "(.*)"\n---\n', text, re.S)
    _eval_require(match is not None, "%s frontmatter is invalid" % path)
    return match.group(1), match.group(2)


def _selection_catalog(bundle, catalog_id="baseline", revision=None):
    _eval_require(catalog_id in ("baseline", "candidate"), "selection catalog id is invalid")
    skills = []
    sources = []
    if catalog_id == "baseline":
        product = [
            (item["id"], item["description"], item["source_sha256"])
            for item in bundle["product"]["skills"]
        ]
    else:
        _eval_require(bool(revision), "candidate catalog requires a recorded revision")
        product = []
        for skill_id in sorted(PRODUCT_SKILLS):
            path = "skills/%s/SKILL.md" % skill_id
            blob = _git_command(bundle["root"], ["show", "%s:%s" % (revision, path)],
                                "cannot resolve candidate skill")
            name, description = _skill_description(blob, path)
            _eval_require(name == skill_id, "%s name does not match its directory" % path)
            product.append((skill_id, description, _sha256(blob.replace(b"\r\n", b"\n"))))
    for skill_id, description, source_hash in product:
        skills.append({
            "id": skill_id,
            "family": "AI-native SDLC+",
            "description": description,
        })
        sources.append({"id": skill_id, "sha256": source_hash})
    for item in bundle["external"]["skills"]:
        skills.append({
            "id": item["id"],
            "family": item["family"],
            "description": item["description"],
        })
        sources.append({"id": item["id"], "sha256": item["description_sha256"]})
    skills.sort(key=lambda item: item["id"])
    sources.sort(key=lambda item: item["id"])
    return {
        "id": catalog_id,
        "sha256": _sha256(_canonical_json(skills)),
        "source_sha256": _sha256(_canonical_json(sources)),
        "skill_count": len(skills),
        "skills": skills,
    }


def _provider_configuration():
    raw = os.environ.get("SDLC_EVAL_PROVIDER_CMD", "")
    try:
        argv = json.loads(raw, parse_constant=_reject_constant)
    except (TypeError, ValueError) as exc:
        raise EvaluationError("provider command must be a valid JSON argv array: %s" % exc)
    _eval_require(isinstance(argv, list) and argv, "provider command must be a non-empty JSON argv array")
    _eval_require(len(argv) <= MAX_PROVIDER_ARGS, "provider command has too many argv entries")
    for arg in argv:
        _eval_require(isinstance(arg, str) and arg and "\x00" not in arg,
                      "provider command argv entries must be non-empty strings")
        _eval_require(len(arg.encode("utf-8")) <= MAX_PROVIDER_ARG_BYTES,
                      "provider command argv entry is too large")

    explicit = []
    raw_names = os.environ.get("SDLC_EVAL_PROVIDER_ENV", "")
    for name in raw_names.split(","):
        name = name.strip()
        if not name:
            continue
        _eval_require(bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)),
                      "provider environment name is invalid: %s" % name)
        _eval_require(name not in explicit, "provider environment names must be unique")
        explicit.append(name)
    child_env = {}
    for name in SAFE_ENV_NAMES:
        if name in os.environ:
            child_env[name] = os.environ[name]
    for name in explicit:
        if name in os.environ:
            child_env[name] = os.environ[name]
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"
    credential_values = [
        os.environ[name]
        for name in explicit
        if name in os.environ and SECRET_NAME.search(name) and len(os.environ[name]) >= 8
    ]
    return argv, child_env, sorted(explicit), credential_values


def _scan_provider_output(raw, credential_values):
    text = raw.decode("utf-8", "replace")
    for value in credential_values:
        if value in text:
            raise EvaluationError("provider response contains an explicitly configured secret")
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise EvaluationError("provider response contains a possible secret (%s)" % label)


def _provider_response(request, argv, child_env, credential_values, max_bytes, timeout, catalog_ids=None):
    started = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            input=_canonical_json(request) + b"\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=child_env,
            shell=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EvaluationError("provider process failed: %s" % exc)
    duration_ms = round((time.monotonic() - started) * 1000, 3)
    if len(result.stdout) > max_bytes:
        raise EvaluationError("provider response exceeds %d bytes" % max_bytes)
    if len(result.stderr) > max_bytes:
        raise EvaluationError("provider stderr exceeds %d bytes" % max_bytes)
    _scan_provider_output(result.stdout + b"\n" + result.stderr, credential_values)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        if len(detail) > 1000:
            detail = detail[-1000:]
        suffix = ": %s" % detail if detail else ""
        raise EvaluationError("provider process exited with status %d%s" % (result.returncode, suffix))
    try:
        response = json.loads(result.stdout.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeError, ValueError) as exc:
        raise EvaluationError("provider response is not valid JSON: %s" % exc)
    _eval_require(isinstance(response, dict), "provider response must be a JSON object")
    _eval_require(response.get("version") == 1, "provider response version must be 1")
    provider = response.get("provider")
    model = response.get("model")
    _eval_require(isinstance(provider, str) and 0 < len(provider) <= 200, "provider response requires provider identity")
    _eval_require(isinstance(model, str) and 0 < len(model) <= 200, "provider response requires model identity")
    usage = response.get("usage")
    _eval_require(isinstance(usage, dict), "provider response requires usage")
    for key in ("input_tokens", "output_tokens"):
        value = usage.get(key)
        _eval_require(isinstance(value, int) and not isinstance(value, bool) and value >= 0,
                      "provider usage %s must be a nonnegative integer" % key)
    cost = usage.get("cost_usd")
    if cost is not None:
        _eval_require(isinstance(cost, (int, float)) and not isinstance(cost, bool) and
                      math.isfinite(cost) and cost >= 0,
                      "provider usage cost_usd must be a nonnegative finite number")
        cost = float(cost)
    normalized = {
        "provider": provider,
        "model": model,
        "duration_ms": duration_ms,
        "usage": {
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "cost_usd": cost,
        },
    }
    if request.get("kind") == "selection":
        selected = response.get("selected")
        _eval_require(isinstance(selected, list) and len(selected) == len(set(selected)),
                      "provider selected must be an array of unique skill IDs")
        _eval_require(all(isinstance(item, str) and item in catalog_ids for item in selected),
                      "provider selected an unknown skill ID")
        normalized["selected"] = sorted(selected)
    elif request.get("kind") == "task":
        task_response = response.get("response")
        _eval_require(isinstance(task_response, str) and task_response.strip(),
                      "provider task response must be non-empty text")
        _eval_require(len(task_response.encode("utf-8")) <= max_bytes,
                      "provider task response exceeds %d bytes" % max_bytes)
        normalized["response"] = task_response
    else:
        raise EvaluationError("provider request kind is unsupported")
    return normalized


def _money(value, label, allow_zero=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise EvaluationError("%s must be a decimal number" % label)
    minimum_ok = result >= 0 if allow_zero else result > 0
    _eval_require(result.is_finite() and minimum_ok,
                  "%s must be %s and finite" % (label, "nonnegative" if allow_zero else "positive"))
    return result


def _selection_request(case, repeat, catalog):
    return {
        "version": 1,
        "kind": "selection",
        "case_id": case["id"],
        "split": case["split"],
        "repeat": repeat,
        "prompt": case["prompt"],
        "catalog": {
            "id": catalog["id"],
            "sha256": catalog["sha256"],
            "skills": catalog["skills"],
        },
        "response_schema": {
            "version": 1,
            "selected": "array of zero or more catalog skill IDs",
            "usage": "input_tokens, output_tokens, and cost_usd",
        },
    }


def _score_selection(case, selected):
    selected = set(selected)
    expected = set(case["expected"])
    allowed = set(case["allowed"])
    forbidden = set(case["forbidden"])
    missing = sorted(expected - selected)
    forbidden_selected = sorted(forbidden & selected)
    unexpected = sorted(selected - expected - allowed - forbidden)
    passed = not missing and not forbidden_selected and not unexpected
    return {
        "status": "pass" if passed else "fail",
        "missing_expected": missing,
        "forbidden_selected": forbidden_selected,
        "unexpected_selected": unexpected,
    }


def _selection_summary(cases, records, criteria):
    by_id = {case["id"]: case for case in cases}
    by_skill = {}
    by_split = {}
    passed = 0
    forbidden_count = 0
    for record in records:
        case = by_id[record["case_id"]]
        outcome = record["outcome"]
        if outcome["status"] == "pass":
            passed += 1
        forbidden_count += len(outcome["forbidden_selected"])
        split = by_split.setdefault(case["split"], {"passed": 0, "failed": 0})
        split["passed" if outcome["status"] == "pass" else "failed"] += 1
        metrics = by_skill.setdefault(case["target_skill"], {"tp": 0, "fn": 0, "tn": 0, "fp": 0})
        target_selected = case["target_skill"] in record["selected"]
        if case["kind"] == "should_trigger":
            metrics["tp" if target_selected else "fn"] += 1
        else:
            metrics["fp" if target_selected else "tn"] += 1
    aggregate = {"tp": 0, "fn": 0, "tn": 0, "fp": 0}
    for metrics in by_skill.values():
        for key in aggregate:
            aggregate[key] += metrics[key]
        precision_denominator = metrics["tp"] + metrics["fp"]
        recall_denominator = metrics["tp"] + metrics["fn"]
        metrics["precision"] = metrics["tp"] / precision_denominator if precision_denominator else 1.0
        metrics["recall"] = metrics["tp"] / recall_denominator if recall_denominator else 1.0
    precision_denominator = aggregate["tp"] + aggregate["fp"]
    recall_denominator = aggregate["tp"] + aggregate["fn"]
    aggregate["precision"] = aggregate["tp"] / precision_denominator if precision_denominator else 1.0
    aggregate["recall"] = aggregate["tp"] / recall_denominator if recall_denominator else 1.0
    failed = len(records) - passed
    verdict = (
        failed == 0 and
        aggregate["precision"] >= criteria["precision_min"] and
        aggregate["recall"] >= criteria["recall_min"]
    )
    return {
        "records": len(records),
        "passed_records": passed,
        "failed_records": failed,
        "forbidden_selections": forbidden_count,
        "aggregate": aggregate,
        "by_skill": dict(sorted(by_skill.items())),
        "by_split": dict(sorted(by_split.items())),
        "verdict": "pass" if verdict else "fail",
    }


def _atomic_json(path, value):
    path = os.path.abspath(path)
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        raise EvaluationError("transcript output parent does not exist: %s" % parent)
    if os.path.islink(path):
        raise EvaluationError("transcript output must not be a symlink")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="\n", dir=parent,
                prefix=".%s." % os.path.basename(path), suffix=".tmp", delete=False) as handle:
            temp_path = handle.name
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except OSError as exc:
        raise EvaluationError("cannot write transcript atomically: %s" % exc)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _atomic_text(path, value):
    path = os.path.abspath(path)
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        raise EvaluationError("report output parent does not exist: %s" % parent)
    if os.path.islink(path):
        raise EvaluationError("report output must not be a symlink")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="\n", dir=parent,
                prefix=".%s." % os.path.basename(path), suffix=".tmp", delete=False) as handle:
            temp_path = handle.name
            handle.write(value.rstrip() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except OSError as exc:
        raise EvaluationError("cannot write report atomically: %s" % exc)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _build_selection_transcript(bundle, args, catalog, cases, records, registration_commit,
                                recorded_revision, registration_hash, environment_names,
                                status, cost_status):
    providers = sorted({record["provider"] for record in records})
    models = sorted({record["model"] for record in records})
    summary = _selection_summary(cases, records, bundle["selection"]["pass_criteria"])
    if status != "complete":
        summary["verdict"] = "unverified"
    return {
        "version": 1,
        "kind": "selection",
        "mode": "record",
        "status": status,
        "cost_status": cost_status,
        "registration_id": bundle["selection"]["registration_id"],
        "registration_commit": registration_commit,
        "registration_sha256": registration_hash,
        "recorded_revision": recorded_revision,
        "recorded_at": _utc_timestamp(),
        "catalog": {
            "id": catalog["id"],
            "sha256": catalog["sha256"],
            "source_sha256": catalog["source_sha256"],
            "skill_count": catalog["skill_count"],
        },
        "case_ids": [case["id"] for case in cases],
        "repetitions": bundle["selection"]["protocol"]["repetitions"],
        "provider": providers[0] if len(providers) == 1 else providers,
        "model": models[0] if len(models) == 1 else models,
        "provider_environment_names": environment_names,
        "records": records,
        "summary": summary,
    }


def record_selection(bundle, args):
    registration_commit, recorded_revision, frozen = _verify_frozen_inputs(
        bundle, args.registration_commit, args.recorded_revision)
    catalog = _selection_catalog(bundle, args.catalog, recorded_revision)
    catalog_ids = {item["id"] for item in catalog["skills"]}
    cases = bundle["selection"]["cases"]
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        _eval_require(bool(cases), "selection case not found: %s" % args.case)
    elif args.split != "all":
        cases = [case for case in cases if case["split"] == args.split]
    _eval_require(bool(cases), "no selection cases matched the requested scope")

    protocol = bundle["selection"]["protocol"]
    registered_request_cap = protocol["limits"]["requests"]
    request_cap = args.request_cap if args.request_cap is not None else registered_request_cap
    _eval_require(isinstance(request_cap, int) and 0 < request_cap <= registered_request_cap,
                  "request cap must be positive and no greater than the registration")
    registered_cost_cap = _money(protocol["limits"]["cost_usd"], "registered cost cap")
    cost_cap = _money(args.cost_cap, "cost cap") if args.cost_cap is not None else registered_cost_cap
    _eval_require(cost_cap <= registered_cost_cap, "cost cap must not exceed the registration")
    max_request_cost = _money(args.max_request_cost, "maximum request cost")
    _eval_require(max_request_cost <= cost_cap, "maximum request cost must not exceed the cost cap")
    _eval_require(isinstance(args.max_response_bytes, int) and 0 < args.max_response_bytes <= MAX_JSON_BYTES,
                  "maximum provider response must be 1..%d bytes" % MAX_JSON_BYTES)
    _eval_require(isinstance(args.provider_timeout, int) and 0 < args.provider_timeout <= 600,
                  "provider timeout must be 1..600 seconds")

    argv, child_env, environment_names, credential_values = _provider_configuration()
    records = []
    spent = Decimal("0")
    input_tokens = 0
    provider_identity = None
    repeats = protocol["repetitions"]
    registration_hash = frozen["selection registration"]
    for case in cases:
        for repeat in range(1, repeats + 1):
            if len(records) >= request_cap:
                raise EvaluationError("request cap would be exceeded before repeat %d" % repeat)
            if spent + max_request_cost > cost_cap:
                raise EvaluationError("cost cap would be exceeded before repeat %d" % repeat)
            request = _selection_request(case, repeat, catalog)
            response = _provider_response(
                request, argv, child_env, credential_values, args.max_response_bytes,
                args.provider_timeout, catalog_ids)
            identity = (response["provider"], response["model"])
            if provider_identity is None:
                provider_identity = identity
            _eval_require(identity == provider_identity, "provider or model identity changed during recording")
            input_tokens += response["usage"]["input_tokens"]
            _eval_require(input_tokens <= protocol["limits"]["input_tokens"],
                          "input token cap was exceeded")
            cost = response["usage"]["cost_usd"]
            outcome = _score_selection(case, response["selected"])
            record = {
                "case_id": case["id"],
                "split": case["split"],
                "repeat": repeat,
                "request_sha256": _sha256(_canonical_json(request)),
                "catalog_sha256": catalog["sha256"],
                "registration_sha256": registration_hash,
                "provider": response["provider"],
                "model": response["model"],
                "selected": response["selected"],
                "usage": response["usage"],
                "outcome": outcome,
            }
            records.append(record)
            if cost is None:
                transcript = _build_selection_transcript(
                    bundle, args, catalog, cases, records, registration_commit,
                    recorded_revision, registration_hash, environment_names,
                    "incomplete", "unverified")
                _atomic_json(args.out, transcript)
                return transcript, 4
            actual_cost = _money(cost, "provider request cost", allow_zero=True)
            _eval_require(actual_cost <= max_request_cost,
                          "provider request cost exceeded the declared maximum")
            spent += actual_cost
            _eval_require(spent <= cost_cap, "provider cost cap was exceeded")

    transcript = _build_selection_transcript(
        bundle, args, catalog, cases, records, registration_commit,
        recorded_revision, registration_hash, environment_names, "complete", "verified")
    _atomic_json(args.out, transcript)
    return transcript, 0


def _catalog_condition_order(case_id, repeat):
    seed = int(_sha256((case_id + ":catalog-order").encode("utf-8"))[:8], 16) % 2
    first = (seed + repeat - 1) % 2
    catalogs = ["baseline", "candidate"]
    return [catalogs[first], catalogs[1 - first]]


def _selection_comparison(cases, records, criteria):
    summaries = {
        catalog_id: _selection_summary(
            cases, [record for record in records if record["catalog_id"] == catalog_id], criteria)
        for catalog_id in ("baseline", "candidate")
    }
    changed = []
    regressions = []
    for case in cases:
        counts = {}
        for catalog_id in ("baseline", "candidate"):
            counts[catalog_id] = sum(
                record["outcome"]["status"] == "pass"
                for record in records
                if record["case_id"] == case["id"] and record["catalog_id"] == catalog_id)
        delta = counts["candidate"] - counts["baseline"]
        if delta:
            item = {
                "case_id": case["id"],
                "baseline_passed": counts["baseline"],
                "candidate_passed": counts["candidate"],
                "delta": delta,
            }
            changed.append(item)
            if delta < 0:
                regressions.append(item)
    comparison = {
        "passed_record_delta": (
            summaries["candidate"]["passed_records"] - summaries["baseline"]["passed_records"]),
        "changed_cases": changed,
        "regressions": regressions,
        "verdict": "pass" if summaries["candidate"]["verdict"] == "pass" and not regressions else "fail",
    }
    return summaries, comparison


def _build_selection_comparison_transcript(bundle, catalogs, cases, records,
                                           registration_commit, recorded_revision,
                                           registration_hash, environment_names,
                                           status, cost_status):
    summaries, comparison = _selection_comparison(
        cases, records, bundle["selection"]["pass_criteria"])
    if status != "complete":
        comparison["verdict"] = "unverified"
    providers = sorted({record["provider"] for record in records})
    models = sorted({record["model"] for record in records})
    return {
        "version": 1,
        "kind": "selection-comparison",
        "mode": "record",
        "status": status,
        "cost_status": cost_status,
        "registration_id": bundle["selection"]["registration_id"],
        "registration_commit": registration_commit,
        "registration_sha256": registration_hash,
        "recorded_revision": recorded_revision,
        "recorded_at": _utc_timestamp(),
        "catalogs": {
            catalog_id: {
                "id": catalog["id"],
                "sha256": catalog["sha256"],
                "source_sha256": catalog["source_sha256"],
                "skill_count": catalog["skill_count"],
            }
            for catalog_id, catalog in sorted(catalogs.items())
        },
        "case_ids": [case["id"] for case in cases],
        "repetitions": bundle["selection"]["protocol"]["repetitions"],
        "provider": providers[0] if len(providers) == 1 else providers,
        "model": models[0] if len(models) == 1 else models,
        "provider_environment_names": environment_names,
        "records": records,
        "summaries": summaries,
        "comparison": comparison,
    }


def record_selection_comparison(bundle, args):
    registration_commit, recorded_revision, frozen = _verify_frozen_inputs(
        bundle, args.registration_commit, args.recorded_revision)
    catalogs = {
        "baseline": _selection_catalog(bundle, "baseline", recorded_revision),
        "candidate": _selection_catalog(bundle, "candidate", recorded_revision),
    }
    catalog_ids = {item["id"] for item in catalogs["baseline"]["skills"]}
    _eval_require(catalog_ids == {item["id"] for item in catalogs["candidate"]["skills"]},
                  "paired catalogs must contain the same skill IDs")
    cases = bundle["selection"]["cases"]
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        _eval_require(bool(cases), "selection case not found: %s" % args.case)
    elif args.split != "all":
        cases = [case for case in cases if case["split"] == args.split]
    _eval_require(bool(cases), "no selection cases matched the requested scope")

    protocol = bundle["selection"]["protocol"]
    registered_request_cap = protocol["limits"]["requests"]
    request_cap = args.request_cap if args.request_cap is not None else registered_request_cap
    _eval_require(isinstance(request_cap, int) and 0 < request_cap <= registered_request_cap,
                  "request cap must be positive and no greater than the registration")
    registered_cost_cap = _money(protocol["limits"]["cost_usd"], "registered cost cap")
    cost_cap = _money(args.cost_cap, "cost cap") if args.cost_cap is not None else registered_cost_cap
    _eval_require(cost_cap <= registered_cost_cap, "cost cap must not exceed the registration")
    max_request_cost = _money(args.max_request_cost, "maximum request cost")
    _eval_require(max_request_cost <= cost_cap, "maximum request cost must not exceed the cost cap")
    _eval_require(isinstance(args.max_response_bytes, int) and 0 < args.max_response_bytes <= MAX_JSON_BYTES,
                  "maximum provider response must be 1..%d bytes" % MAX_JSON_BYTES)
    _eval_require(isinstance(args.provider_timeout, int) and 0 < args.provider_timeout <= 600,
                  "provider timeout must be 1..600 seconds")

    argv, child_env, environment_names, credential_values = _provider_configuration()
    records = []
    spent = Decimal("0")
    input_tokens = 0
    provider_identity = None
    repetitions = protocol["repetitions"]
    registration_hash = frozen["selection registration"]
    for case in cases:
        for repeat in range(1, repetitions + 1):
            for order_index, catalog_id in enumerate(_catalog_condition_order(case["id"], repeat), 1):
                if len(records) >= request_cap:
                    raise EvaluationError("request cap would be exceeded before comparison repeat %d" % repeat)
                if spent + max_request_cost > cost_cap:
                    raise EvaluationError("cost cap would be exceeded before comparison repeat %d" % repeat)
                catalog = catalogs[catalog_id]
                request = _selection_request(case, repeat, catalog)
                response = _provider_response(
                    request, argv, child_env, credential_values, args.max_response_bytes,
                    args.provider_timeout, catalog_ids)
                identity = (response["provider"], response["model"])
                if provider_identity is None:
                    provider_identity = identity
                _eval_require(identity == provider_identity, "provider or model identity changed during recording")
                input_tokens += response["usage"]["input_tokens"]
                _eval_require(input_tokens <= protocol["limits"]["input_tokens"],
                              "input token cap was exceeded")
                record = {
                    "case_id": case["id"],
                    "split": case["split"],
                    "repeat": repeat,
                    "catalog_id": catalog_id,
                    "order_index": order_index,
                    "request_sha256": _sha256(_canonical_json(request)),
                    "catalog_sha256": catalog["sha256"],
                    "registration_sha256": registration_hash,
                    "provider": response["provider"],
                    "model": response["model"],
                    "selected": response["selected"],
                    "usage": response["usage"],
                    "outcome": _score_selection(case, response["selected"]),
                }
                records.append(record)
                cost = response["usage"]["cost_usd"]
                if cost is None:
                    transcript = _build_selection_comparison_transcript(
                        bundle, catalogs, cases, records, registration_commit,
                        recorded_revision, registration_hash, environment_names,
                        "incomplete", "unverified")
                    _atomic_json(args.out, transcript)
                    return transcript, 4
                actual_cost = _money(cost, "provider request cost", allow_zero=True)
                _eval_require(actual_cost <= max_request_cost,
                              "provider request cost exceeded the declared maximum")
                spent += actual_cost
                _eval_require(spent <= cost_cap, "provider cost cap was exceeded")
    transcript = _build_selection_comparison_transcript(
        bundle, catalogs, cases, records, registration_commit,
        recorded_revision, registration_hash, environment_names, "complete", "verified")
    _atomic_json(args.out, transcript)
    return transcript, 0


def replay_selection(bundle, args, transcript=None):
    transcript = transcript or _read_json_path(
        args.transcript, "selection transcript", max_bytes=4 * MAX_JSON_BYTES)
    _eval_require(transcript.get("version") == 1 and transcript.get("kind") == "selection",
                  "selection transcript schema is invalid")
    _eval_require(transcript.get("status") == "complete", "selection transcript is incomplete")
    registration_commit, recorded_revision, frozen = _verify_frozen_inputs(
        bundle, transcript.get("registration_commit"), transcript.get("recorded_revision"))
    _eval_require(transcript.get("registration_sha256") == frozen["selection registration"],
                  "registration hash mismatch")
    _eval_require(transcript.get("registration_id") == bundle["selection"]["registration_id"],
                  "registration id mismatch")
    transcript_catalog = transcript.get("catalog")
    _eval_require(isinstance(transcript_catalog, dict) and
                  transcript_catalog.get("id") in ("baseline", "candidate"),
                  "catalog id is invalid")
    catalog = _selection_catalog(bundle, transcript_catalog["id"], recorded_revision)
    _eval_require(isinstance(transcript_catalog, dict) and
                  transcript_catalog.get("sha256") == catalog["sha256"],
                  "catalog hash mismatch")
    _eval_require(transcript_catalog.get("source_sha256") == catalog["source_sha256"],
                  "catalog source hash mismatch")
    _eval_require(transcript_catalog.get("skill_count") == catalog["skill_count"],
                  "catalog skill count mismatch")
    catalog_ids = {item["id"] for item in catalog["skills"]}
    cases_by_id = {case["id"]: case for case in bundle["selection"]["cases"]}
    case_ids = transcript.get("case_ids")
    _eval_require(isinstance(case_ids, list) and case_ids and len(case_ids) == len(set(case_ids)),
                  "transcript case ids are invalid")
    _eval_require(all(case_id in cases_by_id for case_id in case_ids), "transcript references an unknown case")
    repetitions = bundle["selection"]["protocol"]["repetitions"]
    _eval_require(transcript.get("repetitions") == repetitions, "transcript repeat count mismatch")
    records = transcript.get("records")
    _eval_require(isinstance(records, list), "transcript records must be an array")
    seen = set()
    rescored = []
    for record in records:
        _eval_require(isinstance(record, dict), "transcript records must be objects")
        key = (record.get("case_id"), record.get("repeat"))
        _eval_require(key not in seen, "transcript contains duplicate repeat records")
        seen.add(key)
        case = cases_by_id.get(record.get("case_id"))
        _eval_require(case is not None and case["id"] in case_ids, "transcript record references an unknown case")
        repeat = record.get("repeat")
        _eval_require(isinstance(repeat, int) and 1 <= repeat <= repetitions, "transcript repeat is invalid")
        request = _selection_request(case, repeat, catalog)
        _eval_require(record.get("request_sha256") == _sha256(_canonical_json(request)),
                      "request hash mismatch")
        _eval_require(record.get("catalog_sha256") == catalog["sha256"], "record catalog hash mismatch")
        _eval_require(record.get("registration_sha256") == frozen["selection registration"],
                      "record registration hash mismatch")
        selected = record.get("selected")
        _eval_require(isinstance(selected, list) and len(selected) == len(set(selected)) and
                      all(item in catalog_ids for item in selected), "record selected skills are invalid")
        outcome = _score_selection(case, selected)
        _eval_require(record.get("outcome") == outcome, "record outcome does not match exact label scoring")
        rescored.append(record)
    expected = {(case_id, repeat) for case_id in case_ids for repeat in range(1, repetitions + 1)}
    _eval_require(seen == expected, "transcript repeat coverage is incomplete")
    cases = [cases_by_id[case_id] for case_id in case_ids]
    summary = _selection_summary(cases, rescored, bundle["selection"]["pass_criteria"])
    _eval_require(transcript.get("summary") == summary, "transcript summary does not match replay")
    return {
        "version": 1,
        "kind": "selection",
        "mode": "replay",
        "status": "complete",
        "registration_commit": registration_commit,
        "recorded_revision": recorded_revision,
        "records": rescored,
        "summary": summary,
    }


def replay_selection_comparison(bundle, transcript):
    _eval_require(transcript.get("version") == 1 and transcript.get("kind") == "selection-comparison",
                  "selection comparison transcript schema is invalid")
    _eval_require(transcript.get("status") == "complete", "selection comparison transcript is incomplete")
    registration_commit, recorded_revision, frozen = _verify_frozen_inputs(
        bundle, transcript.get("registration_commit"), transcript.get("recorded_revision"))
    _eval_require(transcript.get("registration_sha256") == frozen["selection registration"],
                  "selection comparison registration hash mismatch")
    _eval_require(transcript.get("registration_id") == bundle["selection"]["registration_id"],
                  "selection comparison registration id mismatch")
    catalogs = {
        "baseline": _selection_catalog(bundle, "baseline", recorded_revision),
        "candidate": _selection_catalog(bundle, "candidate", recorded_revision),
    }
    transcript_catalogs = transcript.get("catalogs")
    _eval_require(isinstance(transcript_catalogs, dict) and set(transcript_catalogs) == set(catalogs),
                  "selection comparison catalogs are invalid")
    for catalog_id, catalog in catalogs.items():
        saved = transcript_catalogs[catalog_id]
        _eval_require(saved.get("sha256") == catalog["sha256"],
                      "%s comparison catalog hash mismatch" % catalog_id)
        _eval_require(saved.get("source_sha256") == catalog["source_sha256"],
                      "%s comparison catalog source hash mismatch" % catalog_id)
        _eval_require(saved.get("skill_count") == catalog["skill_count"],
                      "%s comparison catalog skill count mismatch" % catalog_id)
    catalog_ids = {item["id"] for item in catalogs["baseline"]["skills"]}
    cases_by_id = {case["id"]: case for case in bundle["selection"]["cases"]}
    case_ids = transcript.get("case_ids")
    _eval_require(isinstance(case_ids, list) and case_ids and len(case_ids) == len(set(case_ids)),
                  "selection comparison case ids are invalid")
    _eval_require(all(case_id in cases_by_id for case_id in case_ids),
                  "selection comparison references an unknown case")
    repetitions = bundle["selection"]["protocol"]["repetitions"]
    _eval_require(transcript.get("repetitions") == repetitions,
                  "selection comparison repeat count mismatch")
    records = transcript.get("records")
    _eval_require(isinstance(records, list), "selection comparison records must be an array")
    seen = set()
    rescored = []
    for record in records:
        _eval_require(isinstance(record, dict), "selection comparison records must be objects")
        key = (record.get("case_id"), record.get("repeat"), record.get("catalog_id"))
        _eval_require(key not in seen, "selection comparison has duplicate catalog repeats")
        seen.add(key)
        case = cases_by_id.get(record.get("case_id"))
        _eval_require(case is not None and case["id"] in case_ids,
                      "selection comparison record references an unknown case")
        repeat = record.get("repeat")
        catalog_id = record.get("catalog_id")
        _eval_require(isinstance(repeat, int) and 1 <= repeat <= repetitions,
                      "selection comparison repeat is invalid")
        _eval_require(catalog_id in catalogs, "selection comparison catalog id is invalid")
        expected_order = _catalog_condition_order(case["id"], repeat)
        _eval_require(record.get("order_index") == expected_order.index(catalog_id) + 1,
                      "selection comparison catalog order is invalid")
        catalog = catalogs[catalog_id]
        request = _selection_request(case, repeat, catalog)
        _eval_require(record.get("request_sha256") == _sha256(_canonical_json(request)),
                      "selection comparison request hash mismatch")
        _eval_require(record.get("catalog_sha256") == catalog["sha256"],
                      "selection comparison record catalog hash mismatch")
        _eval_require(record.get("registration_sha256") == frozen["selection registration"],
                      "selection comparison record registration hash mismatch")
        selected = record.get("selected")
        _eval_require(isinstance(selected, list) and len(selected) == len(set(selected)) and
                      all(item in catalog_ids for item in selected),
                      "selection comparison selected skills are invalid")
        outcome = _score_selection(case, selected)
        _eval_require(record.get("outcome") == outcome,
                      "selection comparison outcome does not match exact labels")
        rescored.append(record)
    expected = {
        (case_id, repeat, catalog_id)
        for case_id in case_ids
        for repeat in range(1, repetitions + 1)
        for catalog_id in catalogs
    }
    _eval_require(seen == expected, "selection comparison repeat coverage is incomplete")
    cases = [cases_by_id[case_id] for case_id in case_ids]
    summaries, comparison = _selection_comparison(
        cases, rescored, bundle["selection"]["pass_criteria"])
    _eval_require(transcript.get("summaries") == summaries,
                  "selection comparison summaries do not match replay")
    _eval_require(transcript.get("comparison") == comparison,
                  "selection comparison result does not match replay")
    return {
        "version": 1,
        "kind": "selection-comparison",
        "mode": "replay",
        "status": "complete",
        "cost_status": transcript.get("cost_status"),
        "registration_id": transcript.get("registration_id"),
        "registration_commit": registration_commit,
        "recorded_revision": recorded_revision,
        "recorded_at": transcript.get("recorded_at"),
        "catalogs": transcript_catalogs,
        "case_ids": case_ids,
        "repetitions": repetitions,
        "provider": transcript.get("provider"),
        "model": transcript.get("model"),
        "records": rescored,
        "summaries": summaries,
        "comparison": comparison,
    }


def _task_skill(bundle, revision, skill_id):
    path = "skills/%s/SKILL.md" % skill_id
    blob = _git_command(bundle["root"], ["show", "%s:%s" % (revision, path)],
                        "cannot resolve task skill")
    name, _ = _skill_description(blob, path)
    _eval_require(name == skill_id, "%s name does not match its directory" % path)
    try:
        text = blob.decode("utf-8")
    except UnicodeError as exc:
        raise EvaluationError("%s is not UTF-8: %s" % (path, exc))
    return {
        "id": skill_id,
        "source_path": path,
        "source_sha256": _sha256(blob.replace(b"\r\n", b"\n")),
        "content": text,
    }


def _task_condition_order(case_id, repeat):
    seed = int(_sha256((case_id + ":condition-order").encode("utf-8"))[:8], 16) % 2
    first = (seed + repeat - 1) % 2
    conditions = ["baseline", "with_skill"]
    return [conditions[first], conditions[1 - first]]


def _task_request(case, repeat, condition, skill):
    return {
        "version": 1,
        "kind": "task",
        "case_id": case["id"],
        "role": case["role"],
        "repeat": repeat,
        "condition": condition,
        "prompt": case["prompt"],
        "skill": None if condition == "baseline" else {
            "id": skill["id"],
            "source_sha256": skill["source_sha256"],
            "content": skill["content"],
        },
        "response_schema": {
            "version": 1,
            "response": "plain-text answer to the task",
            "usage": "input_tokens, output_tokens, and cost_usd",
        },
    }


def _json_has_field(value, dotted):
    current = value
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _score_task_assertions(case, response):
    folded = response.casefold()
    try:
        parsed = json.loads(response)
    except ValueError:
        parsed = None
    results = []
    for assertion in case["assertions"]:
        values = assertion["values"]
        kind = assertion["kind"]
        if kind == "contains_all":
            passed = all(value.casefold() in folded for value in values)
        elif kind == "contains_any":
            passed = any(value.casefold() in folded for value in values)
        elif kind == "excludes_all":
            passed = all(value.casefold() not in folded for value in values)
        else:
            passed = parsed is not None and all(_json_has_field(parsed, value) for value in values)
        results.append({"id": assertion["id"], "kind": kind, "passed": bool(passed)})
    return {
        "passed": sum(1 for result in results if result["passed"]),
        "registered": len(results),
        "results": results,
    }


def _task_summary(cases, records, protocol):
    conditions = {
        condition: {
            "records": 0,
            "passed": 0,
            "registered": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "duration_ms": 0.0,
        }
        for condition in ("baseline", "with_skill")
    }
    by_case = {}
    for record in records:
        totals = conditions[record["condition"]]
        totals["records"] += 1
        totals["passed"] += record["assertions"]["passed"]
        totals["registered"] += record["assertions"]["registered"]
        totals["input_tokens"] += record["usage"]["input_tokens"]
        totals["output_tokens"] += record["usage"]["output_tokens"]
        totals["cost_usd"] += record["usage"]["cost_usd"] or 0.0
        totals["duration_ms"] += record["duration_ms"]
        case_totals = by_case.setdefault(record["case_id"], {
            "skill": record["skill"],
            "baseline": {"passed": 0, "registered": 0},
            "with_skill": {"passed": 0, "registered": 0},
        })
        bucket = case_totals[record["condition"]]
        bucket["passed"] += record["assertions"]["passed"]
        bucket["registered"] += record["assertions"]["registered"]
    for totals in conditions.values():
        totals["pass_rate"] = totals["passed"] / totals["registered"] if totals["registered"] else 0.0
        totals["duration_ms"] = round(totals["duration_ms"], 3)
        totals["cost_usd"] = round(totals["cost_usd"], 12)

    negative_deltas = []
    by_skill = {}
    for case_id, totals in sorted(by_case.items()):
        baseline = totals["baseline"]
        with_skill = totals["with_skill"]
        baseline["pass_rate"] = baseline["passed"] / baseline["registered"] if baseline["registered"] else 0.0
        with_skill["pass_rate"] = with_skill["passed"] / with_skill["registered"] if with_skill["registered"] else 0.0
        delta = with_skill["pass_rate"] - baseline["pass_rate"]
        totals["delta"] = delta
        if delta < 0:
            negative_deltas.append({"case_id": case_id, "skill": totals["skill"], "delta": delta})
        skill = by_skill.setdefault(totals["skill"], {"improved_cases": 0, "regressed_cases": 0, "case_deltas": {}})
        skill["case_deltas"][case_id] = delta
        if delta >= 0.15:
            skill["improved_cases"] += 1
        if delta < -0.10:
            skill["regressed_cases"] += 1
    for totals in by_skill.values():
        totals["verdict"] = (
            "pass" if totals["improved_cases"] >= 2 and totals["regressed_cases"] == 0 else "fail")
    complete_corpus = len(cases) == 30
    verdict = "unverified"
    if complete_corpus:
        verdict = "pass" if all(item["verdict"] == "pass" for item in by_skill.values()) else "fail"
    judge = protocol.get("judge", {})
    return {
        "conditions": conditions,
        "by_case": by_case,
        "by_skill": dict(sorted(by_skill.items())),
        "negative_deltas": negative_deltas,
        "judge": {
            "used": False,
            "enabled_by_default": bool(judge.get("enabled_by_default")),
            "human_calibration_samples": judge.get("human_calibration_samples"),
            "human_spotcheck_fraction": judge.get("human_spotcheck_fraction"),
            "caveat": "Automated judge scores are supporting evidence only and were not used for deterministic assertions.",
        },
        "verdict": verdict,
    }


def _build_task_transcript(bundle, catalog, cases, records, registration_commit,
                           recorded_revision, registration_hash, source_hash,
                           environment_names, status, cost_status):
    providers = sorted({record["provider"] for record in records})
    models = sorted({record["model"] for record in records})
    summary = _task_summary(cases, records, bundle["tasks"]["protocol"])
    if status != "complete":
        summary["verdict"] = "unverified"
    return {
        "version": 1,
        "kind": "task",
        "mode": "record",
        "status": status,
        "cost_status": cost_status,
        "registration_id": bundle["tasks"]["registration_id"],
        "registration_commit": registration_commit,
        "registration_sha256": registration_hash,
        "recorded_revision": recorded_revision,
        "recorded_at": _utc_timestamp(),
        "catalog": {"id": catalog["id"], "source_sha256": source_hash},
        "case_ids": [case["id"] for case in cases],
        "repetitions": bundle["tasks"]["protocol"]["repetitions"],
        "conditions": ["baseline", "with_skill"],
        "provider": providers[0] if len(providers) == 1 else providers,
        "model": models[0] if len(models) == 1 else models,
        "provider_environment_names": environment_names,
        "records": records,
        "summary": summary,
    }


def record_tasks(bundle, args):
    registration_commit, recorded_revision, frozen = _verify_frozen_inputs(
        bundle, args.registration_commit, args.recorded_revision)
    _eval_require(args.catalog == "candidate", "paired task evaluation requires the committed candidate catalog")
    catalog = _selection_catalog(bundle, "candidate", recorded_revision)
    cases = bundle["tasks"]["cases"]
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        _eval_require(bool(cases), "task case not found: %s" % args.case)
    _eval_require(bool(cases), "no task cases matched the requested scope")
    skills = {
        skill_id: _task_skill(bundle, recorded_revision, skill_id)
        for skill_id in sorted({case["skill"] for case in cases})
    }
    source_hash = _sha256(_canonical_json([
        {"id": skill_id, "sha256": skills[skill_id]["source_sha256"]}
        for skill_id in sorted(skills)
    ]))

    protocol = bundle["tasks"]["protocol"]
    registered_request_cap = protocol["limits"]["requests"]
    request_cap = args.request_cap if args.request_cap is not None else registered_request_cap
    _eval_require(isinstance(request_cap, int) and 0 < request_cap <= registered_request_cap,
                  "request cap must be positive and no greater than the registration")
    registered_cost_cap = _money(protocol["limits"]["cost_usd"], "registered cost cap")
    cost_cap = _money(args.cost_cap, "cost cap") if args.cost_cap is not None else registered_cost_cap
    _eval_require(cost_cap <= registered_cost_cap, "cost cap must not exceed the registration")
    max_request_cost = _money(args.max_request_cost, "maximum request cost")
    _eval_require(max_request_cost <= cost_cap, "maximum request cost must not exceed the cost cap")
    _eval_require(isinstance(args.max_response_bytes, int) and 0 < args.max_response_bytes <= MAX_JSON_BYTES,
                  "maximum provider response must be 1..%d bytes" % MAX_JSON_BYTES)
    _eval_require(isinstance(args.provider_timeout, int) and 0 < args.provider_timeout <= 600,
                  "provider timeout must be 1..600 seconds")

    argv, child_env, environment_names, credential_values = _provider_configuration()
    records = []
    spent = Decimal("0")
    input_tokens = 0
    provider_identity = None
    repetitions = protocol["repetitions"]
    registration_hash = frozen["task registration"]
    for case in cases:
        skill = skills[case["skill"]]
        for repeat in range(1, repetitions + 1):
            for order_index, condition in enumerate(_task_condition_order(case["id"], repeat), 1):
                if len(records) >= request_cap:
                    raise EvaluationError("request cap would be exceeded before task repeat %d" % repeat)
                if spent + max_request_cost > cost_cap:
                    raise EvaluationError("cost cap would be exceeded before task repeat %d" % repeat)
                request = _task_request(case, repeat, condition, skill)
                response = _provider_response(
                    request, argv, child_env, credential_values, args.max_response_bytes,
                    args.provider_timeout)
                identity = (response["provider"], response["model"])
                if provider_identity is None:
                    provider_identity = identity
                _eval_require(identity == provider_identity, "provider or model identity changed during recording")
                input_tokens += response["usage"]["input_tokens"]
                _eval_require(input_tokens <= protocol["limits"]["input_tokens"],
                              "input token cap was exceeded")
                cost = response["usage"]["cost_usd"]
                record = {
                    "case_id": case["id"],
                    "skill": case["skill"],
                    "role": case["role"],
                    "repeat": repeat,
                    "condition": condition,
                    "order_index": order_index,
                    "request_sha256": _sha256(_canonical_json(request)),
                    "registration_sha256": registration_hash,
                    "skill_source_sha256": skill["source_sha256"],
                    "provider": response["provider"],
                    "model": response["model"],
                    "response": response["response"],
                    "usage": response["usage"],
                    "duration_ms": response["duration_ms"],
                    "assertions": _score_task_assertions(case, response["response"]),
                }
                records.append(record)
                if cost is None:
                    transcript = _build_task_transcript(
                        bundle, catalog, cases, records, registration_commit,
                        recorded_revision, registration_hash, source_hash,
                        environment_names, "incomplete", "unverified")
                    _atomic_json(args.out, transcript)
                    return transcript, 4
                actual_cost = _money(cost, "provider request cost", allow_zero=True)
                _eval_require(actual_cost <= max_request_cost,
                              "provider request cost exceeded the declared maximum")
                spent += actual_cost
                _eval_require(spent <= cost_cap, "provider cost cap was exceeded")

    transcript = _build_task_transcript(
        bundle, catalog, cases, records, registration_commit,
        recorded_revision, registration_hash, source_hash,
        environment_names, "complete", "verified")
    _atomic_json(args.out, transcript)
    return transcript, 0


def replay_tasks(bundle, args, transcript):
    _eval_require(transcript.get("version") == 1 and transcript.get("kind") == "task",
                  "task transcript schema is invalid")
    _eval_require(transcript.get("status") == "complete", "task transcript is incomplete")
    registration_commit, recorded_revision, frozen = _verify_frozen_inputs(
        bundle, transcript.get("registration_commit"), transcript.get("recorded_revision"))
    _eval_require(transcript.get("registration_sha256") == frozen["task registration"],
                  "task registration hash mismatch")
    _eval_require(transcript.get("registration_id") == bundle["tasks"]["registration_id"],
                  "task registration id mismatch")
    transcript_catalog = transcript.get("catalog")
    _eval_require(isinstance(transcript_catalog, dict) and transcript_catalog.get("id") == "candidate",
                  "task catalog id is invalid")
    cases_by_id = {case["id"]: case for case in bundle["tasks"]["cases"]}
    case_ids = transcript.get("case_ids")
    _eval_require(isinstance(case_ids, list) and case_ids and len(case_ids) == len(set(case_ids)),
                  "task transcript case ids are invalid")
    _eval_require(all(case_id in cases_by_id for case_id in case_ids),
                  "task transcript references an unknown case")
    cases = [cases_by_id[case_id] for case_id in case_ids]
    skills = {
        skill_id: _task_skill(bundle, recorded_revision, skill_id)
        for skill_id in sorted({case["skill"] for case in cases})
    }
    source_hash = _sha256(_canonical_json([
        {"id": skill_id, "sha256": skills[skill_id]["source_sha256"]}
        for skill_id in sorted(skills)
    ]))
    _eval_require(transcript_catalog.get("source_sha256") == source_hash,
                  "task skill source hash mismatch")
    repetitions = bundle["tasks"]["protocol"]["repetitions"]
    _eval_require(transcript.get("repetitions") == repetitions, "task transcript repeat count mismatch")
    records = transcript.get("records")
    _eval_require(isinstance(records, list), "task transcript records must be an array")
    seen = set()
    rescored = []
    for record in records:
        _eval_require(isinstance(record, dict), "task transcript records must be objects")
        key = (record.get("case_id"), record.get("repeat"), record.get("condition"))
        _eval_require(key not in seen, "task transcript contains duplicate condition repeats")
        seen.add(key)
        case = cases_by_id.get(record.get("case_id"))
        _eval_require(case is not None and case["id"] in case_ids,
                      "task transcript record references an unknown case")
        repeat = record.get("repeat")
        condition = record.get("condition")
        _eval_require(isinstance(repeat, int) and 1 <= repeat <= repetitions,
                      "task transcript repeat is invalid")
        _eval_require(condition in ("baseline", "with_skill"), "task transcript condition is invalid")
        expected_order = _task_condition_order(case["id"], repeat)
        _eval_require(record.get("order_index") == expected_order.index(condition) + 1,
                      "task condition order does not match registration")
        skill = skills[case["skill"]]
        request = _task_request(case, repeat, condition, skill)
        _eval_require(record.get("request_sha256") == _sha256(_canonical_json(request)),
                      "task request hash mismatch")
        _eval_require(record.get("registration_sha256") == frozen["task registration"],
                      "task record registration hash mismatch")
        _eval_require(record.get("skill_source_sha256") == skill["source_sha256"],
                      "task skill source hash mismatch")
        _eval_require(isinstance(record.get("response"), str) and record["response"].strip(),
                      "task response is invalid")
        _eval_require(isinstance(record.get("duration_ms"), (int, float)) and record["duration_ms"] >= 0,
                      "task duration is invalid")
        assertions = _score_task_assertions(case, record["response"])
        _eval_require(record.get("assertions") == assertions,
                      "task assertions do not match deterministic replay")
        rescored.append(record)
    expected = {
        (case_id, repeat, condition)
        for case_id in case_ids
        for repeat in range(1, repetitions + 1)
        for condition in ("baseline", "with_skill")
    }
    _eval_require(seen == expected, "task transcript repeat coverage is incomplete")
    summary = _task_summary(cases, rescored, bundle["tasks"]["protocol"])
    _eval_require(transcript.get("summary") == summary, "task transcript summary does not match replay")
    return {
        "version": 1,
        "kind": "task",
        "mode": "replay",
        "status": "complete",
        "cost_status": transcript.get("cost_status"),
        "registration_id": transcript.get("registration_id"),
        "registration_commit": registration_commit,
        "recorded_revision": recorded_revision,
        "recorded_at": transcript.get("recorded_at"),
        "catalog": transcript_catalog,
        "case_ids": case_ids,
        "repetitions": repetitions,
        "provider": transcript.get("provider"),
        "model": transcript.get("model"),
        "records": rescored,
        "summary": summary,
    }


def replay_evaluation(bundle, args):
    transcript = _read_json_path(args.transcript, "evaluation transcript", max_bytes=8 * MAX_JSON_BYTES)
    if transcript.get("kind") == "selection":
        return replay_selection(bundle, args, transcript)
    if transcript.get("kind") == "selection-comparison":
        return replay_selection_comparison(bundle, transcript)
    if transcript.get("kind") == "task":
        return replay_tasks(bundle, args, transcript)
    raise EvaluationError("evaluation transcript kind is unsupported")


def _format_number(value):
    return ("%.3f" % value).rstrip("0").rstrip(".")


def _signed_number(value):
    return ("+" if value > 0 else "") + _format_number(value)


def render_task_report(result):
    summary = result["summary"]
    conditions = summary["conditions"]
    labels = (("baseline", "Baseline"), ("with_skill", "With skill"))
    lines = [
        "# Current paired task evaluation",
        "",
        "- Tested revision: `%s`" % result["recorded_revision"],
        "- Registration: `%s` at `%s`" % (result["registration_id"], result["registration_commit"]),
        "- Provider/model: `%s` / `%s`" % (result["provider"], result["model"]),
        "- Cases/repetitions: %d cases, %d repeats, baseline and with-skill conditions" % (
            len(result["case_ids"]), result["repetitions"]),
        "- Recorded at: `%s`; cost status: `%s`" % (result["recorded_at"], result["cost_status"]),
        "- Overall registered verdict: **%s**" % summary["verdict"].upper(),
        "",
        "## Conditions",
        "",
        "| Condition | Assertions | Pass rate | Input tokens | Output/reasoning tokens | Time (s) | Cost (USD) | Per-response spread |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    rates = {condition: [] for condition, _ in labels}
    for record in result["records"]:
        assertions = record["assertions"]
        rates[record["condition"]].append(
            assertions["passed"] / assertions["registered"] if assertions["registered"] else 0.0)
    for condition, label in labels:
        values = conditions[condition]
        spread = "%s%% to %s%%" % (
            _format_number(min(rates[condition]) * 100),
            _format_number(max(rates[condition]) * 100),
        )
        lines.append("| %s | %d/%d | %s%% | %d | %d | %s | %s | %s |" % (
            label,
            values["passed"], values["registered"],
            _format_number(values["pass_rate"] * 100),
            values["input_tokens"], values["output_tokens"],
            _format_number(values["duration_ms"] / 1000),
            _format_number(values["cost_usd"]), spread,
        ))
    baseline = conditions["baseline"]
    with_skill = conditions["with_skill"]
    lines.extend([
        "",
        "With-skill minus baseline: **%s percentage points**, **%+d input tokens**, "
        "**%+d output/reasoning tokens**, **%s seconds**, **%s USD**." % (
            _format_number((with_skill["pass_rate"] - baseline["pass_rate"]) * 100),
            with_skill["input_tokens"] - baseline["input_tokens"],
            with_skill["output_tokens"] - baseline["output_tokens"],
            _signed_number((with_skill["duration_ms"] - baseline["duration_ms"]) / 1000),
            _signed_number(with_skill["cost_usd"] - baseline["cost_usd"]),
        ),
        "",
        "## Per-skill registered verdicts",
        "",
        "| Skill | Improved cases | Regressed cases | Verdict |",
        "|---|---:|---:|---|",
    ])
    for skill, values in sorted(summary["by_skill"].items()):
        lines.append("| %s | %d | %d | %s |" % (
            skill, values["improved_cases"], values["regressed_cases"], values["verdict"].upper()))
    lines.extend(["", "## Negative deltas", ""])
    if summary["negative_deltas"]:
        lines.extend(["| Case | Skill | Delta |", "|---|---|---:|"])
        for item in summary["negative_deltas"]:
            lines.append("| %s | %s | %.1f pp |" % (
                item["case_id"], item["skill"], item["delta"] * 100))
    else:
        lines.append("No registered negative deltas.")
    judge = summary["judge"]
    lines.extend([
        "",
        "## Judge and human evidence",
        "",
        "- Automated judge used: `%s`." % str(judge["used"]).lower(),
        "- Registered human calibration samples: `%s`; spot-check fraction: `%s`." % (
            judge["human_calibration_samples"], judge["human_spotcheck_fraction"]),
        "- Caveat: %s" % judge["caveat"],
        "",
        "## Evidence boundary",
        "",
        "Deterministic string/JSON assertions are narrow supporting evidence only. They do not establish overall response quality, human approval, live loader behavior, or causation. Historical manual reports remain dated and unchanged.",
    ])
    return "\n".join(lines) + "\n"


def render_selection_comparison_report(result):
    summaries = result["summaries"]
    records = result["records"]
    lines = [
        "# Final held-out skill selection comparison",
        "",
        "- Tested revision: `%s`" % result["recorded_revision"],
        "- Registration: `%s` at `%s`" % (result["registration_id"], result["registration_commit"]),
        "- Provider/model: `%s` / `%s`" % (result["provider"], result["model"]),
        "- Cases/repetitions: %d held-out cases, two catalogs, %d repeats" % (
            len(result["case_ids"]), result["repetitions"]),
        "- Recorded at: `%s`; cost status: `%s`" % (result["recorded_at"], result["cost_status"]),
        "- Comparison verdict: **%s**" % result["comparison"]["verdict"].upper(),
        "",
        "## Catalog outcomes",
        "",
        "| Catalog | Exact-label records | Precision | Recall | Input tokens | Output/reasoning tokens | Cost (USD) | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for catalog_id, label in (("baseline", "Baseline"), ("candidate", "Candidate")):
        summary = summaries[catalog_id]
        scoped = [record for record in records if record["catalog_id"] == catalog_id]
        lines.append("| %s | %d/%d | %s%% | %s%% | %d | %d | %s | %s |" % (
            label,
            summary["passed_records"], summary["records"],
            _format_number(summary["aggregate"]["precision"] * 100),
            _format_number(summary["aggregate"]["recall"] * 100),
            sum(record["usage"]["input_tokens"] for record in scoped),
            sum(record["usage"]["output_tokens"] for record in scoped),
            _format_number(sum(record["usage"]["cost_usd"] or 0 for record in scoped)),
            summary["verdict"].upper(),
        ))
    lines.extend([
        "",
        "Candidate minus baseline exact-label records: **%+d**." % result["comparison"]["passed_record_delta"],
        "",
        "## Per-case comparison",
        "",
        "| Case | Baseline | Candidate | Delta |",
        "|---|---:|---:|---:|",
    ])
    for case_id in result["case_ids"]:
        counts = {}
        for catalog_id in ("baseline", "candidate"):
            counts[catalog_id] = sum(
                record["outcome"]["status"] == "pass"
                for record in records
                if record["case_id"] == case_id and record["catalog_id"] == catalog_id)
        lines.append("| %s | %d/%d | %d/%d | %+d |" % (
            case_id, counts["baseline"], result["repetitions"],
            counts["candidate"], result["repetitions"],
            counts["candidate"] - counts["baseline"],
        ))
    lines.extend(["", "## Preserved misses and confusions", ""])
    failed = [record for record in records if record["outcome"]["status"] == "fail"]
    if not failed:
        lines.append("No exact-label misses were recorded.")
    else:
        lines.extend(["| Catalog | Case | Repeat | Selected | Missing | Forbidden | Unexpected |",
                      "|---|---|---:|---|---|---|---|"])
        for record in failed:
            outcome = record["outcome"]
            lines.append("| %s | %s | %d | %s | %s | %s | %s |" % (
                record["catalog_id"], record["case_id"], record["repeat"],
                ", ".join(record["selected"]) or "none",
                ", ".join(outcome["missing_expected"]) or "none",
                ", ".join(outcome["forbidden_selected"]) or "none",
                ", ".join(outcome["unexpected_selected"]) or "none",
            ))
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        "Catalog selection is not live loader discovery, automatic skill invocation, loaded-context measurement, task quality, or human approval. The held-out results were inspected only after descriptions were frozen, and no description edit follows this report.",
    ])
    return "\n".join(lines) + "\n"


def _add_registration_args(parser):
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--selection")
    parser.add_argument("--tasks")
    parser.add_argument("--product-catalog")
    parser.add_argument("--external-catalog")


def _registration_defaults(args):
    root = os.path.realpath(os.path.abspath(args.root))
    args.root = root
    args.selection = args.selection or os.path.join(root, "evals", "selection-cases.json")
    args.tasks = args.tasks or os.path.join(root, "evals", "task-cases.json")
    args.product_catalog = args.product_catalog or os.path.join(root, "evals", "catalogs", "product-baseline.json")
    args.external_catalog = args.external_catalog or os.path.join(root, "evals", "catalogs", "external-distractors.json")


def build_parser():
    parser = argparse.ArgumentParser(prog="model_eval", description=__doc__)
    sub = parser.add_subparsers(dest="command")

    validate = sub.add_parser("validate", help="validate frozen registrations and catalogs")
    _add_registration_args(validate)
    validate.add_argument("--json", action="store_true")

    record = sub.add_parser("record", help="record an explicitly authorized provider run")
    _add_registration_args(record)
    record.add_argument("--kind", choices=("selection", "task"), required=True)
    record.add_argument("--case")
    record.add_argument("--split", choices=("development", "held_out", "all"), default="development")
    record.add_argument("--catalog", choices=("baseline", "candidate", "paired"), default="baseline")
    record.add_argument("--registration-commit", required=True)
    record.add_argument("--recorded-revision", required=True)
    record.add_argument("--out", required=True)
    record.add_argument("--request-cap", type=int)
    record.add_argument("--cost-cap")
    record.add_argument("--max-request-cost", required=True)
    record.add_argument("--max-response-bytes", type=int, default=65536)
    record.add_argument("--provider-timeout", type=int, default=DEFAULT_PROVIDER_TIMEOUT)
    record.add_argument("--json", action="store_true")

    replay = sub.add_parser("replay", help="replay and rescore a committed transcript offline")
    _add_registration_args(replay)
    replay.add_argument("--transcript", required=True)
    replay.add_argument("--report")
    replay.add_argument("--json", action="store_true")
    return parser


def run(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    _registration_defaults(args)
    try:
        if args.command == "validate":
            result = validate_all(args.root, args)
            exit_code = 0
        elif args.command == "record":
            bundle = _load_bundle(args.root, args)
            if args.kind == "selection":
                if args.catalog == "paired":
                    result, exit_code = record_selection_comparison(bundle, args)
                else:
                    result, exit_code = record_selection(bundle, args)
            else:
                result, exit_code = record_tasks(bundle, args)
        else:
            bundle = _load_bundle(args.root, args)
            result = replay_evaluation(bundle, args)
            if args.report:
                if result["kind"] == "task":
                    report = render_task_report(result)
                elif result["kind"] == "selection-comparison":
                    report = render_selection_comparison_report(result)
                else:
                    raise EvaluationError("Markdown reports require task or selection-comparison transcripts")
                _atomic_text(args.report, report)
            exit_code = 0
    except (RegistrationError, EvaluationError) as exc:
        if args.json:
            print(json.dumps({"status": "invalid", "error": str(exc)}, sort_keys=True))
        else:
            sys.stderr.write("model_eval: %s\n" % exc)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.command == "validate":
        print("registrations valid: %d selection cases, %d task cases" % (
            result["selection_cases"], result["task_cases"]))
    elif args.command == "record":
        print("recorded %d %s responses to %s" % (len(result["records"]), result["kind"], args.out))
    else:
        print("replayed %d %s responses" % (len(result["records"]), result["kind"]))
    return exit_code


if __name__ == "__main__":
    sys.exit(run())
