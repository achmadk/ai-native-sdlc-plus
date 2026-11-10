"""Shared specification bundle interpretation and extraction module.

Provides bounded upstream bundle recognition (OpenSpec and Spec Kit),
source extraction, Markdown parsing, and structural mapping validation
for local inspection and revision-bound Git evidence verification.
Standard-library only, Python >= 3.8.
"""

import datetime
import json
import os
import re
import subprocess
import sys

_HIDDEN = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
_BLANK = re.compile(r"___|\bTBD\b")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_FENCE_START = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_APPROVED = re.compile(r"^(?P<name>.*\S)\s*\(\s*(?P<date>\d{4}-\d{2}-\d{2})\s*\)\s*$")
_HEADER_FIELD = re.compile(r"^\s*(?P<key>Lane|Author|Status|Approved-by)\s*:\s*(?P<value>.*?)\s*$", re.I)
_FILLER_LINE = re.compile(r"^\W*(tbd|todo|n/?a|none|\.{2,}|-+)?\W*$", re.I)
_PLACEHOLDER = re.compile(r"\{\{.*?\}\}|\bTBD\b|\bTODO\b|<(?:fill|describe|explain|link|your)[^>]*>", re.I)

MAX_BUNDLE_FILES = 64
MAX_BUNDLE_BYTES = 1000000
MIN_PASS_CHARS = 8
MIN_ARTIFACT_CHARS = 20
MAX_CRITERIA = {
    "Lite": 5,
    "Standard": 15,
    "Critical": 30,
}

# Keep in sync with check_spec.py
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


class BundleError(Exception):
    """Raised when bundle structure, reading, or limits fail."""


