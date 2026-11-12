"""Verify installation health. Honest about what it can and cannot verify.

Statuses (one per check, printed as "name: status - detail"):
  verified    checked here and true
  FAIL        checked here and wrong: the gate will not work, or is unsafe
  WARN        works, but there is a risk or drift to look at (counts as FAIL with --strict)
  unverified  cannot be known from here; fails an explicitly requested enforcement verdict
  info        context only

Exit codes: 0 no FAIL (and no WARN with --strict) | 1 FAIL | 2 usage error.

Network: none by default. REST inspection uses `gh api` GET. Strict enforcement may
also use one fixed read-only GraphQL POST query for classic merge-queue state.
--require-enforcement requires the bounded supported profile.
An observed profile is a settings snapshot, not proof of code correctness or a hosted scan.
The config is parsed with the lane.py that sits next to this file, so a repo's own copy is
never executed. Stdlib only. Python >= 3.8.
"""

import argparse
import base64
import binascii
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import quote

sys.dont_write_bytecode = True  # an inspector must not leave files in the repo it inspects
HERE = os.path.dirname(os.path.abspath(__file__))
try:
    _spec = importlib.util.spec_from_file_location("sdlc_doctor_lane", os.path.join(HERE, "lane.py"))
    lanelib = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(lanelib)
except Exception:  # missing or broken lane.py is reported by the checks, not raised here
    lanelib = None

VERSION = "0.3.0"
OK, FAIL, WARN, UNVERIFIED, INFO = "verified", "FAIL", "WARN", "unverified", "info"
MAX_FILE_BYTES = 1000000
MAX_TRACKED_FILES = 200000
CRITICAL_SHARE_WARN = 0.30   # heuristic: above this, Critical probably fires too often to be taken seriously
MIN_FILES_FOR_SHARE = 20

# (check name, repo-relative path, status if missing)
REQUIRED_FILES = (
    ("lane-script", "scripts/lane.py", FAIL),
    ("evidence-script", "scripts/evidence_check.py", FAIL),
    ("config", "scripts/lane-config.yaml", FAIL),
    ("ci-template", ".github/workflows/sdlc-gate.yml", FAIL),
    ("pr-template", ".github/pull_request_template.md", WARN),
    ("hook-template", "hooks/pre-push.sh", WARN),
)
TOOLING = ("scripts/lane.py", "scripts/evidence_check.py", "scripts/lane-config.yaml",
           ".github/workflows/sdlc-gate.yml")
GATE_FILES = TOOLING  # what CODEOWNERS should cover
CATCH_ALL = {"**", "*", "**/*", "*/**", "**/**"}
_SHA = re.compile(r"^[0-9a-f]{40}$")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def run(cmd, cwd=None, timeout=20, env=None):
    """Return (returncode, stdout, stderr). 127 if the command cannot run."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def git(root, *args):
    return run(["git", "-C", root] + list(args))


def read_text(path):
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def sha256(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def in_git(root):
    code, out, _ = git(root, "rev-parse", "--is-inside-work-tree")
    return code == 0 and out.strip() == "true"


def clip(text, limit=160):
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(text)).replace("::", ": :")
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit - 3] + "..."


# --------------------------------------------------------------------------
# local checks. Each returns a list of (name, status, detail)
# --------------------------------------------------------------------------

def check_environment():
    version = "%d.%d.%d" % sys.version_info[:3]
    if sys.version_info < (3, 8):
        return [("python", FAIL, "Python %s; the gate scripts need >= 3.8" % version)]
    return [("python", OK, "Python %s (>= 3.8)" % version)]


def check_files(root):
    results = []
    for name, rel, missing_status in REQUIRED_FILES:
        present = os.path.isfile(os.path.join(root, rel))
        if present:
            results.append((name, OK, "%s present" % rel))
        else:
            results.append((name, missing_status, "%s missing" % rel))
    return results


def check_drift(root):
    """Compare the repo's scripts with the copies next to doctor.py."""
    results = []
    scripts_dir = os.path.join(root, "scripts")
    if os.path.realpath(scripts_dir) == os.path.realpath(HERE):
        return [("script-drift", OK, "doctor runs from this repo's scripts/, nothing to compare")]
    drifted, compared = [], 0
    for name in ("lane.py", "evidence_check.py"):
        mine, theirs = sha256(os.path.join(HERE, name)), sha256(os.path.join(scripts_dir, name))
        if mine is None or theirs is None:
            continue
        compared += 1
        if mine != theirs:
            drifted.append(name)
    if drifted:
        results.append(("script-drift", WARN,
                        "%s differ from the toolkit copies next to doctor.py (local edits, or a stale install)"
                        % ", ".join(drifted)))
    elif compared:
        results.append(("script-drift", OK, "scripts match the toolkit copies"))
    return results


def load_rules_for(root):
    """Return (rules or None, results). Parses with the trusted lane.py next to this file."""
    path = os.path.join(root, "scripts", "lane-config.yaml")
    if not os.path.isfile(path):
        return None, []  # presence already reported by check_files
    if lanelib is None:
        return None, [("config-valid", UNVERIFIED, "lane.py is not importable next to doctor.py, so the config was not parsed")]
    rules, error = lanelib.load_rules(path)
    if rules is None:
        return None, [("config-valid", FAIL, clip(error))]
    counts = {name: len(rules[name]) for name in lanelib.LANE_SECTIONS}
    detail = "valid (version %d; %d critical, %d standard, %d lite rules)" % (
        lanelib.CONFIG_VERSION, counts["critical"], counts["standard"], counts["lite"])
    results = [("config-valid", OK, detail)]

    if counts["critical"] == 0:
        results.append(("config-critical", WARN,
                        "no Critical rules: only the built-in gate files are Critical, so auth, payments and "
                        "migrations get the same process as everything else"))
    broad = [(name, pattern) for name in ("critical", "lite") for pattern in rules[name] if pattern.strip() in CATCH_ALL]
    for name, pattern in broad:
        meaning = "every path is Critical (alert fatigue)" if name == "critical" else \
            "every path not claimed by a higher lane becomes Lite, which removes the safe default"
        results.append(("config-catch-all", WARN, "%s rule %r: %s" % (name, pattern, meaning)))
    wide = [p for p in rules.get("non_executable", []) if p.strip() in CATCH_ALL or p.strip() in ("*.md", "**/*.md")]
    if wide:
        results.append(("config-non-executable", WARN,
                        "non_executable %s lets changes skip test evidence; wrong if Markdown is behaviour in this repo "
                        "(for example SKILL.md)" % ", ".join(repr(p) for p in wide)))

    # canary: the built-in protection of the gate files must survive any config
    lane_, _ = lanelib.classify(["scripts/lane.py"], rules)
    if lane_ != "Critical":
        results.append(("builtin-protection", FAIL,
                        "scripts/lane.py classified %s, not Critical: the gate no longer protects itself" % lane_))
    else:
        results.append(("builtin-protection", OK, "gate files are always Critical"))
    return rules, results


def check_rule_coverage(root, rules):
    """Calibration: do the rules match real files, and how often is Critical?"""
    if rules is None or lanelib is None:
        return []
    code, out, _ = git(root, "ls-files", "-z")
    if code != 0:
        return [("rule-coverage", UNVERIFIED, "not a git work tree, so rules were not tested against real files")]
    files = [p for p in out.split("\0") if p][:MAX_TRACKED_FILES]
    if not files:
        return [("rule-coverage", UNVERIFIED, "no tracked files yet (commit something, then re-run)")]
    compiled = lanelib.compile_rules(rules)
    config_critical = set(rules["critical"])
    hits = dict.fromkeys(config_critical, 0)
    per_lane = {"Critical": 0, "Standard": 0, "Lite": 0}
    unmatched = total = 0
    for item in files:
        path, _ = lanelib.clean_path(item)
        if path is None:
            continue
        total += 1
        lane_, rule = lanelib.path_lane(path, compiled)
        per_lane[lane_] += 1
        if rule is None:
            unmatched += 1
        for pattern, matches in compiled["critical"]:
            if pattern in config_critical and matches(path):
                hits[pattern] += 1
    results = [("rule-coverage", INFO,
                "%d tracked files: %d Critical, %d Standard, %d Lite (%d matched no rule and default to Standard)"
                % (total, per_lane["Critical"], per_lane["Standard"], per_lane["Lite"], unmatched))]
    dead = sorted(pattern for pattern, count in hits.items() if count == 0)
    if dead:
        results.append(("rule-dead-critical", WARN,
                        "Critical rule(s) matching no tracked file: %s (typo, stale, or not yet calibrated for this repo)"
                        % ", ".join(dead[:5]) + (" +%d more" % (len(dead) - 5) if len(dead) > 5 else "")))
    if total >= MIN_FILES_FOR_SHARE and per_lane["Critical"] / float(total) > CRITICAL_SHARE_WARN:
        results.append(("rule-critical-share", WARN,
                        "%d%% of tracked files are Critical (heuristic limit %d%%): a lane that fires this often gets ignored"
                        % (round(100.0 * per_lane["Critical"] / total), int(CRITICAL_SHARE_WARN * 100))))
    return results


