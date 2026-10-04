"""Classify changed paths into Lite / Standard / Critical from a config file.

Rules (read this before changing anything):
  * Every path gets its own lane; the change takes the HIGHEST lane of any path.
    So Lite means *every* path matched a Lite rule. One unmatched or malformed
    path can only raise the lane, never hide a Critical one.
  * A path that matches no rule is Standard. Unknown is never Lite.
  * Gate-control files (this script, the config, the workflow, CODEOWNERS, hooks)
    are always Critical, whatever the config says, so a PR cannot weaken its own gate.
  * The config is parsed strictly. A typo'd section or bad version is an error,
    not a silent downgrade.

Exit codes: 0 ok | 2 usage error | 3 config/git error (only with --strict).
Stdlib only, no network. Python >= 3.8.
"""

import argparse
import json
import posixpath
import re
import subprocess
import sys
import unicodedata

LANES = ("Lite", "Standard", "Critical")
RANK = {name: index for index, name in enumerate(LANES)}
CONFIG_VERSION = 1
LANE_SECTIONS = ("critical", "standard", "lite")
OPTIONAL_SECTIONS = ("tests", "non_executable")  # consumed by evidence_check.py
MAX_PATH_LEN = 4096
MAX_DOUBLE_STAR = 4  # bounds regex backtracking for patterns from config

# Always Critical. Not overridable by config: this is the gate protecting itself.
BUILTIN_CRITICAL = (
    "scripts/lane.py",
    "scripts/evidence_check.py",
    "scripts/lane-config.yaml",
    "scripts/doctor.py",
    ".github/workflows/**",
    ".github/CODEOWNERS",
    "CODEOWNERS",
    "docs/CODEOWNERS",
    "hooks/**",
)

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_REF_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@^~{}:-]*$")


class ConfigError(Exception):
    """Config file unreadable or invalid."""


class GitError(Exception):
    """Could not compute the changed paths from git."""


# --------------------------------------------------------------------------
# Glob matching: * and ? stay inside one path segment, ** crosses segments.
# A pattern with no "/" matches any path segment at any depth (gitignore style).
# A pattern with "/" is anchored at the repo root. "[ ]" is literal.
# --------------------------------------------------------------------------

def _normalise_text(text):
    return unicodedata.normalize("NFC", text)


def glob_to_regex(pattern):
    """Translate one glob (already normalised) to a regex source string."""
    out = []
    i, n = 0, len(pattern)
    while i < n:
        char = pattern[i]
        if char == "*":
            if pattern.startswith("**", i):
                i += 2
                if pattern.startswith("/", i):
                    out.append("(?:.*/)?")
                    i += 1
                else:
                    out.append(".*")
            else:
                out.append("[^/]*")
                i += 1
        elif char == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(char))
            i += 1
    return "".join(out)


def compile_pattern(pattern, ignore_case=False):
    """Return a predicate(path) -> bool for a config glob."""
    text = _normalise_text(pattern.strip().replace("\\", "/"))
    while text.startswith("./"):
        text = text[2:]
    if not text or text == "/":
        raise ConfigError("empty pattern")
    if text.count("**") > MAX_DOUBLE_STAR:
        raise ConfigError("too many '**' in pattern: %s" % text)
    if text.endswith("/"):
        text += "**"
    flags = re.IGNORECASE if ignore_case else 0
    if "/" not in text:
        segment = re.compile(glob_to_regex(text), flags)
        return lambda path: any(segment.fullmatch(part) for part in path.split("/"))
    anchored = re.compile(glob_to_regex(text.lstrip("/")), flags)
    return lambda path: anchored.fullmatch(path) is not None


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

def _split_item(raw):
    """Return the pattern from a '- item' line, honouring quotes and comments."""
    body = raw[1:].strip()
    if body[:1] in ("'", '"'):
        quote = body[0]
        end = body.find(quote, 1)
        if end == -1:
            raise ConfigError("unterminated quote: %s" % raw)
        return body[1:end]
    return re.split(r"\s#", body, maxsplit=1)[0].strip()


def parse_config(text):
    """Parse the small YAML subset we rely on. Raise ConfigError on anything odd."""
    sections = {name: [] for name in LANE_SECTIONS + OPTIONAL_SECTIONS}
    current = None
    version = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") or line == "-":
            if current is None:
                raise ConfigError("line %d: list item outside a section" % number)
            pattern = _split_item(line)
            if not pattern:
                raise ConfigError("line %d: empty pattern" % number)
            sections[current].append(pattern)
            continue
        key, sep, value = line.partition(":")
        key = key.strip()
        value = re.split(r"\s#", value, maxsplit=1)[0].strip().strip("'\"")
        if not sep:
            raise ConfigError("line %d: cannot parse %r" % (number, line))
        if key == "version":
            version = value
            current = None
        elif key in sections:
            current = key
            if value and value not in ("[]",):
                raise ConfigError("line %d: put patterns on '- ' lines under %s:" % (number, key))
        else:
            allowed = ", ".join(("version",) + LANE_SECTIONS + OPTIONAL_SECTIONS)
            raise ConfigError("line %d: unknown key %r (allowed: %s)" % (number, key, allowed))
    if version != str(CONFIG_VERSION):
        raise ConfigError("unsupported or missing 'version:' (need %d, got %r)" % (CONFIG_VERSION, version))
    if not any(sections[name] for name in LANE_SECTIONS):
        raise ConfigError("config has no lane rules")
    for name, patterns in sections.items():
        for pattern in patterns:
            compile_pattern(pattern)  # validate early
    return sections


