"""Verify the evidence a change owes for its lane. Local warns (fail-open), CI fails closed.

What this checks: that required evidence EXISTS and is structurally real
(section present and not template filler, spec link resolves to a file in the
repo, the diff touches test paths). What it never checks: whether the evidence
is any good. A determined author can still write 20 meaningless characters;
this raises the cost of skipping the process, it does not prove the process ran.

Evidence is derived, not self-declared. In --ci mode the lane comes from the
diff (lane.py) and the evidence comes from the PR description and the repo.
`--present` (manual attestation) is for local use only and is rejected in --ci.

Exit codes: 0 ok (or local warning) | 1 evidence missing (--ci) |
            2 usage error | 3 tooling error (--ci). Stdlib only, no network. Python >= 3.8.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane as lanelib  # noqa: E402  (same directory; trusted copy in CI)

REQUIRED = {
    "Lite": ["intent_block", "test_changes", "trace_block"],
    "Standard": ["spec_link", "test_changes", "trace_block", "review_notes"],
    "Critical": ["intent_link", "spec_link", "threat_note", "test_changes",
                 "trace_block", "review_notes", "rollout_plan"],
}

# Headings the gate looks for in the PR description (case/punctuation-insensitive).
# Keep in sync with .github/pull_request_template.md and the skills' assets/ templates.
SECTION_ALIASES = {
    "intent_block": ("intent", "intent and plan", "intent plan"),
    "trace_block": ("trace", "decision trace", "ai trace", "trace block"),
    "review_notes": ("review notes", "reviewer notes", "review"),
    "threat_note": ("threat note", "threat model", "threats"),
    "rollout_plan": ("rollout plan", "rollout", "rollout and rollback"),
}
# "Key: value" lines in the PR description.
LINK_KEYS = {
    "spec_link": ("spec", "spec link"),
    "intent_link": ("intent link", "intent"),
}

DEFAULT_TESTS = ("test", "tests", "__tests__", "*_test.*", "test_*.*",
                 "*.test.*", "*.spec.*", "evals/**")
DEFAULT_NON_EXECUTABLE = ("docs/**", "LICENSE", "CHANGELOG.md", "README.md", ".gitignore")

MIN_SECTION_CHARS = 20   # meaningful characters a section needs
MIN_WAIVER_CHARS = 15    # meaningful characters a waiver reason needs
MAX_BODY_BYTES = 1000000

HINTS = {
    "intent_block": "add a '## Intent' section: what and why, 2-3 sentences",
    "intent_link": "add a line 'Intent link: path/to/intent.md' that resolves in the repo",
    "spec_link": "add a line 'Spec: path/to/spec.md' that resolves in the repo",
    "threat_note": "add a '## Threat note' section: what could go wrong, who is affected",
    "test_changes": "change a test path, or add 'Tests: none - <reason>' (a waiver on a Critical change is flagged for review)",
    "trace_block": "add a '## Trace' section: prompts/agents used, decisions, rejected options",
    "review_notes": "add a '## Review notes' section: intent checked, risks, open questions",
    "rollout_plan": "add a '## Rollout plan' section: stages, monitoring, rollback",
}

_PLACEHOLDER = re.compile(r"\{\{.*?\}\}|\bTBD\b|\bTODO\b|<(?:fill|describe|explain|link|your)[^>]*>", re.I)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
_FILLER_LINE = re.compile(r"^\W*(tbd|todo|n/?a|none|\.{2,}|-+)?\W*$", re.I)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
# Key lines never count as section content (else "Tests: none - why" would fill an empty section).
_KEYLINE = re.compile(
    r"^\s*(?:[-*+]\s+)?\*{0,2}(?:spec(?: link)?|intent link|lane|tests?|test waiver|no tests)\s*:", re.I)


class ToolError(Exception):
    """The check could not be performed (distinct from 'evidence missing')."""


def safe(text, limit=80):
    """Make untrusted text safe to print in CI logs (no workflow-command injection)."""
    text = _CONTROL.sub(" ", str(text)).replace("::", ": :")
    return text if len(text) <= limit else text[:limit - 3] + "..."


def norm(text):
    text = re.sub(r"\(.*?\)", "", text.lower())
    return re.sub(r"[^a-z0-9]+", "", text)


# --------------------------------------------------------------------------
# PR description parsing
# --------------------------------------------------------------------------

def _scan(body):
    """Yield (index, line, in_fence) for the body with HTML comments removed."""
    body = _COMMENT.sub("", body)
    in_fence, marker = False, ""
    for index, line in enumerate(body.splitlines()):
        match = _FENCE.match(line)
        if match and (not in_fence or match.group(1) == marker):
            in_fence = not in_fence
            marker = match.group(1) if in_fence else ""
            yield index, line, True
            continue
        yield index, line, in_fence


def parse_sections(body):
    """Return list of (normalised title, content text). Headings inside fences ignored."""
    scanned = list(_scan(body))
    heads = []
    for index, line, in_fence in scanned:
        match = None if in_fence else _HEADING.match(line)
        if match:
            heads.append((index, len(match.group(1)), norm(match.group(2))))
    lines = [line for _, line, _ in scanned]
    head_positions = {index for index, _, _ in heads}
    sections = []
    for position, (index, level, title) in enumerate(heads):
        end = len(lines)
        for next_index, next_level, _ in heads[position + 1:]:
            if next_level <= level:
                end = next_index
                break
        # Sub-heading titles are structure, not content: "### Why" must not make an empty section look filled.
        body_lines = [ln for pos, ln in enumerate(lines[index + 1:end], index + 1)
                      if not _KEYLINE.match(ln) and not (pos in head_positions)]
        sections.append((title, "\n".join(body_lines)))
    return sections


def meaningful_chars(text):
    """Count real characters after removing comments, placeholders and filler lines."""
    text = _PLACEHOLDER.sub("", _COMMENT.sub("", text))
    kept = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s*(?:\[[ xX]\])?\s*", "", line)
        if line.strip() and not _FILLER_LINE.match(line):
            kept.append(line)
    return len(re.sub(r"\W+", "", "".join(kept), flags=re.UNICODE))


def find_section(sections, aliases):
    wanted = {norm(alias) for alias in aliases}
    best = None
    for title, content in sections:
        if title in wanted:
            chars = meaningful_chars(content)
            if best is None or chars > best:
                best = chars
    return best


def find_key_value(body, keys):
    """Return the value of the first 'Key: value' line outside fences/comments."""
    pattern = re.compile(
        r"^\s*(?:[-*+]\s+)?\*{0,2}(%s)\s*:\s*\*{0,2}\s*(\S.*?)\s*$"
        % "|".join(re.escape(k) for k in keys), re.I)
    for _, line, in_fence in _scan(body):
        if in_fence:
            continue
        match = pattern.match(line)
        if match:
            return match.group(2)
    return None


def link_target(value):
    value = value.strip()
    match = re.search(r"\]\(([^)\s]+)", value)
    if match:
        value = match.group(1)
    value = value.strip("<>`'\" ")
    return value


def resolve_repo_file(target, repo_root):
    """Return (ok, detail). Accepts a repo-relative file path or an http(s) URL."""
    if re.match(r"^https?://\S+$", target, re.I):
        return True, "URL accepted, not verified (no network by design)"
    path = re.split(r"[#?]", target, maxsplit=1)[0]
    if not path or path.startswith("/") or ".." in path.replace("\\", "/").split("/"):
        return False, "link is not a safe repo-relative path"
    root = os.path.realpath(repo_root)
    full = os.path.realpath(os.path.join(root, path))
    try:
        inside = os.path.commonpath([root, full]) == root
    except ValueError:  # different drives on Windows
        inside = False
    if not inside:
        return False, "link resolves outside the repository"
    if not os.path.isfile(full):
        return False, "no such file in the change: %s" % safe(path, 60)
    if os.path.getsize(full) == 0:
        return False, "linked file is empty: %s" % safe(path, 60)
    return True, "verified: %s" % safe(path, 60)


# --------------------------------------------------------------------------
# Evidence detection
# --------------------------------------------------------------------------

def _matches_any(path, patterns):
    return any(lanelib.compile_pattern(p)(path) for p in patterns)


def detect(body, paths, repo_root, rules, lane):
    """Return {evidence name: (ok, detail)} for every name this lane might need."""
    found = {}
    sections = parse_sections(body)
    for name, aliases in SECTION_ALIASES.items():
        chars = find_section(sections, aliases)
        if chars is None:
            found[name] = (False, "no '## %s' section in the PR description" % aliases[0].title())
        elif chars < MIN_SECTION_CHARS:
            found[name] = (False, "section is empty or template filler (%d/%d chars)" % (chars, MIN_SECTION_CHARS))
        else:
            found[name] = (True, "section present (%d chars)" % chars)

    for name, keys in LINK_KEYS.items():
        value = find_key_value(body, keys)
        if value is None:
            found[name] = (False, "no '%s:' line in the PR description" % keys[0].capitalize())
        else:
            found[name] = resolve_repo_file(link_target(value), repo_root)

    tests = rules.get("tests") or list(DEFAULT_TESTS)
    non_exec = rules.get("non_executable") or list(DEFAULT_NON_EXECUTABLE)
    clean = [p for p in (lanelib.clean_path(x)[0] for x in paths) if p]
    test_paths = [p for p in clean if _matches_any(p, tests)]
    waiver = find_key_value(body, ("tests", "test waiver", "no tests"))
    waived = None
    if waiver:
        match = re.match(r"(?:none|n/?a|waived)\b[\s:,\-\u2013\u2014]*(.*)$", waiver, re.I)
        if match:
            if meaningful_chars(match.group(1)) >= MIN_WAIVER_CHARS:
                waived = match.group(1)
            else:
                found["test_changes"] = (False, "test waiver needs a reason (%d+ chars)" % MIN_WAIVER_CHARS)
    if test_paths:
        found["test_changes"] = (True, "%d test path(s) changed" % len(test_paths))
    elif waived is not None:
        mark = "WAIVER on a Critical change" if lane == "Critical" else "waived"
        found["test_changes"] = (True, "%s: %s" % (mark, safe(waived)))
    elif clean and lane in ("Lite", "Standard") and all(_matches_any(p, non_exec) for p in clean):
        found["test_changes"] = (True, "waived: only non-executable paths changed")
    elif "test_changes" not in found:
        found["test_changes"] = (False, "no test path changed and no 'Tests: none - <reason>' waiver")
    return found


def declared_lane(body):
    match = None
    for _, line, in_fence in _scan(body):
        if not in_fence:
            match = re.match(r"^\s*(?:[-*+]\s+)?\*{0,2}lane\s*:\s*\*{0,2}\s*(lite|standard|critical)\b", line, re.I)
            if match:
                return match.group(1).title()
    return None


def check(lane, present):
    """Return list of missing evidence names (backward-compatible helper)."""
    required = REQUIRED.get(lane, REQUIRED["Standard"])
    return [name for name in required if name not in present]


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------

def read_body(args):
    """Return the PR description text ('' if none supplied)."""
    event_path = args.event_path or (os.environ.get("GITHUB_EVENT_PATH") if args.ci else None)
    text = ""
    try:
        if args.pr_body_file == "-":
            text = sys.stdin.read(MAX_BODY_BYTES + 1)
        elif args.pr_body_file:
            with open(args.pr_body_file, encoding="utf-8", errors="replace") as handle:
                text = handle.read(MAX_BODY_BYTES + 1)
        elif event_path:
            with open(event_path, encoding="utf-8") as handle:
                payload = json.load(handle)
            text = ((payload.get("pull_request") or {}).get("body")) or ""
    except (OSError, ValueError, AttributeError) as exc:
        raise ToolError("cannot read PR description: %s" % exc)
    if len(text) > MAX_BODY_BYTES:
        raise ToolError("PR description larger than %d bytes" % MAX_BODY_BYTES)
    return text


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def md_safe(text):
    return re.sub(r"[`<>\[\]|]", "/", safe(text, 120))


def write_summary(lane, rows, verdict, notes=()):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = ["### sdlc-gate: %s lane - %s" % (lane, verdict), "", "| Evidence | Status | Detail |", "|---|---|---|"]
    for name, ok, detail in rows:
        lines.append("| `%s` | %s | %s |" % (name, "ok" if ok else "**missing**", md_safe(detail)))
    for note in notes:
        lines.append("")
        lines.append("> " + md_safe(note))
    lines += ["", "_Presence and structure only. Quality is judged by humans._", ""]
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
    except OSError:
        pass


def main(argv=None):
    if sys.version_info < (3, 8):
        sys.stderr.write("evidence_check.py needs Python >= 3.8\n")
        return 2
    parser = argparse.ArgumentParser(description="Check lane evidence")
    parser.add_argument("--lane", default=None, help="lane floor; the lane can only go up from here")
    parser.add_argument("--present", nargs="*", default=None,
                        help="manual attestation of evidence names (local only)")
    parser.add_argument("--ci", action="store_true", help="fail closed; otherwise warn and exit 0")
    parser.add_argument("--paths", nargs="*", default=None)
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--config", default="scripts/lane-config.yaml")
    parser.add_argument("--pr-body-file", help="file with the PR description ('-' for stdin)")
    parser.add_argument("--event-path", default=None, help="GitHub event JSON (CI)")
    parser.add_argument("--diff-only", action="store_true",
                        help="local hooks: check only what the diff can prove (test changes) and list what the "
                             "PR description must carry. Never valid with --ci")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.lane is not None and args.lane not in REQUIRED:
        parser.error("--lane must be one of %s" % ", ".join(lanelib.LANES))
    if args.ci and args.present is not None:
        sys.stderr.write("evidence_check.py: --present is manual attestation and is rejected with --ci\n")
        return 2
    if args.paths is not None and args.base:
        parser.error("use either --paths or --base, not both")
    auto = args.paths is not None or bool(args.base)
    if args.diff_only and args.ci:
        sys.stderr.write("evidence_check.py: --diff-only checks a subset and is rejected with --ci\n")
        return 2
    if args.diff_only and not auto:
        sys.stderr.write("evidence_check.py: --diff-only needs --base (or --paths)\n")
        return 2
    if args.ci and not auto:
        sys.stderr.write("evidence_check.py: --ci needs --base (or --paths) so the lane is computed, not assumed\n")
        return 2

    try:
        lane, rows, extra = run(args, auto)
    except (ToolError, lanelib.GitError, lanelib.ConfigError) as exc:
        message = "tooling error: %s" % safe(exc, 200)
        if args.ci:
            print("ERROR (%s)" % message)
            if os.environ.get("GITHUB_ACTIONS"):
                print("::error title=sdlc-gate::%s" % message)
            return 3
        print("WARNING: %s (local, not blocking)" % message)
        return 0

    missing = [name for name, ok, _ in rows if not ok]
    if args.json:
        print(json.dumps({"lane": lane, "missing": missing, "notes": extra,
                          "evidence": [{"name": n, "ok": ok, "detail": d} for n, ok, d in rows]}, sort_keys=True))
    else:
        for note in extra:
            print("note: %s" % note)
        for name, ok, detail in rows:
            print("%-8s %-14s %s" % ("ok" if ok else "MISSING", name, safe(detail, 100)))
            if not ok and name in HINTS:
                print("         -> %s" % HINTS[name])

    say = (lambda text: None) if args.json else print  # keep --json output machine-readable
    if not missing:
        say(("diff checks ok for %s (PR description items are checked in CI)" if args.diff_only
             else "evidence ok for %s") % lane)
        write_summary(lane, rows, "ok", extra)
        return 0
    message = "missing evidence for %s: %s" % (lane, ", ".join(missing))
    write_summary(lane, rows, "missing: " + ", ".join(missing), extra)
    if args.ci:
        say("FAIL: %s" % message)
        if os.environ.get("GITHUB_ACTIONS"):
            print("::error title=sdlc-gate::%s" % message)
        return 1
    say("WARNING: %s (local, not blocking)" % message)
    return 0


def run(args, auto):
    """Compute (lane, [(name, ok, detail)], notes). Raises ToolError/GitError/ConfigError."""
    notes = []
    floor = args.lane
    if not auto:  # legacy manual mode: lane given, evidence attested
        lane = floor or "Standard"
        present = set(args.present or [])
        rows = []
        for name in REQUIRED[lane]:
            rows.append((name, name in present, "attested by --present, not verified" if name in present else "not attested"))
        return lane, rows, notes

    rules, error = lanelib.load_rules(args.config)
    if rules is None:
        raise ToolError(error)
    paths = lanelib.git_changed_paths(args.base, args.head, args.repo_root) if args.base else list(args.paths)
    computed, reason, _ = lanelib.classify_detailed(paths, rules)
    if args.diff_only:
        lane = lanelib.max_lane(computed, floor)
        notes.append("lane %s (%s)" % (lane, safe(reason, 100)))
        found = detect("", paths, args.repo_root, rules, lane)["test_changes"]
        detail = found[1]
        if not found[0]:
            detail = "no test path changed; if that is intended, add 'Tests: none - <reason>' to the PR description"
        owed = [name for name in REQUIRED[lane] if name != "test_changes"]
        notes.append("the PR description must carry: %s (checked in CI)" % ", ".join(owed))
        return lane, [("test_changes", found[0], detail)], notes
    body = read_body(args)
    declared = declared_lane(body)
    lane = lanelib.max_lane(computed, declared, floor)
    notes.append("lane %s (computed %s: %s; declared %s; floor %s)" % (
        lane, computed, safe(reason, 100), declared or "-", floor or "-"))
    if declared and lanelib.RANK[declared] < lanelib.RANK[computed]:
        notes.append("declared lane %s ignored: a change can be escalated, never downgraded" % declared)

    detected = detect(body, paths, args.repo_root, rules, lane)
    if args.present:
        notes.append("--present attestations merged for local use; not valid in CI")
        for name in args.present:
            if name in detected and not detected[name][0]:
                detected[name] = (True, "attested by --present, not verified")
    rows = [(name, detected[name][0], detected[name][1]) for name in REQUIRED[lane]]
    if lane == "Critical" and detected["test_changes"][1].startswith("WAIVER"):
        notes.append("Critical change relies on a test waiver: a human reviewer must confirm the reason")
    return lane, rows, notes


if __name__ == "__main__":
    sys.exit(main())