class ProfileError(ValueError):
    """An input is outside the deliberately bounded inspection profile."""


def _yaml_comment(line):
    quoted, escaped = None, False
    for i, char in enumerate(line):
        if escaped:
            escaped = False
        elif quoted == '"' and char == "\\":
            escaped = True
        elif char == quoted:
            quoted = None
        elif quoted is None and char in "\"'":
            quoted = char
        elif quoted is None and char == "#" and (i == 0 or line[i - 1].isspace()):
            return line[:i].rstrip()
    return line.rstrip()


def _yaml_scalar(value):
    """Only single-line scalars and flat flow values; never aliases, tags or folding."""
    if value.startswith("{") and value.endswith("}"):
        result = {}
        for item in re.split(r",(?=(?:[^\"']|\"[^\"]*\"|'[^']*')*$)", value[1:-1]):
            if not item.strip() and not result:
                continue
            match = re.fullmatch(r"\s*([A-Za-z_][\w-]*):\s+(.+)", item)
            if not match or match[1] in result:
                raise ProfileError("unsupported or duplicate flow mapping key")
            scalar = _yaml_scalar(match[2].strip())
            if isinstance(scalar, (dict, list)):
                raise ProfileError("nested flow values are unsupported")
            result[match[1]] = scalar
        return result
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1]
        if not body.strip():
            return []
        items = re.split(r",(?=(?:[^\"']|\"[^\"]*\"|'[^']*')*$)", body)
        parsed = [_yaml_scalar(item.strip()) for item in items]
        if any(isinstance(item, (dict, list)) for item in parsed):
            raise ProfileError("nested flow values are unsupported")
        return parsed
    if value.startswith('"'):
        try:
            result = json.loads(value)
            if isinstance(result, str):
                return result
        except ValueError:
            pass
        raise ProfileError("unsupported quoted scalar")
    if value.startswith("'"):
        if re.fullmatch(r"'(?:[^']|'')*'", value):
            return value[1:-1].replace("''", "'")
        raise ProfileError("unsupported quoted scalar")
    if not value or value[0] in "&*!|>[]{}`%@" or ": " in value or " #" in value:
        raise ProfileError("unsupported YAML scalar or indirection")
    if value in ("true", "false"):
        return value == "true"
    if value in ("null", "~"):
        return None
    if re.fullmatch(r"0|[1-9][0-9]*", value):
        return int(value)
    return value


def parse_workflow(text):
    """Parse a small, two-space YAML subset, rejecting ambiguity rather than guessing.

    Mapping keys, block sequences, flat flow values and literal blocks are supported.
    Duplicate keys, tabs, anchors, merges, tags, multiline scalars and extra documents
    are not. Semantic allowlists below are separate from this structural parser.
    """
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise ProfileError("workflow unreadable or too large")
    if re.search(r"[\x00-\x09\x0b-\x1f\x7f\ufeff]", text):
        raise ProfileError("unsupported workflow control character")
    lines, tokens, i = text.splitlines(), [], 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        line = _yaml_comment(raw).strip()
        if not line:
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ProfileError("workflow requires two-space indentation")
        if line.startswith("- "):
            tokens.append((indent, "-", None))
            indent += 2
            line = line[2:]
        literal = None
        if re.fullmatch(r"[A-Za-z_][\w-]*: \|", line):
            content = []
            while i < len(lines):
                child = lines[i]
                if child.strip() and len(child) - len(child.lstrip(" ")) <= indent:
                    break
                if child.strip() and not child.startswith(" " * (indent + 2)):
                    raise ProfileError("unsupported literal block indentation")
                content.append(child[indent + 2:] if child.strip() else "")
                i += 1
            literal = "\n".join(content) + "\n"
        tokens.append((indent, line, literal))
    if not tokens or tokens[0][0] != 0 or len(tokens) > 10000:
        raise ProfileError("empty, oversized or indented workflow")

    def block(pos, indent, depth=0):
        if depth > 32 or tokens[pos][0] != indent:
            raise ProfileError("unsupported workflow nesting")
        sequence = tokens[pos][1] == "-"
        result = [] if sequence else {}
        while pos < len(tokens) and tokens[pos][0] == indent:
            _, line, literal = tokens[pos]
            pos += 1
            if sequence:
                if line != "-" or pos == len(tokens):
                    raise ProfileError("unsupported sequence item")
                value, pos = block(pos, indent + 2, depth + 1)
                result.append(value)
                continue
            match = re.fullmatch(r"([A-Za-z_][\w-]*|'[A-Za-z_][\w-]*'|\"[A-Za-z_][\w-]*\"):(?: (.*))?", line)
            if not match:
                if not result and depth and (pos == len(tokens) or tokens[pos][0] < indent):
                    return _yaml_scalar(line), pos
                raise ProfileError("unsupported workflow mapping")
            key, raw_value = match.groups()
            key = key.strip("'\"")
            if key in result:
                raise ProfileError("duplicate workflow key: %s" % key)
            if literal is not None:
                value = literal
            elif raw_value:
                value = _yaml_scalar(raw_value)
            elif pos < len(tokens) and tokens[pos][0] > indent:
                value, pos = block(pos, indent + 2, depth + 1)
            else:
                value = None
            result[key] = value
            if pos < len(tokens) and tokens[pos][0] > indent:
                raise ProfileError("unsupported multiline scalar or indentation")
        return result, pos

    result, consumed = block(0, 0)
    if consumed != len(tokens) or not isinstance(result, dict):
        raise ProfileError("unsupported workflow document")
    return result


_BASE = "${{ github.event.pull_request.base.sha }}"
_HEAD = "${{ github.event.pull_request.head.sha }}"
_EVENTS = {"opened", "synchronize", "reopened", "edited", "ready_for_review"}
_GATE_COMMAND = ('python3 -I trusted/scripts/evidence_check.py --ci '
                 '--config trusted/scripts/lane-config.yaml --repo-root change '
                 '--base="$BASE_SHA" --head="$HEAD_SHA" --emit-json evidence-manifest.json '
                 '--event-path "$GITHUB_EVENT_PATH"')
_CI_NAMES = ("no-pr-target", "trigger", "edited-trigger", "invokes-gate", "fetch-depth",
             "trusted-tooling", "isolated-python", "permissions", "persist-credentials", "pinned-actions",
             "manifest-artifact")


def scanner_references():
    """Read approvals from this inspector's bundle, never from the inspected repo."""
    prefix = "trusted scanner-profiles.json: "

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        with open(os.path.join(HERE, "scanner-profiles.json"), "rb") as handle:
            raw = handle.read(MAX_FILE_BYTES + 1)
    except OSError as exc:
        raise ProfileError(prefix + "cannot read registry (%s)" % type(exc).__name__) from None
    if len(raw) > MAX_FILE_BYTES:
        raise ProfileError(prefix + "registry exceeds the size limit")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ProfileError(prefix + "invalid UTF-8 JSON (%s)" % type(exc).__name__) from None
    if not isinstance(data, dict) or set(data) != {"version", "scanner", "approved"}:
        raise ProfileError(prefix + "expected version, scanner and approved fields")
    if type(data["version"]) is not int or data["version"] != 1:
        raise ProfileError(prefix + "unsupported registry version")
    if data["scanner"] != "gitleaks/gitleaks-action":
        raise ProfileError(prefix + "unsupported scanner owner/repository")
    if not isinstance(data["approved"], list) or not data["approved"]:
        raise ProfileError(prefix + "approved must be a nonempty list")
    releases, references = set(), set()
    for entry in data["approved"]:
        if not isinstance(entry, dict) or set(entry) != {"release", "sha"}:
            raise ProfileError(prefix + "each approval requires only release and sha")
        release, sha = entry["release"], entry["sha"]
        if not isinstance(release, str) or not release or release.strip() != release or not release.isprintable():
            raise ProfileError(prefix + "release must be a nonempty printable label")
        if not isinstance(sha, str) or not _SHA.fullmatch(sha):
            raise ProfileError(prefix + "approval requires a full lowercase commit SHA")
        reference = data["scanner"] + "@" + sha
        if release in releases or reference in references:
            raise ProfileError(prefix + "duplicate release or commit approval")
        releases.add(release)
        references.add(reference)
    return references