def load_rules(config_path):
    """Return (rules, "") or (None, error message). Kept for backward compatibility."""
    try:
        with open(config_path, encoding="utf-8") as handle:
            return parse_config(handle.read()), ""
    except OSError as exc:
        return None, "cannot read config: %s" % exc
    except ConfigError as exc:
        return None, "invalid config: %s" % exc


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

def clean_path(item):
    """Return (normalised path, "") or (None, reason) for unsafe input."""
    if not isinstance(item, str) or not item.strip():
        return None, "empty path entry"
    if _CONTROL_CHARS.search(item):
        return None, "control character in path"
    text = _normalise_text(item.strip().replace("\\", "/"))
    if len(text) > MAX_PATH_LEN:
        return None, "path too long"
    if text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return None, "absolute path"
    if ".." in text.split("/"):
        return None, "path traversal"
    text = posixpath.normpath(text)
    if text in (".", ""):
        return None, "empty path entry"
    return text, ""


def compile_rules(rules):
    """Compile rule predicates once. Critical matches case-insensitively (fail safe)."""
    compiled = {"critical": [], "standard": [], "lite": []}
    for pattern in BUILTIN_CRITICAL:
        compiled["critical"].append((pattern + " (built-in)", compile_pattern(pattern, True)))
    for name in LANE_SECTIONS:
        for pattern in rules.get(name, []):
            compiled[name].append((pattern, compile_pattern(pattern, name == "critical")))
    return compiled


def path_lane(path, compiled):
    """Return (lane, rule) for one clean path. Highest matching lane wins."""
    for lane in ("Critical", "Standard", "Lite"):
        for pattern, matches in compiled[lane.lower()]:
            if matches(path):
                return lane, pattern
    return "Standard", None


def classify_detailed(paths, rules):
    """Return (lane, reason, per_path list). Never raises on bad paths."""
    if not paths:
        return "Standard", "no paths supplied, escalated", []
    compiled = compile_rules(rules)
    per_path = []
    for item in paths:
        path, problem = clean_path(item)
        if path is None:
            per_path.append({"path": str(item), "lane": "Standard",
                             "rule": None, "note": "malformed (%s), escalated" % problem})
            continue
        lane, rule = path_lane(path, compiled)
        note = "no rule matched, escalated" if rule is None else "matched %s rule %s" % (lane, rule)
        per_path.append({"path": path, "lane": lane, "rule": rule, "note": note})
    top = max(per_path, key=lambda entry: RANK[entry["lane"]])
    lane = top["lane"]
    first = next(entry for entry in per_path if entry["lane"] == lane)
    reason = first["note"]
    others = sum(1 for entry in per_path if entry is not first and entry["lane"] == lane)
    if len(per_path) > 1:
        reason += " (%s%s)" % (_short(first["path"]), " +%d more" % others if others else "")
    return lane, reason, per_path


def classify(paths, rules):
    """Return (lane, reason). Backward-compatible wrapper."""
    lane, reason, _ = classify_detailed(paths, rules)
    return lane, reason


def _short(text, limit=60):
    text = _CONTROL_CHARS.sub("?", text).replace("::", ": :")
    return text if len(text) <= limit else text[:limit - 3] + "..."


def max_lane(*lanes):
    return max((lane for lane in lanes if lane), key=lambda name: RANK[name])


# --------------------------------------------------------------------------
# Git input
# --------------------------------------------------------------------------

def git_changed_paths(base, head="HEAD", repo_root="."):
    """Paths changed between merge-base(base, head) and head.

    --no-renames lists BOTH sides of a rename, so moving a file out of a
    Critical directory is still seen as touching it. -z keeps odd filenames intact.
    """
    for ref in (base, head):
        if not _REF_OK.match(ref or ""):
            raise GitError("refusing unsafe ref: %r" % ref)
    cmd = ["git", "-C", repo_root, "diff", "--name-only", "--no-renames", "-z",
           "%s...%s" % (base, head), "--"]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except OSError as exc:
        raise GitError("cannot run git: %s" % exc)
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-1:]
        raise GitError("git diff failed (shallow clone? use fetch-depth: 0): %s" % " ".join(tail))
    return [p.decode("utf-8", "replace") for p in proc.stdout.split(b"\0") if p]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Classify change lane")
    parser.add_argument("--paths", nargs="*", default=None)
    parser.add_argument("--base", help="git base ref/SHA; classify the diff base...head")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--config", default="scripts/lane-config.yaml")
    parser.add_argument("--strict", "--ci", dest="strict", action="store_true",
                        help="config/git errors exit 3 instead of escalating to Standard")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.paths is not None and args.base:
        parser.error("use either --paths or --base, not both")

    def emit(lane, reason, per_path, error=None):
        if args.json:
            print(json.dumps({"lane": lane, "reason": reason, "error": error,
                              "paths": per_path}, sort_keys=True))
        else:
            print("%s: %s" % (lane, reason))

    rules, error = load_rules(args.config)
    if rules is None:
        sys.stderr.write("lane.py: %s\n" % error)
        emit("Standard", error, [], error)
        return 3 if args.strict else 0

    try:
        paths = git_changed_paths(args.base, args.head, args.repo_root) if args.base else (args.paths or [])
    except GitError as exc:
        sys.stderr.write("lane.py: %s\n" % exc)
        emit("Standard", str(exc), [], str(exc))
        return 3 if args.strict else 0

    if args.base and not paths:
        emit("Standard", "no changed files, escalated", [])
        return 0
    lane, reason, per_path = classify_detailed(paths, rules)
    emit(lane, reason, per_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