def norm(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def parse_date(text):
    try:
        return datetime.date(int(text[:4]), int(text[5:7]), int(text[8:10]))
    except (ValueError, IndexError):
        return None


def blank_comments_and_fences(text):
    """Blank out HTML comments and fenced code blocks, preserving line numbers."""
    text = _COMMENT.sub(lambda match: "\n" * match.group(0).count("\n"), text)
    lines = text.splitlines()
    in_fence = None
    cleaned = []
    for line in lines:
        m = _FENCE_START.match(line)
        if m:
            marker = m.group(1)[0]
            count = len(m.group(1))
            if in_fence is None:
                in_fence = (marker, count)
                cleaned.append("")
                continue
            elif in_fence[0] == marker and count >= in_fence[1]:
                in_fence = None
                cleaned.append("")
                continue
        if in_fence is not None:
            cleaned.append("")
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


def meaningful_chars(text):
    """Count non-filler, non-placeholder characters."""
    cleaned = _PLACEHOLDER.sub("", _COMMENT.sub("", text))
    kept = []
    for line in cleaned.splitlines():
        line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s*(?:\[[ xX]\])?\s*", "", line)
        if line.strip() and not _FILLER_LINE.match(line):
            kept.append(line)
    return len(re.sub(r"\W+", "", "".join(kept), flags=re.UNICODE))


def split_markdown_table_row(line):
    """Split a Markdown table row into cells, honoring escaped pipes (\\|)."""
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    cells = []
    current = []
    escaped = False
    for char in raw:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    cells.append("".join(current).strip())
    return cells


class LocalBundleReader:
    """Safely reads files from a local directory root with boundary enforcement."""

    def __init__(self, root_path):
        self.root = os.path.realpath(root_path)
        if not os.path.isdir(self.root):
            raise BundleError("not a directory: %s" % root_path)

    def list_files(self):
        result = []
        for dirpath, _, filenames in os.walk(self.root):
            for fname in sorted(filenames):
                full = os.path.join(dirpath, fname)
                try:
                    rel = os.path.relpath(full, self.root).replace("\\", "/")
                except ValueError:
                    continue
                result.append(rel)
        return sorted(result)

    def file_exists(self, rel_path):
        norm_p = rel_path.replace("\\", "/").strip("/")
        full = os.path.realpath(os.path.join(self.root, norm_p))
        try:
            inside = os.path.commonpath([self.root, full]) == self.root
        except ValueError:
            return False
        return inside and os.path.isfile(full)

    def read_text(self, rel_path):
        norm_p = rel_path.replace("\\", "/").strip("/")
        if ".." in norm_p.split("/"):
            raise BundleError("path traversal detected in bundle reference: %s" % rel_path)
        full = os.path.realpath(os.path.join(self.root, norm_p))
        try:
            inside = os.path.commonpath([self.root, full]) == self.root
        except ValueError:
            inside = False
        if not inside:
            raise BundleError("file resolves outside bundle directory: %s" % rel_path)
        if not os.path.isfile(full):
            raise BundleError("bundle file not found: %s" % rel_path)
        if os.path.islink(full):
            raise BundleError("symlinked bundle members are not permitted: %s" % rel_path)
        try:
            with open(full, "rb") as handle:
                raw_bytes = handle.read()
        except OSError as exc:
            raise BundleError("cannot read bundle file '%s': %s" % (rel_path, exc))
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BundleError("invalid UTF-8 encoding in bundle file: %s" % rel_path)


class GitRevisionReader:
    """Reads tracked files from an explicit Git commit at a base path."""

    def __init__(self, repo_root, commit, bundle_base_path):
        self.repo_root = repo_root
        self.commit = commit
        self.base_path = bundle_base_path.replace("\\", "/").strip("/")
        self._entries = {}
        self._blobs = {}
        self._load_tree()

    def _load_tree(self):
        try:
            cmd = ["git", "--literal-pathspecs", "-C", self.repo_root, "ls-tree",
                   "-r", "--full-tree", "-l", "-z", self.commit, "--", self.base_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            if res.returncode != 0:
                raise BundleError("cannot list Git tree at revision %s" % self.commit)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BundleError("Git operation failed: %s" % type(exc).__name__)

        raw_items = [item for item in res.stdout.split(b"\0") if item]
        prefix = (self.base_path + "/").encode("utf-8") if self.base_path else b""

        for item in raw_items:
            meta, sep, raw_path = item.partition(b"\t")
            if not sep:
                continue
            parts = meta.split()
            if len(parts) != 4:
                continue
            mode, otype, sha, size_b = parts[0], parts[1], parts[2], parts[3]
            # Security checks: regular blob only
            if mode not in (b"100644", b"100755") or otype != b"blob":
                raise BundleError("bundle member is not a regular tracked blob: %s" % raw_path.decode("utf-8", errors="replace"))
            if not size_b.isdigit() or int(size_b) == 0:
                raise BundleError("bundle member is empty: %s" % raw_path.decode("utf-8", errors="replace"))

            if prefix and raw_path.startswith(prefix):
                rel = raw_path[len(prefix):].decode("utf-8", errors="replace")
            else:
                rel = raw_path.decode("utf-8", errors="replace")
            self._entries[rel] = sha.decode("ascii")

    def list_files(self):
        return sorted(self._entries.keys())

    def file_exists(self, rel_path):
        norm_p = rel_path.replace("\\", "/").strip("/")
        return norm_p in self._entries

    def read_text(self, rel_path):
        norm_p = rel_path.replace("\\", "/").strip("/")
        sha = self._entries.get(norm_p)
        if not sha:
            raise BundleError("file not found in evaluated revision: %s" % rel_path)
        if sha in self._blobs:
            return self._blobs[sha]
        try:
            cmd = ["git", "-C", self.repo_root, "cat-file", "-p", sha]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            if res.returncode != 0:
                raise BundleError("cannot read blob from Git: %s" % rel_path)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BundleError("Git operation failed: %s" % type(exc).__name__)
        try:
            text = res.stdout.decode("utf-8")
        except UnicodeDecodeError:
            raise BundleError("invalid UTF-8 encoding in bundle member: %s" % rel_path)
        self._blobs[sha] = text
        return text


def detect_profile(reader):
    """Detect whether reader represents an OpenSpec change, Spec Kit feature, or neither."""
    has_proposal = reader.file_exists("proposal.md")
    has_design = reader.file_exists("design.md")
    has_speckit_spec = reader.file_exists("spec.md")
    has_speckit_plan = reader.file_exists("plan.md")
    has_tasks = reader.file_exists("tasks.md")

    all_files = reader.list_files()
    has_openspec_specs = any(
        f.startswith("specs/") and f.endswith("/spec.md") and len(f.split("/")) >= 3
        for f in all_files
    )

    is_openspec = has_proposal or has_openspec_specs
    is_speckit = has_speckit_spec or has_speckit_plan

    if is_openspec and is_speckit:
        return "ambiguous", "folder contains conflicting OpenSpec (proposal/specs) and Spec Kit (spec.md/plan.md) layouts"
    if is_openspec:
        missing = []
        if not has_proposal:
            missing.append("proposal.md")
        if not has_openspec_specs:
            missing.append("at least one specs/**/spec.md delta specification")
        if not has_design:
            missing.append("design.md")
        if not has_tasks:
            missing.append("tasks.md")
        if missing:
            return "incomplete_openspec", "incomplete OpenSpec change bundle: missing %s" % ", ".join(missing)
        return "openspec", None
    if is_speckit:
        missing = []
        if not has_speckit_spec:
            missing.append("spec.md")
        if not has_speckit_plan:
            missing.append("plan.md")
        if not has_tasks:
            missing.append("tasks.md")
        if missing:
            return "incomplete_speckit", "incomplete Spec Kit feature bundle: missing %s" % ", ".join(missing)
        return "speckit", None

    return "unsupported", "unsupported specification folder layout: unrecognized bundle format"


def extract_openspec_units(reader, files, add_error):
    """Extract units from OpenSpec delta specs under specs/**/spec.md."""
    units = {}  # (source, unit_tuple) -> {"source": rel_path, "operation": op, "outcome": text}
    spec_files = [f for f in files if f.startswith("specs/") and f.endswith("/spec.md")]

    for sf in spec_files:
        text = reader.read_text(sf)
        lines = blank_comments_and_fences(text).splitlines()
        current_op = None
        current_req = None
        current_scenario = None
        scenario_then = []
        removed_reason = None
        removed_migration = None

        def flush_scenario():
            nonlocal current_scenario, scenario_then
            if current_scenario and current_req and current_op in ("ADDED", "MODIFIED"):
                key = (current_op, current_req, current_scenario)
                outcome = " ".join(scenario_then).strip()
                units[(sf, key)] = {"source": sf, "operation": current_op, "outcome": outcome}
            current_scenario = None
            scenario_then = []

        def flush_removed():
            nonlocal current_req, removed_reason, removed_migration
            if current_op == "REMOVED" and current_req:
                if not removed_reason or not removed_migration:
                    add_error("REMOVED requirement '%s' in %s requires both **Reason** and **Migration**"
                              % (current_req, sf))
                key = ("REMOVED", current_req)
                units[(sf, key)] = {"source": sf, "operation": "REMOVED", "outcome": ""}
            current_req = None
            removed_reason = None
            removed_migration = None

        for line in lines:
            h_match = _HEADING.match(line)
            if h_match:
                level = len(h_match.group(1))
                htext = h_match.group(2).strip()
                if level == 2:
                    flush_scenario()
                    flush_removed()
                    norm_h = htext.upper()
                    if "ADDED" in norm_h:
                        current_op = "ADDED"
                    elif "MODIFIED" in norm_h:
                        current_op = "MODIFIED"
                    elif "REMOVED" in norm_h:
                        current_op = "REMOVED"
                    elif "RENAMED" in norm_h:
                        current_op = "RENAMED"
                    else:
                        current_op = None
                    current_req = None
                    continue
                elif level == 3 and current_op:
                    flush_scenario()
                    flush_removed()
                    if htext.lower().startswith("requirement:"):
                        current_req = htext.split(":", 1)[1].strip()
                        if current_op == "RENAMED":
                            parts = re.split(r"\s+TO:\s+", current_req, flags=re.I)
                            if len(parts) == 2:
                                from_name = re.sub(r"^FROM:\s*", "", parts[0], flags=re.I).strip()
                                key = ("RENAMED", from_name, parts[1].strip())
                            else:
                                key = ("RENAMED", current_req)
                            units[(sf, key)] = {"source": sf, "operation": current_op, "outcome": ""}
                            current_req = None
                    continue
                elif level == 4 and current_op in ("ADDED", "MODIFIED") and current_req:
                    flush_scenario()
                    if htext.lower().startswith("scenario:"):
                        current_scenario = htext.split(":", 1)[1].strip()
                    else:
                        current_scenario = htext
                    continue

            if current_op == "REMOVED" and current_req:
                if re.search(r"\*{0,2}Reason\*{0,2}\s*:", line, re.I):
                    removed_reason = line.split(":", 1)[1].strip()
                elif re.search(r"\*{0,2}Migration\*{0,2}\s*:", line, re.I):
                    removed_migration = line.split(":", 1)[1].strip()

            if current_scenario:
                then_match = re.search(r"[-*]\s+\*{0,2}THEN\*{0,2}\s+(.*)", line, re.I)
                if then_match:
                    scenario_then.append(then_match.group(1).strip())
                elif scenario_then and line.startswith("  "):
                    scenario_then.append(line.strip())

        flush_scenario()
        flush_removed()

    return units


def extract_speckit_units(reader):
    """Extract units from Spec Kit spec.md."""
    units = {}
    if not reader.file_exists("spec.md"):
        return units
    text = reader.read_text("spec.md")
    lines = blank_comments_and_fences(text).splitlines()
    current_story = None
    current_scenario = None
    scenario_then = []

    def flush_scenario():
        nonlocal current_scenario, scenario_then
        if current_story and current_scenario:
            key = (current_story, current_scenario)
            outcome = " ".join(scenario_then).strip()
            units[("spec.md", key)] = {"source": "spec.md", "operation": "STORY", "outcome": outcome}
        current_scenario = None
        scenario_then = []

    for line in lines:
        h_match = _HEADING.match(line)
        if h_match:
            level = len(h_match.group(1))
            htext = h_match.group(2).strip()
            if level == 3:
                flush_scenario()
                s_match = re.search(r"\b(US\d+|User Story \d+)\b", htext, re.I)
                if s_match:
                    tag = s_match.group(1).upper().replace("USER STORY ", "US").replace(" ", "")
                    current_story = tag
                else:
                    current_story = htext.split("-")[0].strip()
                continue
            elif level == 4 and current_story:
                flush_scenario()
                sc_match = re.search(r"\b(Scenario \d+)\b", htext, re.I)
                if sc_match:
                    current_scenario = sc_match.group(1).title()
                elif htext.lower().startswith("scenario:"):
                    current_scenario = htext.split(":", 1)[1].strip()
                else:
                    current_scenario = htext.split("-")[0].strip()
                continue

        if current_scenario:
            then_match = re.search(r"[-*]\s+\*{0,2}THEN\*{0,2}\s+(.*)", line, re.I)
            if then_match:
                scenario_then.append(then_match.group(1).strip())
            elif scenario_then and line.startswith("  "):
                scenario_then.append(line.strip())

    flush_scenario()
    return units


def parse_sdlc_evidence_table(tasks_text):
    """Parse header metadata and ## SDLC evidence mapping table from tasks.md."""
    lines = blank_comments_and_fences(tasks_text).splitlines()
    in_evidence = False
    header = {}
    rows = []
    headers = None

    for line in lines:
        h_match = _HEADING.match(line)
        if h_match and len(h_match.group(1)) >= 2:
            section_title = h_match.group(2).strip().lower()
            if section_title in ("sdlc evidence", "sdlc-evidence", "evidence"):
                in_evidence = True
            else:
                in_evidence = False
            continue

        if not in_evidence:
            continue

        f_match = _HEADER_FIELD.match(line)
        if f_match:
            header[f_match.group("key").lower()] = f_match.group("value").strip()
            continue

        raw_stripped = line.strip()
        if raw_stripped.startswith("|") and raw_stripped.endswith("|"):
            cells = split_markdown_table_row(line)
            if not cells or all(re.match(r"^:?-+:?$", c) for c in cells):
                continue
            norm_cells = [c.lower() for c in cells]
            if "unit" in norm_cells and "source" in norm_cells:
                headers = norm_cells
                continue
            if headers:
                row_dict = {}
                for idx, col in enumerate(headers):
                    if idx < len(cells):
                        row_dict[col] = cells[idx]
                    else:
                        row_dict[col] = ""
                rows.append(row_dict)

    return header, rows


def validate_bundle(reader, kind, lane, repo_root, require_approved=False, require_tests_exist=False):
    """Validate an OpenSpec or Spec Kit bundle directory or reader.

    Returns (findings, criteria_count).
    Each finding is (level, line, message).
    """
    findings = []

    def add(level, line, message):
        findings.append((level, line, message))

    all_files = reader.list_files()
    if len(all_files) > MAX_BUNDLE_FILES:
        add("ERROR", 1, "bundle exceeds limit of %d files (%d found)" % (MAX_BUNDLE_FILES, len(all_files)))
        return findings, 0

    total_bytes = 0
    file_contents = {}
    for rel in all_files:
        try:
            content = reader.read_text(rel)
            total_bytes += len(content.encode("utf-8", errors="replace"))
            file_contents[rel] = content
        except BundleError as exc:
            add("ERROR", 1, str(exc))
            return findings, 0

    if total_bytes > MAX_BUNDLE_BYTES:
        add("ERROR", 1, "bundle aggregate size (%d bytes) exceeds budget of %d bytes" % (total_bytes, MAX_BUNDLE_BYTES))
        return findings, 0

    # Safety checks across all files
    for rel, content in file_contents.items():
        raw_lines = content.splitlines()
        for idx, line in enumerate(raw_lines, 1):
            scan = line[1:] if idx == 1 and line.startswith("\ufeff") else line
            if _HIDDEN.search(scan):
                add("ERROR", 1, "%s line %d: hidden Unicode control characters: remove them" % (rel, idx))
            for label, pattern in SECRETS:
                if pattern.search(line):
                    add("ERROR", 1, "%s line %d: possible secret (%s): remove it" % (rel, idx, label))

    profile, profile_err = detect_profile(reader)
    if profile_err:
        add("ERROR", 1, profile_err)
        return findings, 0

    # Extract declared units from specs
    def add_spec_err(msg):
        add("ERROR", 1, msg)

    if profile == "openspec":
        spec_units = extract_openspec_units(reader, all_files, add_spec_err)
    elif profile == "speckit":
        spec_units = extract_speckit_units(reader)
    else:
        spec_units = {}

    # Extract tasks.md evidence
    tasks_content = file_contents.get("tasks.md", "")
    tasks_header, table_rows = parse_sdlc_evidence_table(tasks_content)

    # Check approval status
    status = tasks_header.get("status")
    if not status and profile == "speckit" and "spec.md" in file_contents:
        for line in file_contents["spec.md"].splitlines()[:20]:
            m = _HEADER_FIELD.match(line)
            if m:
                tasks_header.setdefault(m.group("key").lower(), m.group("value").strip())
        status = tasks_header.get("status")

    if lane != "Lite":
        if not status:
            add("ERROR", 1, "%s %s needs 'Status: draft' or 'Status: approved' in tasks.md SDLC evidence" % (lane, kind))
        elif status.lower() not in ("draft", "approved"):
            add("ERROR", 1, "Status must be 'draft' or 'approved', got '%s'" % status)
        elif status.lower() == "approved":
            approver = tasks_header.get("approved-by")
            match = _APPROVED.match(approver) if approver else None
            if not match or parse_date(match.group("date")) is None or "_" in match.group("name"):
                add("ERROR", 1, "an approved spec needs 'Approved-by: Name (YYYY-MM-DD)' in tasks.md SDLC evidence")
        elif require_approved and status.lower() == "draft":
            add("ERROR", 1, "Status is draft: a %s change needs one human approval before build" % lane)

    # Critical artifacts requirement
    if lane == "Critical":
        for risk_file, label in (("threat-note.md", "Threat considerations"), ("rollout-plan.md", "Rollout constraints")):
            if not reader.file_exists(risk_file):
                add("ERROR", 1, "Critical bundle requires '%s' with substantive %s" % (risk_file, label.lower()))
            else:
                art_content = file_contents.get(risk_file, "")
                if meaningful_chars(art_content) < MIN_ARTIFACT_CHARS:
                    add("ERROR", 1, "Critical artifact '%s' is empty or placeholder only" % risk_file)

    # Validate mapping table rows
    mapped_units = set()
    for row in table_rows:
        unit_raw = row.get("unit", "").strip()
        source_rel = row.get("source", "").strip()
        test_ref = row.get("test", "").strip()
        fails_before = row.get("fails before", row.get("fails-before", "")).strip()
        expected = row.get("expected result", row.get("expected-result", "")).strip()

        try:
            unit_parsed = json.loads(unit_raw)
            if isinstance(unit_parsed, list):
                unit_key = tuple(unit_parsed)
            else:
                unit_key = (str(unit_parsed),)
        except Exception:
            add("ERROR", 1, "malformed Unit cell (must be JSON array string): %s" % unit_raw)
            continue

        mapping_lookup_key = (source_rel, unit_key)
        if mapping_lookup_key in mapped_units:
            add("ERROR", 1, "duplicate mapping for unit %s in %s" % (json.dumps(list(unit_key)), source_rel))
        mapped_units.add(mapping_lookup_key)

        if mapping_lookup_key not in spec_units:
            add("ERROR", 1, "mapping refers to unknown source unit %s in %s" % (json.dumps(list(unit_key)), source_rel))
        else:
            unit_info = spec_units[mapping_lookup_key]
            spec_outcome = unit_info.get("outcome", "").strip()
            # If scenario defines a THEN outcome, the mapping cannot alter it
            if spec_outcome and expected and norm(expected) != norm(spec_outcome):
                add("ERROR", 1, "mapping expected result '%s' cannot replace source THEN outcome '%s' for unit %s"
                    % (expected, spec_outcome, json.dumps(list(unit_key))))
            # For removal/rename operations, an explicit expected result is mandatory
            if unit_info.get("operation") in ("REMOVED", "RENAMED") and not expected:
                add("ERROR", 1, "operation %s for unit %s requires an explicit Expected result transition expectation"
                    % (unit_info.get("operation"), json.dumps(list(unit_key))))

        if len(fails_before) < MIN_PASS_CHARS or fails_before.lower() in ("n/a", "none"):
            add("ERROR", 1, "fails-before for %s must explain failure today" % json.dumps(list(unit_key)))

        if not test_ref:
            add("ERROR", 1, "test reference missing for unit %s" % json.dumps(list(unit_key)))
        elif require_tests_exist and repo_root:
            from check_spec import test_path_problem
            prob = test_path_problem(test_ref, repo_root)
            if prob:
                add("ERROR", 1, "test '%s': %s" % (test_ref[:60], prob))

    # Check unmapped spec units
    for (sf, u_key), u_info in sorted(spec_units.items()):
        if (sf, u_key) not in mapped_units:
            add("ERROR", 1, "acceptance unit %s in %s has no test expectation in tasks.md" % (json.dumps(list(u_key)), sf))

    criteria_count = len(mapped_units)
    max_c = MAX_CRITERIA.get(lane, 15)
    if criteria_count > max_c:
        add("ERROR", 1, "%d criteria exceeds the %s cap of %d" % (criteria_count, lane, max_c))

    if criteria_count == 0 and kind == "spec":
        add("ERROR", 1, "no acceptance criteria or scenario mappings found in bundle")

    return findings, criteria_count
