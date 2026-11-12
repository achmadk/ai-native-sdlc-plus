"""Validate preregistered model-selection and paired task evaluation inputs."""

import sys

if sys.version_info < (3, 8):
    sys.exit("model_eval requires Python >= 3.8")
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import math
import os
import re
import subprocess


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


class RegistrationError(ValueError):
    pass


def _reject_constant(value):
    raise ValueError("non-finite JSON number: %s" % value)


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


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
        with open(actual_path, "rb") as handle:
            actual_hash = _sha256(handle.read())
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


def validate_all(root, args):
    root = os.path.realpath(os.path.abspath(root))
    product, product_path = _load_json(root, args.product_catalog, "product catalog")
    external, external_path = _load_json(root, args.external_catalog, "external catalog")
    product_ids = validate_product_catalog(root, product)
    external_ids = validate_external_catalog(external)
    selection, selection_path = _load_json(root, args.selection, "selection registration")
    tasks, _ = _load_json(root, args.tasks, "task registration")
    validate_selection(root, selection, selection_path, product_path, external_path, product_ids | external_ids)
    validate_tasks(tasks)
    return {
        "status": "valid",
        "registration_ids": [selection["registration_id"], tasks["registration_id"]],
        "selection_cases": len(selection["cases"]),
        "task_cases": len(tasks["cases"]),
        "product_skills": len(product_ids),
        "external_skills": len(external_ids),
    }


def build_parser():
    parser = argparse.ArgumentParser(prog="model_eval", description=__doc__)
    sub = parser.add_subparsers(dest="command")
    validate = sub.add_parser("validate", help="validate frozen registrations and catalogs")
    validate.add_argument("--root", default=DEFAULT_ROOT)
    validate.add_argument("--selection")
    validate.add_argument("--tasks")
    validate.add_argument("--product-catalog")
    validate.add_argument("--external-catalog")
    validate.add_argument("--json", action="store_true")
    return parser


def run(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "validate":
        parser.print_help()
        return 2
    root = os.path.realpath(os.path.abspath(args.root))
    args.selection = args.selection or os.path.join(root, "evals", "selection-cases.json")
    args.tasks = args.tasks or os.path.join(root, "evals", "task-cases.json")
    args.product_catalog = args.product_catalog or os.path.join(root, "evals", "catalogs", "product-baseline.json")
    args.external_catalog = args.external_catalog or os.path.join(root, "evals", "catalogs", "external-distractors.json")
    try:
        result = validate_all(root, args)
    except RegistrationError as exc:
        if args.json:
            print(json.dumps({"status": "invalid", "error": str(exc)}, sort_keys=True))
        else:
            sys.stderr.write("model_eval: registration error: %s\n" % exc)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("registrations valid: %d selection cases, %d task cases" % (
            result["selection_cases"], result["task_cases"]))
    return 0


if __name__ == "__main__":
    sys.exit(run())
