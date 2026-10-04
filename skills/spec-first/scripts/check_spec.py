"""Validate a spec or intent statement against the spec-first templates. Deterministic checks only.

It checks that every acceptance criterion is observable-in-form and has a pass condition, that
every criterion maps to at least one test expectation (and no test points at a criterion that does
not exist), that blanks are filled, that Standard/Critical specs record a human approval, and that
nothing secret was pasted in. It cannot tell whether the spec is the RIGHT spec, and the vague-word
check is a tripwire for common phrasings, not a judgement.

Criterion:   - AC1: observable behavior | pass: measurable condition
Test line:   - AC1[, AC2] -> tests/test_x.py::test_name | fails-before: why it fails today
             (use "manual: <what>" in place of a test path only when it cannot be automated)
Header:      Lane: Standard / Status: draft|approved / Approved-by: Name (YYYY-MM-DD)

Exit codes: 0 ok (warnings allowed unless --strict) | 1 errors | 2 usage or unreadable file.
Stdlib only, no network. Python >= 3.8.
"""

import argparse
import datetime
import json
import os
import re
import sys

LANES = ("Lite", "Standard", "Critical")
RANK = {name: i for i, name in enumerate(LANES)}
MAX_CRITERIA = {"Lite": 5, "Standard": 15, "Critical": 30}
MAX_BYTES = 1000000
MIN_PASS_CHARS = 8

REQUIRED = {
    ("spec", "Lite"): ("intent", "criteria", "tests"),
    ("spec", "Standard"): ("intent", "criteria", "tests", "outofscope", "constraints", "plan"),
    ("spec", "Critical"): ("intent", "criteria", "tests", "outofscope", "constraints", "plan", "threat", "rollout"),
}
for _lane in LANES:
    REQUIRED[("intent", _lane)] = ("intent", "why", "outofscope", "success")
LABELS = {"intent": "Intent", "criteria": "Acceptance criteria", "tests": "Test expectations", "outofscope": "Out of scope",
          "constraints": "Constraints", "plan": "Plan", "threat": "Threat considerations", "rollout": "Rollout constraints",
          "why": "Why", "success": "Success measures"}
SECTION_NAMES = {
    "intent": "intent", "why": "why", "whynow": "why", "outofscope": "outofscope", "nongoals": "outofscope",
    "acceptancecriteria": "criteria", "criteria": "criteria", "constraints": "constraints",
    "testexpectations": "tests", "tests": "tests", "assumptionsandopenquestions": "assumptions",
    "assumptions": "assumptions", "openquestions": "assumptions", "plan": "plan",
    "threatconsiderations": "threat", "threatnote": "threat", "rolloutconstraints": "rollout",
    "successmeasures": "success", "successmeasure": "success",
    "trigger": "trigger", "impact": "impact", "mitigation": "mitigation", "followups": "followups",
}

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST = re.compile(r"^\s*[-*]\s+")
_CRITERION = re.compile(r"^\s*[-*]\s+(?P<id>AC\d+)\s*:\s*(?P<behavior>.+?)\s*\|\s*pass\s*:\s*(?P<pass>.*)$", re.I)
_TEST = re.compile(r"^\s*[-*]\s+(?P<ids>AC\d+(?:\s*,\s*AC\d+)*)\s*->\s*(?P<ref>.+?)\s*\|\s*fails-before\s*:\s*(?P<why>.*)$", re.I)
_HEADER = re.compile(r"^\s*(?P<key>Lane|Author|Status|Approved-by)\s*:\s*(?P<value>.*?)\s*$", re.I)
_APPROVED = re.compile(r"^(?P<name>.*\S)\s*\(\s*(?P<date>\d{4}-\d{2}-\d{2})\s*\)\s*$")
_BLANK = re.compile(r"___|\bTBD\b")
_HIDDEN = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
_VAGUE = re.compile(
    r"\b(fast(?:er)?|quick(?:ly|er)?|slow(?:er)?|better|improv(?:e|ed|es|ing)|eas(?:y|ier|ily)|intuitive|user-friendly|robust|"
    r"secure(?:ly)?|scalab(?:le|ility)|efficient(?:ly)?|performant|seamless(?:ly)?|appropriate(?:ly)?|reasonable|properly|"
    r"correctly|as needed|etc|and so on|should work|works?)\b", re.I)
_PATHLIKE = re.compile(r"[/\\]|\.\w{1,5}$")

# Keep in sync with context-pack/scripts/check_brief.py (tests/test_check_spec.py asserts the lists match).
SECRETS = (
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("URL with embedded credentials", re.compile(r"://[^/\s:@]+:[^/\s@]+@")),
    ("credential assignment", re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*[\"']?[^\s\"']{8,}")),
)