def workflow_results(text, scanner=False):
    prefix = "scanner-" if scanner else "ci-"
    if scanner:
        try:
            approved_scanners = scanner_references()
        except ProfileError as exc:
            return [("scanner-profile-data", FAIL, str(exc))]
    try:
        doc = parse_workflow(text)
    except ProfileError as exc:
        return [(prefix + "workflow-profile", UNVERIFIED, str(exc))] + [
            (prefix + name, UNVERIFIED, "unsupported workflow; execution not inferred from text") for name in _CI_NAMES]
    events, jobs = doc.get("on"), doc.get("jobs")
    job_id = "scan" if scanner else "evidence"
    job = jobs.get(job_id) if isinstance(jobs, dict) else None
    shape = (set(doc) <= {"name", "on", "permissions", "concurrency", "jobs"} and
             ("name" not in doc or isinstance(doc["name"], str) and "${{" not in doc["name"]) and
             isinstance(events, dict) and isinstance(jobs, dict) and set(jobs) == {job_id} and
             isinstance(job, dict))
    job = job if isinstance(job, dict) else {}
    steps = job.get("steps")
    shape = shape and (set(job) <= {"name", "runs-on", "timeout-minutes", "steps"} and
                       job.get("name", job_id) == ("gitleaks" if scanner else "evidence") and
                       job.get("runs-on") == "ubuntu-latest" and isinstance(steps, list) and
                       len(steps) == (2 if scanner else 4))
    steps = steps if isinstance(steps, list) else []
    shape = shape and all(isinstance(step, dict) and set(step) <= {"name", "uses", "with", "env", "run"}
                          and ("name" not in step or isinstance(step["name"], str)) for step in steps)
    if "concurrency" in doc:
        shape = shape and doc["concurrency"] == {
            "group": "sdlc-gate-${{ github.event.pull_request.number }}", "cancel-in-progress": True} and not scanner
        shape = shape and doc["concurrency"].get("cancel-in-progress") is True
    if scanner:
        shape = shape and ("timeout-minutes" not in job or type(job["timeout-minutes"]) is int
                           and job["timeout-minutes"] == 5)
    else:
        shape = shape and type(job.get("timeout-minutes")) is int and job["timeout-minutes"] == 5
    events = events if isinstance(events, dict) else {}
    on_pr = "pull_request" in events
    pr = events.get("pull_request")
    types = pr.get("types") if isinstance(pr, dict) else None
    event_profile = (set(events) <= ({"pull_request", "push"} if scanner else {"pull_request"}) and on_pr)
    if scanner:
        event_profile = event_profile and pr is None
        if "push" in events:
            push = events["push"]
            event_profile = event_profile and (isinstance(push, dict) and set(push) == {"branches"} and
                isinstance(push["branches"], list) and bool(push["branches"]) and
                all(isinstance(b, str) and re.fullmatch(r"[\w./-]+", b) for b in push["branches"]))
    else:
        event_profile = event_profile and isinstance(pr, dict) and set(pr) == {"types"} and isinstance(types, list)
        event_profile = event_profile and all(isinstance(t, str) for t in types) and len(set(types)) == len(types)
        event_profile = event_profile and set(types) <= _EVENTS
    shape = shape and event_profile
    results = [(prefix + "workflow-profile", OK if shape else UNVERIFIED,
                "recognized bounded workflow structure (not execution proof)" if shape else
                "unsupported workflow shape, condition, permission override or indirection")]

    def add(name, good, bad_status, detail):
        results.append((prefix + name, OK if good else bad_status, detail))

    add("no-pr-target", "pull_request_target" not in events, FAIL, "pull_request_target is outside the read-only profile")
    add("trigger", on_pr, FAIL, "pull_request trigger present" if on_pr else "missing pull_request trigger")
    expected_perms = {"contents": "read", "pull-requests": "read"} if scanner else {"contents": "read"}
    add("permissions", doc.get("permissions") == expected_perms, WARN,
        "requires exactly read-only permissions: %s" % ", ".join(sorted(expected_perms)))
    actions = [s.get("uses") for s in steps if isinstance(s, dict) and "uses" in s]
    unpinned = sorted(set(a for a in actions if isinstance(a, str) and
                          not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", a)))
    pinned = len(actions) == (2 if scanner else 3) and not unpinned and all(isinstance(a, str) for a in actions)
    add("pinned-actions", pinned, WARN, "all actions pinned to commit SHAs" if pinned else
        "not pinned to a commit SHA: %s" % clip(", ".join(unpinned) or "missing/unsupported action"))
    checkouts = [s for s in steps if isinstance(s, dict) and isinstance(s.get("uses"), str)
                 and s["uses"].startswith("actions/checkout@")]
    add("persist-credentials", len(checkouts) == (1 if scanner else 2) and all(
        isinstance(s.get("with"), dict) and s["with"].get("persist-credentials") is False for s in checkouts),
        WARN, "every checkout requires persist-credentials: false")
    if not shape:
        results.append((prefix + "invokes-gate", UNVERIFIED, "unsupported workflow: no execution claim"))
        return results
    without_name = lambda step: {k: v for k, v in step.items() if k != "name"}
    if scanner:
        checkout, scan = (without_name(s) for s in steps)
        checkout_ok = (set(checkout) == {"uses", "with"} and isinstance(checkout["uses"], str) and
                       checkout["uses"].startswith("actions/checkout@") and
                       checkout["with"] == {"fetch-depth": 0, "persist-credentials": False} and
                       type(checkout["with"].get("fetch-depth")) is int)
        env = scan.get("env")
        scanner_ref = scan.get("uses")
        supported_scanner = isinstance(scanner_ref, str) and scanner_ref in approved_scanners
        scan_ok = (set(scan) == {"uses", "env"} and supported_scanner and isinstance(env, dict) and
                   set(env) <= {"GITHUB_TOKEN", "GITLEAKS_ENABLE_COMMENTS", "GITLEAKS_LICENSE"} and
                   env.get("GITHUB_TOKEN") == "${{ secrets.GITHUB_TOKEN }}" and
                   (env.get("GITLEAKS_ENABLE_COMMENTS") == "false" or env.get("GITLEAKS_ENABLE_COMMENTS") is False) and
                   ("GITLEAKS_LICENSE" not in env or env["GITLEAKS_LICENSE"] == "${{ secrets.GITLEAKS_LICENSE }}"))
        add("fetch-depth", checkout_ok, FAIL, "gitleaks requires full-history checkout without persisted credentials")
        add("invokes-gate", scan_ok, FAIL,
            "gitleaks pinned supported action requires GITHUB_TOKEN, read-only PR access and comments disabled; "
            "license/fork availability and hosted scans are not established by workflow recognition"
            if supported_scanner else
            "gitleaks action reference is not approved by trusted scanner-profiles.json: " + clip(scanner_ref))
        return results
    base, head, gate, upload = (without_name(s) for s in steps)
    base_with, head_with = base.get("with"), head.get("with")
    base_ok = (set(base) == {"uses", "with"} and isinstance(base.get("uses"), str) and
               base["uses"].startswith("actions/checkout@") and
               base_with == {"ref": _BASE, "path": "trusted", "persist-credentials": False})
    head_ok = (set(head) == {"uses", "with"} and isinstance(head.get("uses"), str) and
               head["uses"].startswith("actions/checkout@") and
               head_with == {"ref": _HEAD, "path": "change", "fetch-depth": 0, "persist-credentials": False} and
               type(head_with.get("fetch-depth")) is int)
    command = gate.get("run")
    command = command.replace("\\\n", " ").strip() if isinstance(command, str) else ""
    single_command = "\n" not in command and "\r" not in command
    command = " ".join(command.split())
    isolated = command == _GATE_COMMAND
    legacy = command == _GATE_COMMAND.replace("python3 -I ", "python3 ")
    gate_ok = (set(gate) == {"env", "run"} and gate.get("env") == {"BASE_SHA": _BASE, "HEAD_SHA": _HEAD}
               and single_command and (isolated or legacy))
    add("edited-trigger", isinstance(types, list) and set(types) == _EVENTS, WARN,
        "requires open, synchronize, reopen, edited and ready_for_review events; old-event reruns use the old PR body")
    add("invokes-gate", gate_ok, FAIL, "recognized evidence_check.py --ci command with explicit base/head/event" if gate_ok
        else "unsupported gate command; requires --ci and explicit trusted config, base/head and event (no success fallback)")
    add("fetch-depth", isinstance(head_with, dict) and type(head_with.get("fetch-depth")) is int
        and head_with["fetch-depth"] == 0, FAIL, "head checkout requires fetch-depth: 0")
    add("trusted-tooling", base_ok and head_ok and gate_ok, WARN,
        "recognized base-branch checkout (trusted/) and explicit candidate checkout" if base_ok and head_ok and gate_ok else
        "tooling/config must run from the base checkout with the explicit candidate revision")
    add("isolated-python", isolated and gate_ok, WARN, "gate must use python3 -I without shell indirection")
    upload_ok = (set(upload) == {"uses", "with"} and isinstance(upload.get("uses"), str) and
                 upload["uses"].startswith("actions/upload-artifact@") and
                 upload.get("with") == {"name": "evidence-manifest", "path": "evidence-manifest.json",
                                        "if-no-files-found": "error"})
    add("manifest-artifact", upload_ok, FAIL,
        "evidence manifest artifact is uploaded from a pinned action" if upload_ok else
        "requires actions/upload-artifact@<pinned SHA> with the evidence-manifest.json path")
    return results


def check_workflow(root):
    results = []
    for rel, scanner in (("sdlc-gate.yml", False), ("gitleaks.yml", True)):
        path = os.path.join(root, ".github", "workflows", rel)
        if not os.path.isfile(path):
            if scanner:
                try:
                    scanner_references()
                except ProfileError as exc:
                    results.append(("scanner-profile-data", FAIL, str(exc)))
            continue  # strict hosted inspection requires both; preserve legacy installation diagnostics
        results += workflow_results(read_text(path), scanner)
    return results


HOOK_MARKER = "sdlc-pre-push"


def check_hook(root):
    """Is a pre-push hook that git will actually RUN installed, and is it ours?

    Git only runs a file named exactly 'pre-push' (no extension), found in core.hooksPath or
    .git/hooks, so presence of hooks/pre-push.sh proves nothing. Ask git where it will look.
    """
    if not os.path.isfile(os.path.join(root, "hooks", "pre-push.sh")):
        return []
    if not in_git(root):
        return [("hook-active", UNVERIFIED, "not a git work tree")]
    code, out, _ = git(root, "rev-parse", "--git-path", "hooks/pre-push")
    if code != 0 or not out.strip():
        return [("hook-active", UNVERIFIED, "could not ask git where pre-push hooks live")]
    target = out.strip()
    target = target if os.path.isabs(target) else os.path.join(root, target)
    try:
        shown = os.path.relpath(target, root)
    except ValueError:
        # A linked worktree can share hooks on another Windows volume.
        shown = target
    if not os.path.isfile(target):
        return [("hook-active", WARN,
                 "git would run %s and nothing is there (git only runs a file named exactly 'pre-push', so hooks/pre-push.sh alone is "
                 "never run). Fix: add hooks/pre-push (the dispatcher) and `git config core.hooksPath hooks`, or copy "
                 "hooks/pre-push.sh to .git/hooks/pre-push" % shown)]
    if not os.access(target, os.X_OK):
        return [("hook-active", WARN, "%s is not executable, so git skips it: chmod +x %s" % (shown, shown))]
    text = read_text(target) or ""
    if HOOK_MARKER not in text:
        return [("hook-active", WARN, "a pre-push hook is active (%s) but it is not the sdlc hook; the lane warning will not run" % shown)]
    return [("hook-active", OK, "git runs %s (advisory only: `git push --no-verify` skips it)" % shown)]


def _codeowners_path(root):
    for rel in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):  # GitHub's lookup order
        if os.path.isfile(os.path.join(root, rel)):
            return rel
    return None


def check_codeowners(root):
    rel = _codeowners_path(root)
    if rel is None:
        return [("codeowners", WARN,
                 "no CODEOWNERS file: nothing requires an owner's review when a PR edits the workflow or scripts")]
    if lanelib is None:
        return [("codeowners", UNVERIFIED, "lane.py not importable, so CODEOWNERS patterns were not evaluated")]
    text = read_text(os.path.join(root, rel)) or ""
    entries = []
    for line in text.splitlines():
        line = re.sub(r"(^|\s)#.*$", "", line).strip()
        if not line:
            continue
        parts = line.split()
        try:
            entries.append((lanelib.compile_pattern(parts[0]), len(parts) > 1))
        except lanelib.ConfigError:
            continue
    uncovered = []
    for target in GATE_FILES:
        covered = False
        for matches, has_owner in entries:  # last matching pattern wins, and an owner-less line un-owns the path
            if matches(target):
                covered = has_owner
        if not covered:
            uncovered.append(target)
    if uncovered:
        return [("codeowners", WARN, "%s: gate files with no code owner: %s" % (rel, ", ".join(uncovered)))]
    return [("codeowners", OK, "%s covers the gate files. Whether review is REQUIRED is a branch-protection "
                               "setting (see --check-branch-protection)" % rel)]


def check_default_branch(root):
    if not in_git(root):
        return [("tooling-on-default-branch", UNVERIFIED, "not a git work tree")]
    results = []
    code, out, _ = git(root, "status", "--porcelain", "--", "scripts", ".github", "hooks")
    pending = [ln for ln in out.splitlines() if ln.strip() and "__pycache__" not in ln and not ln.endswith(".pyc")] \
        if code == 0 else []
    if pending:
        results.append(("gate-files-committed", WARN,
                        "%d uncommitted change(s) under scripts/, .github/ or hooks/: the gate only reads COMMITTED "
                        "tooling from the base branch" % len(pending)))
    code, out, _ = git(root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
    if code != 0 or not out.strip():
        results.append(("tooling-on-default-branch", UNVERIFIED,
                        "origin/HEAD is unknown; run `git remote set-head origin -a` and re-run"))
        return results
    ref = out.strip().replace("refs/remotes/", "", 1)
    missing = [rel for rel in TOOLING if git(root, "cat-file", "-e", "%s:%s" % (ref, rel))[0] != 0]
    if missing:
        results.append(("tooling-on-default-branch", WARN,
                        "missing on %s (as of the last fetch): %s. The gate reads its tooling from the base branch, so "
                        "PRs error until it is merged there" % (ref, ", ".join(missing))))
    else:
        results.append(("tooling-on-default-branch", OK, "present on %s (as of the last fetch)" % ref))
    return results


def check_shallow(root):
    if not in_git(root):
        return []
    code, out, _ = git(root, "rev-parse", "--is-shallow-repository")
    if code == 0 and out.strip() == "true":
        return [("shallow-clone", WARN, "this is a shallow clone: `lane.py --base` and the merge-base diff can fail here")]
    return []


# --------------------------------------------------------------------------
# opt-in remote checks (REST GETs, one fixed read-only GraphQL POST)
# --------------------------------------------------------------------------

_REMOTE = re.compile(r"^(?:https://(?:[^@/]+@)?github\.com/|git@github\.com:|ssh://git@github\.com/)"
                     r"([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")


def _gh_result(command):
    env = dict(os.environ, GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1", GH_HOST="github.com")
    code, out, err = run(command, env=env)
    if code == 0:
        try:
            if len(out) > 16000000:
                return "error", None, "provider response exceeds inspection limit"
            return "ok", json.loads(out, object_pairs_hook=_unique_json), ""
        except ValueError:
            return "error", None, "unparseable response"
    return "error", None, clip(err or out or "gh api failed", 120)


def _gh(path):
    return _gh_result(["gh", "api", path, "--method", "GET", "--hostname", "github.com",
                       "-H", "Accept: application/vnd.github+json", "-H", "X-GitHub-Api-Version: 2022-11-28"])


_QUEUE_QUERY = ('query SdlcMergeQueue($owner: String!, $repo: String!, $branch: String!) { '
                'repository(owner: $owner, name: $repo) { mergeQueue(branch: $branch) { id } } }')


def _gh_queue(owner, repo, branch):
    # The sole POST operation: fixed query text, with all external input in variables.
    return _gh_result(["gh", "api", "graphql", "--method", "POST", "--hostname", "github.com",
                       "-f", "query=" + _QUEUE_QUERY, "-f", "owner=" + owner,
                       "-f", "repo=" + repo, "-f", "branch=" + branch])


def _classic_queue(slug, branch):
    owner, repo = slug.split("/")
    state, response, error = _gh_queue(owner, repo, branch)
    unavailable = (UNVERIFIED, "classic merge-queue state unverified: missing/unsupported GraphQL data")
    if state != "ok":
        return UNVERIFIED, "classic merge-queue state unverified (%s)" % clip(error)
    if not isinstance(response, dict) or ("errors" in response and response["errors"] != []):
        return unavailable
    data = response.get("data")
    repo = data.get("repository") if isinstance(data, dict) else None
    if not isinstance(repo, dict) or "mergeQueue" not in repo:
        return unavailable
    queue = repo["mergeQueue"]
    if queue is None:
        return OK, "GraphQL observed no merge queue on %s" % branch
    if isinstance(queue, dict) and isinstance(queue.get("id"), str) and queue["id"]:
        return FAIL, "merge queue enabled on %s: unsupported without a separately supported merge-group workflow" % branch
    return unavailable


def _context_matches(context, check_name):
    return context == check_name


def _unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _actions_identity():
    state, app, error = _gh("apps/github-actions")
    if (state == "ok" and isinstance(app, dict) and type(app.get("id")) is int and app["id"] > 0 and
            app.get("slug") == "github-actions" and isinstance(app.get("owner"), dict) and
            app["owner"].get("login") == "github"):
        return app["id"], "GitHub Actions application github-actions (id %d), resolved from github.com/apps metadata" % app["id"]
    return None, "GitHub Actions application identity unverified (%s)" % (error or "incomplete/unexpected app metadata")


def check_branch_protection(root, check_name):
    name = "required-check"
    if not in_git(root):
        return [(name, UNVERIFIED, "not a git work tree")]
    code, out, _ = git(root, "remote", "get-url", "origin")
    match = _REMOTE.match(out.strip()) if code == 0 else None
    if not match:
        return [(name, UNVERIFIED, "origin is not a github.com remote, so branch protection cannot be read")]
    slug = "%s/%s" % match.groups()
    if shutil.which("gh") is None:
        return [(name, UNVERIFIED, "gh CLI not found; install it and run `gh auth login`, or check branch protection by hand")]
    state, repo, err = _gh("repos/%s" % slug)
    if state != "ok" or not isinstance(repo, dict) or not repo.get("default_branch"):
        return [(name, UNVERIFIED, "could not read the repository (%s)" % (err or "no default branch in response"))]
    branch = repo["default_branch"]
    if not isinstance(branch, str) or not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
        return [(name, UNVERIFIED, "unsupported default branch name")]
    encoded_branch = quote(branch, safe="")
    app_id, app_detail = _actions_identity()

    matched, unpinned, answered, errors = False, False, 0, []
    owners_required, owners_known, admins_enforced = False, False, None

    try:
        rules = _provider_pages("repos/%s/rules/branches/%s" % (slug, encoded_branch))
        state, err = "ok", ""
    except ProfileError as exc:
        state, rules, err = "error", None, str(exc)
    if state == "ok" and isinstance(rules, list):
        answered += 1
        for rule in rules:
            if not isinstance(rule, dict):
                errors.append("rulesets: incomplete rule")
                continue
            params = rule.get("parameters") or {}
            if not isinstance(params, dict):
                errors.append("rulesets: incomplete parameters")
                continue
            if rule.get("type") == "required_status_checks":
                checks = params.get("required_status_checks")
                if not isinstance(checks, list):
                    errors.append("rulesets: incomplete check list")
                    continue
                for item in checks:
                    if not isinstance(item, dict):
                        errors.append("rulesets: incomplete check")
                        continue
                    if _context_matches(str(item.get("context", "")), check_name):
                        matched = True
                        if (app_id is None or type(item.get("integration_id")) is not int or
                                item["integration_id"] != app_id):
                            unpinned = True
            if rule.get("type") == "pull_request":
                owners_known = True
                owners_required = owners_required or bool(params.get("require_code_owner_review"))
    else:
        errors.append("rulesets: %s" % (err or "unexpected response"))

    state, prot, err = _gh("repos/%s/branches/%s/protection" % (slug, encoded_branch))
    if state == "ok" and isinstance(prot, dict):
        answered += 1
        required = prot.get("required_status_checks") or {}
        if not isinstance(required, dict):
            required = {}
            errors.append("branch protection: incomplete check settings")
        classic_checks = required.get("checks", [])
        if not isinstance(classic_checks, list):
            classic_checks = []
            errors.append("branch protection: incomplete check list")
        for item in classic_checks:
            if not isinstance(item, dict):
                errors.append("branch protection: incomplete check")
                continue
            if _context_matches(str(item.get("context", "")), check_name):
                matched = True
                if app_id is None or type(item.get("app_id")) is not int or item["app_id"] != app_id:
                    unpinned = True
        classic_contexts = required.get("contexts", [])
        if not isinstance(classic_contexts, list) or not all(isinstance(c, str) for c in classic_contexts):
            classic_contexts = []
            errors.append("branch protection: incomplete check contexts")
        for context in classic_contexts:
            if _context_matches(str(context), check_name) and not matched:
                matched, unpinned = True, True
        reviews = prot.get("required_pull_request_reviews")
        if isinstance(reviews, dict):
            owners_known = True
            owners_required = owners_required or bool(reviews.get("require_code_owner_reviews"))
        admins_enforced = prot["enforce_admins"].get("enabled") if isinstance(prot.get("enforce_admins"), dict) else None
    elif "not protected" in err.lower():
        answered += 1  # an authoritative "no classic protection"
    else:
        errors.append("branch protection: %s" % (err or "unexpected response"))

    results = []
    if matched:
        results.append((name, (UNVERIFIED if app_id is None else WARN) if unpinned else OK,
                        "'%s' is a required status check on %s; %s" % (check_name, branch, app_detail)))
        if unpinned:
            results.append(("required-check-source", WARN,
                            "required check '%s' lacks the exact authoritative GitHub Actions application identity" % check_name))
    elif not errors:  # both sources answered authoritatively and neither lists the check
        results.append((name, FAIL, "'%s' is NOT a required status check on %s: the gate cannot block merges" % (check_name, branch)))
    else:
        results.append((name, UNVERIFIED, "could not read everything (%s); not proven either way" % "; ".join(errors)))

    if owners_known and answered:
        results.append(("codeowners-required", OK if owners_required else WARN,
                        "code-owner review is required on %s" % branch if owners_required else
                        "code-owner review is not required on %s: CODEOWNERS entries are advisory" % branch))
    if admins_enforced is False:
        results.append(("admins-bound", WARN, "branch protection does not apply to admins: they can merge past the gate"))
    return results


def _provider(path, expected):
    state, value, error = _gh(path)
    if state != "ok" or not isinstance(value, expected):
        raise ProfileError("%s unverified (%s)" % (clip(path), error or "unexpected provider response"))
    return value


def _provider_pages(path):
    values = []
    separator = "&" if "?" in path else "?"
    for page in range(1, 11):
        entries = _provider(path + separator + "per_page=100&page=%d" % page, list)
        if len(entries) > 100:
            raise ProfileError("oversized provider page; completeness unverified")
        values.extend(entries)
        if len(entries) < 100:
            return values
    raise ProfileError("provider pagination limit exceeded; completeness/bypass visibility unverified")


def _boolean(data, key, label):
    if not isinstance(data, dict) or type(data.get(key)) is not bool:
        raise ProfileError("%s unverified: missing or non-boolean %s" % (label, key))
    return data[key]


def _rule_signature(rule):
    if not isinstance(rule, dict) or not isinstance(rule.get("type"), str):
        raise ProfileError("ruleset rule type unverified")
    params = rule.get("parameters", {})
    if not isinstance(params, dict):
        raise ProfileError("ruleset parameters unverified")
    return json.dumps([rule["type"], params], sort_keys=True)


def _ruleset_applies(conditions, branch):
    if not isinstance(conditions, dict) or set(conditions) != {"ref_name"}:
        raise ProfileError("unsupported ruleset conditions; applicability unverified")
    refs = conditions["ref_name"]
    if not isinstance(refs, dict) or set(refs) != {"include", "exclude"}:
        raise ProfileError("ruleset ref conditions unverified")

    def matches(pattern):
        if pattern in ("~ALL", "~DEFAULT_BRANCH"):
            return True  # the inspected branch is the provider's default branch
        if not isinstance(pattern, str) or not re.fullmatch(r"refs/heads/[A-Za-z0-9._/-]+", pattern):
            raise ProfileError("unsupported ruleset ref pattern; applicability unverified")
        return pattern == "refs/heads/" + branch

    selected = {}
    for key in ("include", "exclude"):
        if not isinstance(refs[key], list):
            raise ProfileError("ruleset ref conditions unverified")
        selected[key] = [matches(pattern) for pattern in refs[key]]
    return any(selected["include"]) and not any(selected["exclude"])


def enforcement_settings(prefix, branch, app_id):
    """Combine effective rules only after checking their provenance and bypass visibility."""
    encoded = quote(branch, safe="")
    effective = _provider_pages(prefix + "/rules/branches/" + encoded)
    effective_by_id = {}
    for rule in effective:
        _rule_signature(rule)
        rid = rule.get("ruleset_id")
        if type(rid) is not int or rid <= 0:
            raise ProfileError("effective ruleset identity unverified")
        effective_by_id.setdefault(rid, []).append(rule)

    listed = _provider_pages(prefix + "/rulesets?includes_parents=true")

    checks, reviews, bypasses, seen = [], [], [], set()
    prohibit_delete = prohibit_force = False

    def status_checks(params, classic=False):
        key = "checks" if classic else "required_status_checks"
        items = params.get(key)
        if not isinstance(items, list):
            raise ProfileError("required check list unverified")
        fresh = _boolean(params, "strict" if classic else "strict_required_status_checks_policy", "up-to-date checks")
        if not classic and _boolean(params, "do_not_enforce_on_create", "check creation bypass"):
            bypasses.append("ruleset skips checks on branch creation")
        contexts = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("context"), str) or not item["context"]:
                raise ProfileError("required check context unverified")
            source = item.get("app_id" if classic else "integration_id")
            if source is not None and type(source) is not int:
                raise ProfileError("%s application identity unverified" % clip(item["context"]))
            contexts.append(item["context"])
            checks.append((item["context"], source, fresh))
        if classic:
            names = params.get("contexts")
            if not isinstance(names, list) or not all(isinstance(c, str) for c in names):
                raise ProfileError("required check contexts unverified")
            for name in names:
                if name not in contexts:
                    checks.append((name, None, fresh))

    def review_rule(params, classic=False):
        count = params.get("required_approving_review_count")
        if type(count) is not int or count < 0:
            raise ProfileError("required pull request review count unverified")
        owners = _boolean(params, "require_code_owner_reviews" if classic else "require_code_owner_review", "owner review")
        stale = _boolean(params, "dismiss_stale_reviews" if classic else "dismiss_stale_reviews_on_push", "fresh review")
        last = _boolean(params, "require_last_push_approval", "fresh review")
        reviews.append((count, owners, stale or last))
        if classic:
            allowances = params.get("bypass_pull_request_allowances")
            if not isinstance(allowances, dict) or not {"users", "teams", "apps"} <= set(allowances):
                raise ProfileError("classic pull request bypass allowances unverified")
            for kind in ("users", "teams", "apps"):
                actors = allowances[kind]
                if not isinstance(actors, list) or not all(isinstance(a, dict) for a in actors):
                    raise ProfileError("classic bypass actors unverified")
                if actors:
                    names = [str(a.get("login") or a.get("slug") or a.get("id") or "unknown") for a in actors]
                    bypasses.append("classic %s: %s" % (kind, clip(", ".join(names))))

    slug = prefix[len("repos/"):]
    for summary in listed:
        if not isinstance(summary, dict) or type(summary.get("id")) is not int or summary["id"] <= 0:
            raise ProfileError("ruleset listing identity unverified")
        rid = summary["id"]
        if rid in seen:
            raise ProfileError("duplicate ruleset listing; completeness unverified")
        seen.add(rid)
        mode, target = summary.get("enforcement"), summary.get("target")
        if mode not in ("active", "evaluate", "disabled") or target not in ("branch", "tag", "push"):
            raise ProfileError("unsupported ruleset mode or target")
        if mode != "active" or target != "branch":
            if rid in effective_by_id:
                raise ProfileError("effective ruleset disagrees with listed enforcement/target")
            continue
        source_type, source = summary.get("source_type"), summary.get("source")
        if source_type == "Repository" and source == slug:
            route = prefix + "/rulesets/%d" % rid
        elif source_type == "Organization" and source == slug.split("/")[0]:
            route = "orgs/%s/rulesets/%d" % (quote(source, safe=""), rid)
        else:
            raise ProfileError("unsupported ruleset source; inherited bypass settings unverified")
        detail = _provider(route, dict)
        if any(detail.get(key) != summary.get(key) for key in ("id", "source_type", "source", "enforcement", "target")):
            raise ProfileError("ruleset metadata disagrees with listing; re-inspect settings")
        applies = _ruleset_applies(detail.get("conditions"), branch)
        rules = detail.get("rules")
        if not isinstance(rules, list):
            raise ProfileError("ruleset rules unverified")
        signatures = sorted(_rule_signature(r) for r in rules)
        expected = effective_by_id.get(rid, [])
        if not applies:
            if expected:
                raise ProfileError("effective ruleset applicability disagrees with conditions")
            continue
        if signatures != sorted(_rule_signature(r) for r in expected) or any(
                r.get("ruleset_source_type") != source_type or r.get("ruleset_source") != source for r in expected):
            raise ProfileError("effective ruleset contents or source unverified")
        actors = detail.get("bypass_actors")
        if not isinstance(actors, list):
            raise ProfileError("ruleset %d bypass actors unverified (missing/inaccessible)" % rid)
        for actor in actors:
            if not isinstance(actor, dict) or not {"actor_id", "actor_type", "bypass_mode"} <= set(actor):
                raise ProfileError("ruleset bypass actor metadata unverified")
            bypasses.append("ruleset %d: %s %s (%s)" % (
                rid, clip(actor["actor_type"]), clip(actor["actor_id"]), clip(actor["bypass_mode"])))
        for rule in rules:
            kind, params = rule["type"], rule.get("parameters", {})
            if kind == "required_status_checks":
                if set(params) - {"required_status_checks", "strict_required_status_checks_policy", "do_not_enforce_on_create"}:
                    raise ProfileError("unsupported status-check ruleset parameters")
                status_checks(params)
            elif kind == "pull_request":
                if set(params) - {"required_approving_review_count", "require_code_owner_review",
                                  "dismiss_stale_reviews_on_push", "require_last_push_approval",
                                  "required_review_thread_resolution", "allowed_merge_methods"}:
                    raise ProfileError("unsupported pull request ruleset parameters")
                review_rule(params)
            elif kind in ("deletion", "non_fast_forward", "required_signatures", "required_linear_history") and not params:
                prohibit_delete = prohibit_delete or kind == "deletion"
                prohibit_force = prohibit_force or kind == "non_fast_forward"
            else:
                raise ProfileError("unsupported ruleset rule %s%s" % (clip(kind),
                    "; merge queues need a separately supported merge-group workflow" if kind == "merge_queue" else ""))
    if set(effective_by_id) - seen:
        raise ProfileError("effective ruleset absent from complete listing; bypass visibility unverified")

    state, protection, error = _gh(prefix + "/branches/" + encoded + "/protection")
    if state == "ok" and isinstance(protection, dict):
        if not {"required_status_checks", "required_pull_request_reviews"} <= set(protection):
            raise ProfileError("classic protection settings incomplete/unverified")
        required, review = protection["required_status_checks"], protection["required_pull_request_reviews"]
        if required is not None:
            if not isinstance(required, dict):
                raise ProfileError("classic required checks unverified")
            status_checks(required, classic=True)
        if review is not None:
            if not isinstance(review, dict):
                raise ProfileError("classic pull request settings unverified")
            review_rule(review, classic=True)
        admins = _boolean(protection.get("enforce_admins"), "enabled", "administrative bypass")
        force = _boolean(protection.get("allow_force_pushes"), "enabled", "force-push bypass")
        delete = _boolean(protection.get("allow_deletions"), "enabled", "branch deletion bypass")
        if not admins:
            bypasses.append("classic protection exempts administrators")
        if force:
            bypasses.append("classic protection permits force pushes")
        if delete:
            bypasses.append("classic protection permits branch deletion")
        prohibit_force = prohibit_force or not force and admins
        prohibit_delete = prohibit_delete or not delete and admins
    elif not (state != "ok" and "branch not protected" in error.lower() and "404" in error):
        raise ProfileError("classic branch protection unverified (%s)" % (error or "unexpected response"))

    queue_status, queue_detail = (_classic_queue(slug, branch) if state == "ok" else
        (OK, "no classic protection and no merge queue in the complete effective ruleset inventory"))
    results = [("enforcement-protection-sources", OK, "observed classic protection and complete applicable active rulesets"),
               ("enforcement-merge-queue", queue_status, queue_detail)]
    for context in ("evidence", "gitleaks"):
        bindings = [source for c, source, _ in checks if c == context]
        found = bool(bindings) and all(source == app_id for source in bindings) if app_id is not None else False
        results.append(("enforcement-check-" + context, (OK if found else FAIL) if app_id is not None else UNVERIFIED,
                        "exact '%s' check from GitHub Actions application id %s %s on %s" %
                        (context, app_id, "required" if found else "NOT required with the expected identity", branch)))
    criteria = (
        ("pr", bool(reviews), "pull request changes required"),
        ("owner-review", any(count >= 1 and owner for count, owner, _ in reviews), "required approving owner review"),
        ("review-freshness", any(count >= 1 and fresh for count, _, fresh in reviews),
         "fresh review after pushes (dismiss stale approvals or require last-push approval)"),
        ("branch-freshness", app_id is not None and all(any(c == wanted and source == app_id and fresh
             for c, source, fresh in checks) for wanted in ("evidence", "gitleaks")), "up-to-date required check evaluation"),
        ("bypass", not bypasses and prohibit_force and prohibit_delete,
         "no unreviewed bypass: admins bound, force pushes/deletion blocked, no disclosed bypass actors"))
    for name, good, label in criteria:
        detail = label + (" observed" if good else " NOT established")
        if name == "bypass" and bypasses:
            detail += "; disclosed bypasses need a separate operator decision: " + "; ".join(bypasses)
        results.append(("enforcement-" + name, OK if good else FAIL, detail))
    return results


def _glob_language(patterns, boundary=False):
    """Epsilon-NFA for a bounded glob grammar, without sampling current paths.

    Boundary basename rules match any segment, per lane.compile_pattern. Owner
    basename rules match file basenames; explicit directory/** rules cover their
    descendants. This conservative subset never promotes root-only ownership.
    """
    edges, epsilon, accepts = [[]], [set()], set()
    alphabet = {"/", "\0"}  # NUL represents characters absent from all literal sets.

    def node():
        edges.append([])
        epsilon.append(set())
        return len(edges) - 1

    for pattern in patterns:
        rooted = pattern.startswith("/")
        pattern = pattern[1:] if rooted else pattern
        if pattern.endswith("/"):
            pattern += "**"
        basename = "/" not in pattern
        if basename and (boundary or not rooted):
            pattern = "**/" + pattern
        variants = [pattern]
        if boundary and basename:
            variants.append(pattern + "/**")
        for variant in variants:
            current = node()
            epsilon[0].add(current)
            i = 0
            while i < len(variant):
                following = node()
                if variant.startswith("**/", i):
                    loop = node()
                    epsilon[current].update((following, loop))
                    edges[loop].extend(((None, loop), (frozenset("/"), following)))
                    i += 3
                elif variant.startswith("**", i):
                    edges[current].append((None, current))
                    epsilon[current].add(following)
                    i += 2
                elif variant[i] == "*":
                    edges[current].append(("segment", current))
                    epsilon[current].add(following)
                    i += 1
                elif variant[i] == "?":
                    edges[current].append(("segment", following))
                    i += 1
                else:
                    char = variant[i]
                    chars = {char}
                    if boundary and char.isalpha():
                        chars.update((char.lower(), char.upper()))
                        # Unicode IGNORECASE has these additional ASCII equivalents.
                        chars.update({"i": "\u0130\u0131", "s": "\u017f", "k": "\u212a"}.get(char.lower(), ""))
                    alphabet.update(chars)
                    edges[current].append((frozenset(chars), following))
                    i += 1
                current = following
            accepts.add(current)

    def closure(states):
        result, pending = set(states), list(states)
        while pending:
            for target in epsilon[pending.pop()]:
                if target not in result:
                    result.add(target)
                    pending.append(target)
        return frozenset(result)

    def step(states, char):
        targets = set()
        for state in states:
            for label, target in edges[state]:
                if label is None or (char != "/" if label == "segment" else char in label):
                    targets.add(target)
        return closure(targets)

    return closure({0}), accepts, alphabet, step


def _ownership_coverage(text, paths):
    if lanelib is None:
        raise ProfileError("ownership boundary unverified: trusted lane module unavailable")
    patterns = []
    for line in text.splitlines():
        line = re.sub(r"(^|\s)#.*$", "", line).strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ProfileError("ownership has ownerless overrides; full boundary coverage unverified")
        if not all(re.fullmatch(r"@[A-Za-z0-9][A-Za-z0-9-]*(?:/[A-Za-z0-9_.-]+)?", owner) for owner in parts[1:]):
            raise ProfileError("unsupported ownership identity syntax")
        pattern = parts[0]
        if (not re.fullmatch(r"[A-Za-z0-9_./*?-]+", pattern) or pattern == "/" or "//" in pattern or
                pattern.endswith("**/") or
                any(part in (".", "..") for part in pattern.split("/")) or
                any("**" in part and part != "**" for part in pattern.split("/"))):
            raise ProfileError("unsupported ownership pattern")
        patterns.append(pattern)
    if not patterns:
        raise ProfileError("ownership declarations are missing")
    if any(p in ("*", "**", "/**", "**/*", "/**/*") for p in patterns):
        return  # every later declaration also has provider-validated owners
    if sum(len(p) for p in patterns) > 10000:
        raise ProfileError("ownership patterns exceed supported proof limit")
    owner_start, owner_ends, owner_chars, owner_step = _glob_language(patterns)
    for pattern in lanelib.BUILTIN_CRITICAL:
        if not pattern.isascii():
            raise ProfileError("unsupported non-ASCII ownership boundary")
        start, ends, chars, step = _glob_language([pattern], boundary=True)
        pending, seen = [(start, owner_start)], {(start, owner_start)}
        while pending:
            critical, owned = pending.pop()
            if ends.intersection(critical) and not owner_ends.intersection(owned):
                raise ProfileError("ownership does not cover the complete case-insensitive future boundary %s "
                                   "(root anchoring and all case variants matter)" % pattern)
            for char in chars | owner_chars:
                after = step(critical, char)
                if not after:
                    continue
                pair = (after, owner_step(owned, char))
                if pair not in seen:
                    seen.add(pair)
                    pending.append(pair)
            if len(seen) > 6000:
                raise ProfileError("ownership coverage proof exceeds supported state limit; unverified")


def enforcement_files(prefix, branch):
    """Inspect immutable provider blobs. Never execute hosted or inspected-repo scripts."""
    snapshot = _provider(prefix + "/branches/" + quote(branch, safe=""), dict)
    try:
        sha, tree_sha = snapshot["commit"]["sha"], snapshot["commit"]["commit"]["tree"]["sha"]
    except (KeyError, TypeError):
        raise ProfileError("protected branch snapshot unverified")
    if not all(isinstance(value, str) and _SHA.fullmatch(value) for value in (sha, tree_sha)):
        raise ProfileError("protected branch snapshot identity unverified")
    tree = _provider(prefix + "/git/trees/" + tree_sha + "?recursive=1", dict)
    if tree.get("sha") != tree_sha or tree.get("truncated") is not False or not isinstance(tree.get("tree"), list):
        raise ProfileError("hosted tree unverified or truncated")
    if len(tree["tree"]) > MAX_TRACKED_FILES:
        raise ProfileError("hosted tree exceeds inspection limit")
    entries = {}
    for entry in tree["tree"]:
        if not isinstance(entry, dict):
            raise ProfileError("hosted tree entry unverified")
        path = entry.get("path")
        if (not isinstance(path, str) or not path or path in entries or path.startswith("/") or
                any(p in ("", ".", "..") for p in path.split("/")) or re.search(r"[\x00-\x1f\x7f\\]", path)):
            raise ProfileError("hosted tree path unverified")
        entries[path] = entry

    def blob(path):
        entry = entries.get(path)
        if (not isinstance(entry, dict) or entry.get("type") != "blob" or entry.get("mode") not in ("100644", "100755") or
                not isinstance(entry.get("sha"), str) or not _SHA.fullmatch(entry["sha"])):
            raise ProfileError("hosted %s missing or not a regular tracked file" % clip(path))
        response = _provider(prefix + "/git/blobs/" + entry["sha"], dict)
        if (response.get("sha") != entry["sha"] or response.get("encoding") != "base64" or
                not isinstance(response.get("content"), str) or type(response.get("size")) is not int or
                not 0 < response["size"] <= MAX_FILE_BYTES or len(response["content"]) > MAX_FILE_BYTES * 2):
            raise ProfileError("hosted %s blob response unverified" % clip(path))
        try:
            data = base64.b64decode("".join(response["content"].split()), validate=True)
            identity = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
            if len(data) != response["size"] or identity != entry["sha"]:
                raise ValueError("blob identity mismatch")
            return data.decode("utf-8")
        except (ValueError, UnicodeError, binascii.Error):
            raise ProfileError("hosted %s blob integrity/encoding unverified" % clip(path))

    results = [("enforcement-snapshot", OK, "inspecting %s at %s (read-only branch snapshot)" % (branch, sha))]
    for filename in ("lane.py", "evidence_check.py"):
        body = blob("scripts/" + filename)
        if hashlib.sha256(body.encode("utf-8")).hexdigest() != sha256(os.path.join(HERE, filename)):
            raise ProfileError("hosted tooling differs from the trusted inspector distribution; execution contract unverified")
    try:
        if lanelib is None:
            raise ProfileError("trusted config parser unavailable")
        lanelib.parse_config(blob("scripts/lane-config.yaml"))
    except (ValueError, lanelib.ConfigError if lanelib is not None else ValueError):
        raise ProfileError("hosted lane configuration unverified")
    results.append(("enforcement-tooling", OK, "hosted checker/lane match the trusted distribution; config parses as data"))

    foundation = {".github/workflows/sdlc-gate.yml": False, ".github/workflows/gitleaks.yml": True}
    for path, scanner in foundation.items():
        inspected = workflow_results(blob(path), scanner)
        problems = [name for name, status, _ in inspected if status != OK]
        results.append(("enforcement-workflow-" + ("gitleaks" if scanner else "evidence"),
                        UNVERIFIED if problems else OK,
                        "%s workflow %s" % (path, "unsupported/unsafe: " + ", ".join(problems) if problems else
                                             "matches the bounded supported profile (not runtime proof)")))
    others = [p for p in entries if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")) and p not in foundation]
    if len(others) > 100:
        raise ProfileError("workflow inventory exceeds supported inspection limit")
    for path in others:
        try:
            doc = parse_workflow(blob(path))
        except ProfileError:
            raise ProfileError("other workflow has unsupported shape; exact check-name uniqueness unverified")
        jobs, permissions = doc.get("jobs"), doc.get("permissions")
        if not isinstance(jobs, dict) or not isinstance(permissions, dict) or any(v not in ("read", "none") for v in permissions.values()):
            raise ProfileError("other workflow permissions/shape unsupported; check-source uniqueness unverified")
        for job_id, job in jobs.items():
            if not isinstance(job, dict) or "uses" in job:
                raise ProfileError("reusable/indirect workflow check names unsupported")
            name = job.get("name", job_id)
            if not isinstance(name, str) or "${{" in name or name in ("evidence", "gitleaks"):
                raise ProfileError("other workflow has duplicate or indeterminate evidence/gitleaks check names")
            if "permissions" in job and (not isinstance(job["permissions"], dict) or
                                          any(v not in ("read", "none") for v in job["permissions"].values())):
                raise ProfileError("other workflow job permissions unsupported; check-source uniqueness unverified")
    results.append(("enforcement-workflow-names", OK, "no other workflow can declare the same exact check names in the supported profile"))
    owner_path = next((p for p in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS") if p in entries), None)
    if owner_path is None:
        raise ProfileError("hosted ownership declarations missing")
    owners = blob(owner_path)
    errors = _provider(prefix + "/codeowners/errors?ref=" + sha, dict)
    if not isinstance(errors.get("errors"), list):
        raise ProfileError("provider ownership validation unverified")
    if errors["errors"]:
        raise ProfileError("provider reports %d ownership error(s); owner identities/coverage not established" % len(errors["errors"]))
    _ownership_coverage(owners, entries)
    results.append(("enforcement-ownership", OK, "%s: provider-valid owners cover the entire declared execution boundary, including new files" % owner_path))
    return results


def check_enforcement(root):
    results = []
    try:
        if not in_git(root):
            raise ProfileError("not a git work tree; hosted enforcement unverified")
        code, remote, _ = git(root, "remote", "get-url", "origin")
        match = _REMOTE.fullmatch(remote.strip()) if code == 0 else None
        if not match or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", p) for p in match.groups()):
            raise ProfileError("origin is not a supported github.com repository")
        if shutil.which("gh") is None:
            raise ProfileError("gh CLI unavailable; hosted enforcement unverified")
        prefix = "repos/%s/%s" % match.groups()
        repo = _provider(prefix, dict)
        branch = repo.get("default_branch")
        if not isinstance(branch, str) or not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
            raise ProfileError("default branch unverified or unsupported")
        app_id, app_detail = _actions_identity()
        results.append(("enforcement-application", OK if app_id is not None else UNVERIFIED, app_detail))
        results += enforcement_settings(prefix, branch, app_id)
        results += enforcement_files(prefix, branch)
    except ProfileError as exc:
        results.append(("enforcement-inspection", UNVERIFIED, str(exc)))
    ready = bool(results) and all(status == OK for _, status, _ in results)
    results.append(("enforcement-readiness", OK if ready else FAIL,
                    "supported profile observed; not code correctness, authenticated approval, runtime agent isolation or "
                    "a successful hosted scan. Settings can change; scanner licensing/fork/private access still need "
                    "authorized hosted verification" if ready else
                    "NOT ready: false, missing, unsupported or unverified prerequisites. No settings changed; activation "
                    "and any disclosed bypass need separate operator authorization"))
    return results


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def check_repo(root, check_remote=False, check_name="evidence", require_enforcement=False):
    """Return a list of (name, status, detail)."""
    results = check_environment()
    results += check_files(root)
    results += check_drift(root)
    rules, config_results = load_rules_for(root)
    results += config_results
    results += check_rule_coverage(root, rules)
    results += check_workflow(root)
    results += check_hook(root)
    results += check_codeowners(root)
    results += check_default_branch(root)
    results += check_shallow(root)
    if require_enforcement and not check_remote:
        raise ValueError("--require-enforcement requires --check-branch-protection")
    if require_enforcement:
        results += check_enforcement(root)
    elif check_remote:
        results += check_branch_protection(root, check_name)
    else:
        results.append(("required-check", UNVERIFIED,
                        "mark the CI check '%s' as required in branch protection or a ruleset; nothing blocks merges until "
                         "then. Prove it with --check-branch-protection (uses gh)" % check_name))
    if not require_enforcement:
        results.append(("enforcement-readiness", UNVERIFIED,
                        "installation health or a single required check is not hosted merge readiness; use "
                        "--check-branch-protection --require-enforcement for the supported profile"))
    return results


def summarise(results):
    counts = {OK: 0, FAIL: 0, WARN: 0, UNVERIFIED: 0, INFO: 0}
    for _, status, _ in results:
        counts[status] += 1
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check install health")
    parser.add_argument("--root", default=".")
    parser.add_argument("--strict", action="store_true", help="treat WARN as failure")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-branch-protection", action="store_true",
                        help="read branch protection via `gh api` (network, read-only)")
    parser.add_argument("--require-enforcement", action="store_true",
                        help="require the complete supported hosted profile; needs --check-branch-protection")
    parser.add_argument("--check-name", default="evidence",
                        help="job name of the required check (default: evidence)")
    args = parser.parse_args(argv)
    if args.require_enforcement and not args.check_branch_protection:
        parser.error("--require-enforcement requires --check-branch-protection")
    if args.require_enforcement and args.check_name != "evidence":
        parser.error("--require-enforcement requires the exact evidence and gitleaks checks, not a custom --check-name")
    if not os.path.isdir(args.root):
        sys.stderr.write("doctor: --root %r is not a directory\n" % args.root)
        return 2

    results = check_repo(args.root, args.check_branch_protection, args.check_name, args.require_enforcement)
    counts = summarise(results)
    failed = counts[FAIL] > 0 or (args.strict and counts[WARN] > 0)
    if args.json:
        print(json.dumps({"version": VERSION, "summary": counts, "failed": failed,
                          "results": [{"name": n, "status": s, "detail": d} for n, s, d in results]}, sort_keys=True))
    else:
        print("doctor %s" % VERSION)
        for name, status, detail in results:
            print("%s: %s - %s" % (name, status, detail))
        print("summary: %d verified, %d FAIL, %d WARN, %d unverified" % (
            counts[OK], counts[FAIL], counts[WARN], counts[UNVERIFIED]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