def norm(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def blank_comments(text):
    return _COMMENT.sub(lambda match: "\n" * match.group(0).count("\n"), text)


def parse_date(text):
    try:
        return datetime.date(int(text[:4]), int(text[5:7]), int(text[8:10]))
    except (ValueError, IndexError):
        return None


def test_path_problem(ref, repo_root):
    """None if the test reference points at an existing repo file (or is not a path); else a message."""
    target = ref.split("::", 1)[0].strip().strip("`")
    if not _PATHLIKE.search(target):
        return None
    if target.startswith("/") or ".." in target.replace("\\", "/").split("/"):
        return "not a safe repo-relative path"
    root = os.path.realpath(repo_root)
    full = os.path.realpath(os.path.join(root, target))
    try:
        inside = os.path.commonpath([root, full]) == root
    except ValueError:
        inside = False
    if not inside:
        return "resolves outside the repository"
    if not os.path.isfile(full):
        return "test file does not exist yet (write the failing test first, then re-run)"
    return None


def check(text, kind, lane, repo_root, require_approved, require_tests_exist):
    """Return (findings, criteria_count). Each finding is (level, line, message)."""
    findings = []

    def add(level, line, message):
        findings.append((level, line, message))

    raw_lines = text.splitlines()
    for number, line in enumerate(raw_lines, 1):
        scan = line[1:] if number == 1 and line.startswith("\ufeff") else line
        if _HIDDEN.search(scan):
            add("ERROR", number, "hidden Unicode control characters (zero-width or bidi): remove them")
        for label, pattern in SECRETS:
            if pattern.search(line):
                add("ERROR", number, "possible secret (%s): remove it and link the source instead" % label)

    lines = blank_comments(text).splitlines()
    header = {}
    sections = {}                 # canonical -> {"line": n, "text": count of non-blank lines}
    criteria, tests = {}, []      # criteria: id -> line ; tests: (line, [ids], ref, why)
    current = None
    for index, line in enumerate(lines):
        number = index + 1
        heading = _HEADING.match(line)
        if heading and len(heading.group(1)) >= 2:
            current = SECTION_NAMES.get(norm(heading.group(2)))
            if current is None:
                add("WARN", number, "unknown section '%s'" % heading.group(2)[:40])
            elif current in sections:
                add("WARN", number, "section '%s' appears twice" % heading.group(2)[:40])
            else:
                sections[current] = {"line": number, "text": 0}
            continue
        if heading:
            continue
        if not line.strip():
            continue
        if current is None:
            match = _HEADER.match(line)
            if match:
                header[match.group("key").lower()] = (number, match.group("value").strip())
            continue
        if current in sections:
            sections[current]["text"] += 1
        if _BLANK.search(line):
            add("ERROR", number, "unfilled blank (___ or TBD): fill it in, or delete the line")
        if current == "criteria" and _LIST.match(line):
            match = _CRITERION.match(line)
            if not match:
                add("ERROR", number, "not in criterion format: - AC1: observable behavior | pass: measurable condition")
                continue
            cid = match.group("id").upper()
            if cid in criteria:
                add("ERROR", number, "%s is defined twice" % cid)
            criteria[cid] = number
            pass_text = match.group("pass").strip()
            if len(pass_text) < MIN_PASS_CHARS:
                add("ERROR", number, "%s needs a pass condition (at least %d characters) a test could assert" % (cid, MIN_PASS_CHARS))
            elif not re.search(r"\d", pass_text):
                words = sorted({w.lower() for w in _VAGUE.findall(match.group("behavior") + " " + pass_text)})
                if words:
                    add("WARN", number, "%s uses vague wording (%s) with no number in the pass condition: say how a test would "
                                        "tell, e.g. 'p95 under 300 ms on fixture X'" % (cid, ", ".join(words[:4])))
        elif current == "tests" and _LIST.match(line):
            match = _TEST.match(line)
            if not match:
                add("ERROR", number, "not in test format: - AC1 -> tests/test_x.py::test_name | fails-before: why it fails today")
                continue
            ids = [part.strip().upper() for part in match.group("ids").split(",")]
            why = match.group("why").strip()
            if len(why) < MIN_PASS_CHARS or why.lower() in ("n/a", "none"):
                add("ERROR", number, "fails-before must say why this test fails today (a test that never failed proves nothing)")
            ref = match.group("ref").strip()
            if ref.lower().startswith("manual:"):
                add("WARN", number, "manual check for %s: no automated test. Say why it cannot be automated under Assumptions" % ", ".join(ids))
            elif require_tests_exist:
                problem = test_path_problem(ref, repo_root)
                if problem:
                    add("ERROR", number, "test '%s': %s" % (ref[:60], problem))
            tests.append((number, ids))

    covered = set()
    for number, ids in tests:
        for cid in ids:
            if cid not in criteria:
                add("ERROR", number, "%s has a test expectation but no such acceptance criterion" % cid)
            covered.add(cid)
    for cid, number in sorted(criteria.items(), key=lambda kv: kv[1]):
        if cid not in covered:
            add("ERROR", number, "%s has no test expectation: every criterion must map to a scenario a test could assert" % cid)

    if "criteria" in sections and not criteria and kind == "spec":
        add("ERROR", sections["criteria"]["line"], "no acceptance criteria found")
    if len(criteria) > MAX_CRITERIA[lane]:
        add("ERROR", 1, "%d criteria exceeds the %s cap of %d: the change is too large, split it" % (len(criteria), lane, MAX_CRITERIA[lane]))

    for name in REQUIRED[(kind, lane)]:
        info = sections.get(name)
        if info is None:
            add("ERROR", 1, "%s %s requires a '%s' section" % (lane, kind, LABELS[name]))
        elif info["text"] == 0:
            add("ERROR", info["line"], "'%s' is empty" % LABELS[name])

    _check_header(header, kind, lane, require_approved, add)
    return findings, len(criteria)


def _check_header(header, kind, lane, require_approved, add):
    declared = header.get("lane")
    if declared and declared[1].title() in RANK and RANK[declared[1].title()] < RANK[lane]:
        add("WARN", declared[0], "the document declares lane %s but the change classifies as %s: a lane can only go up" % (declared[1], lane))
    if lane == "Lite" and kind == "spec":
        return
    status = header.get("status")
    if status is None:
        add("ERROR", 1, "%s %s needs 'Status: draft' or 'Status: approved' in the header" % (lane, kind))
        return
    value = status[1].lower()
    if value not in ("draft", "approved"):
        add("ERROR", status[0], "Status must be 'draft' or 'approved'")
        return
    approver = header.get("approved-by")
    if value == "approved":
        match = _APPROVED.match(approver[1]) if approver else None
        if not match or parse_date(match.group("date")) is None or "_" in match.group("name"):
            add("ERROR", approver[0] if approver else status[0],
                "an approved spec needs 'Approved-by: Name (YYYY-MM-DD)': one named human, with the date")
        else:
            author = header.get("author")
            if author and author[1].strip().lower() == match.group("name").strip().lower():
                add("WARN", approver[0], "the approver is also the author: a second human is stronger evidence")
    elif require_approved:
        add("ERROR", status[0], "Status is draft: a %s change needs one human approval before build" % lane)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a spec or intent statement")
    parser.add_argument("spec")
    parser.add_argument("--lane", choices=LANES, default="Standard")
    parser.add_argument("--kind", choices=("spec", "intent"), default="spec",
                        help="'intent' validates the Critical-lane intent statement")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--require-approved", action="store_true", help="draft specs fail (use before build or in CI)")
    parser.add_argument("--require-tests-exist", action="store_true", help="referenced test files must exist (use before merge)")
    parser.add_argument("--strict", action="store_true", help="warnings fail the check")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if os.path.getsize(args.spec) > MAX_BYTES:
            sys.stderr.write("check_spec.py: file is larger than %d bytes\n" % MAX_BYTES)
            return 2
        with open(args.spec, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError as exc:
        sys.stderr.write("check_spec.py: cannot read spec: %s\n" % exc)
        return 2

    findings, count = check(text, args.kind, args.lane, args.repo_root, args.require_approved, args.require_tests_exist)
    findings.sort(key=lambda f: (f[1], f[0]))
    errors = sum(1 for f in findings if f[0] == "ERROR")
    warnings = sum(1 for f in findings if f[0] == "WARN")
    failed = errors > 0 or (args.strict and warnings > 0)
    if args.json:
        print(json.dumps({"lane": args.lane, "kind": args.kind, "criteria": count, "errors": errors, "warnings": warnings,
                          "failed": failed, "findings": [{"level": l, "line": n, "message": m} for l, n, m in findings]},
                         sort_keys=True))
    else:
        for level, line, message in findings:
            print("%s line %d: %s" % (level, line, message))
        print("%s (%s lane): %d criteria, %d error(s), %d warning(s)" % (args.kind, args.lane, count, errors, warnings))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
