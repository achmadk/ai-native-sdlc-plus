#!/usr/bin/env python3
"""trace_lint.py - cheap heuristics that PR evidence is more than empty paperwork.

evidence_check.py answers "does the evidence exist?". This tool asks a few
follow-up questions that catch the commonest ways to satisfy a presence check
without doing the work:

  placeholder   unedited template text (TODO, TBD, <describe ...>, {{var}} ...)
  empty-section a markdown heading with nothing under it
  empty-field   a "Label:" line with no value
  bad-link      a relative link whose target file does not exist
  no-spec-link  (opt-in) no link at all in the body
  no-tests      Standard/Critical change that touches source but no test files
  no-independent-reviewer
                the only recorded reviewer is the author

It is heuristic by design and never judges whether content is *good*.
Standard library only; no network.

Usage:
  python3 scripts/trace_lint.py --body-file pr_body.md \\
      --changed-files changed.txt --lane Standard --author alice --reviewer bob
  gh pr view 12 --json body -q .body | \\
      python3 scripts/trace_lint.py --body-file - --git-diff origin/main --lane Standard

Exit status: 0 = no errors, 1 = errors found, 2 = bad invocation.
--advisory forces exit 0; --strict promotes warnings to errors.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import List, Optional, Sequence

ERROR = "ERROR"
WARNING = "WARNING"


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    line: Optional[int] = None

    def render(self) -> str:
        where = f" (line {self.line})" if self.line else ""
        return f"{self.level}: [{self.code}] {self.message}{where}"


# --------------------------------------------------------------------------
# Text preparation
# --------------------------------------------------------------------------

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCE = re.compile(r"^\s{0,3}(```|~~~)")


def strip_html_comments(text: str) -> str:
    """Drop <!-- ... --> (template instructions) but keep line numbering."""
    return _HTML_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def fence_mask(lines: Sequence[str]) -> List[bool]:
    """True for lines inside (or delimiting) a fenced code block."""
    mask = [False] * len(lines)
    inside = False
    marker = ""
    for i, line in enumerate(lines):
        m = _FENCE.match(line)
        if m:
            if not inside:
                inside, marker, mask[i] = True, m.group(1), True
                continue
            if m.group(1) == marker:
                inside, mask[i] = False, True
                continue
        mask[i] = inside
    return mask


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

PLACEHOLDER_PATTERNS = [
    ("TODO/TBD marker", re.compile(r"\b(?:TODO|TBD|FIXME)\b")),
    ("fill-in marker", re.compile(r"\bfill\s*(?:me|in)\b", re.I)),
    (
        "angle-bracket placeholder",
        re.compile(
            r"<(?:your|describe|link|paste|insert|add|enter|name|what|why|how|"
            r"summary|description)\s+[^<>\n]*>",
            re.I,
        ),
    ),
    ("template variable", re.compile(r"\{\{[^{}\n]*\}\}")),
    ("lorem ipsum", re.compile(r"lorem ipsum", re.I)),
    ("ellipsis-only value", re.compile(r":\s*(?:\.\.\.|\u2026)\s*$")),
]


def check_placeholders(lines: Sequence[str], ignore: Sequence["re.Pattern[str]"]) -> List[Finding]:
    out: List[Finding] = []
    for i, line in enumerate(lines, 1):
        if any(rx.search(line) for rx in ignore):
            continue
        for name, rx in PLACEHOLDER_PATTERNS:
            if rx.search(line):
                out.append(
                    Finding(ERROR, "placeholder", f"unfilled template text ({name}): {line.strip()[:80]!r}", i)
                )
                break
    return out


_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(\S.*)$")


def check_empty_sections(lines: Sequence[str], mask: Sequence[bool]) -> List[Finding]:
    heads = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        m = _HEADING.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
    out: List[Finding] = []
    for n, (i, level, title) in enumerate(heads):
        if n + 1 < len(heads):
            nxt_i, nxt_level, _ = heads[n + 1]
            if nxt_level > level:
                continue  # parent of a deeper heading; the child is judged on its own
            end = nxt_i
        else:
            end = len(lines)
        if not any(s.strip() for s in lines[i + 1 : end]):
            out.append(Finding(WARNING, "empty-section", f"section {title!r} has no content", i + 1))
    return out


_LABEL_ONLY = re.compile(r"^(\s*)([-*+]\s+)?([A-Za-z][^:\n]{0,40}):\s*$")
_LABEL_VALUE = re.compile(r"^\s*(?:[-*+]\s+)?[A-Za-z][^:\n]{0,40}:\s+\S")
_BULLET = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+\S")


def _plain(line: str) -> str:
    return line.replace("**", "").replace("__", "")


def _indent(line: str) -> int:
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip())


def _has_content(line: str, label_indent: int, label_is_bullet: bool) -> bool:
    if _HEADING.match(line):
        return False
    plain = _plain(line)
    if _FENCE.match(line) or plain.lstrip().startswith("|"):
        return True
    if _indent(plain) > label_indent:
        return True
    if _BULLET.match(plain):
        # "- Label:" followed by a sibling bullet means the label is empty;
        # "Label:" followed by bullets means the bullets are its value.
        return not label_is_bullet
    if _LABEL_VALUE.match(plain) or _LABEL_ONLY.match(plain):
        return False
    return True  # plain paragraph continuing the label


def check_empty_fields(lines: Sequence[str], mask: Sequence[bool]) -> List[Finding]:
    out: List[Finding] = []
    for i, raw in enumerate(lines):
        if mask[i]:
            continue
        m = _LABEL_ONLY.match(_plain(raw))
        if not m:
            continue
        label_indent = len(m.group(1).expandtabs(4))
        label_is_bullet = bool(m.group(2))
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines) or not _has_content(lines[j], label_indent, label_is_bullet):
            out.append(Finding(WARNING, "empty-field", f"field {m.group(3).strip()!r} has no value", i + 1))
    return out


_MD_LINK = re.compile(r"\[[^\]\n]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_SCHEME = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.I)


def check_links(
    lines: Sequence[str], mask: Sequence[bool], root: Path, require_link: bool
) -> List[Finding]:
    out: List[Finding] = []
    good = 0
    root_resolved = root.resolve()
    for i, line in enumerate(lines, 1):
        if mask[i - 1]:
            continue
        for m in _MD_LINK.finditer(line):
            target = m.group(1)
            if target.startswith("#"):
                continue
            if _SCHEME.match(target):
                if target.lower().startswith(("http://", "https://")):
                    good += 1
                continue
            path = re.split(r"[#?]", target, maxsplit=1)[0]
            if not path:
                continue
            resolved = (root_resolved / path.lstrip("/")).resolve()
            try:
                resolved.relative_to(root_resolved)
            except ValueError:
                out.append(Finding(ERROR, "bad-link", f"link escapes the repository root: {path}", i))
                continue
            if resolved.exists():
                good += 1
            else:
                out.append(Finding(ERROR, "bad-link", f"link target not found: {path}", i))
    if require_link and good == 0:
        out.append(Finding(ERROR, "no-spec-link", "no usable link found (expected a link to the spec or intent)"))
    return out


_TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|specs?)/"
    r"|(^|/)test_[^/]+\.py$"
    r"|_test\.(py|go|rb|js|jsx|ts|tsx|rs)$"
    r"|\.(test|spec)\.[cm]?[jt]sx?$"
    r"|(Test|Tests)\.(java|kt|cs)$"
    r"|_spec\.rb$",
    re.I,
)
_NON_SOURCE = re.compile(
    r"(^|/)(docs?|assets)/|^\.github/|\.(md|mdx|rst|txt|adoc)$|(^|/)(LICENSE|CHANGELOG|CODEOWNERS|\.gitignore)$",
    re.I,
)


def check_tests(changed: Sequence[str], lane: str) -> List[Finding]:
    if lane.strip().lower() not in ("standard", "critical"):
        return []
    files = [f.replace("\\", "/") for f in changed if f.strip()]
    source = [f for f in files if not _NON_SOURCE.search(f)]
    tests = [f for f in files if _TEST_PATH.search(f)]
    if source and not tests:
        return [
            Finding(
                ERROR,
                "no-tests",
                f"{lane} lane changes {len(source)} source file(s) but no test files (e.g. {source[0]})",
            )
        ]
    return []


def check_review(author: str, reviewers: Sequence[str]) -> List[Finding]:
    independent = [r for r in reviewers if r.strip().lower() != author.strip().lower()]
    if independent:
        return []
    why = "no reviewer recorded" if not reviewers else "the only reviewer is the author"
    return [Finding(WARNING, "no-independent-reviewer", f"{why}")]


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def lint(
    body: str,
    *,
    root: str = ".",
    changed: Optional[Sequence[str]] = None,
    lane: Optional[str] = None,
    author: Optional[str] = None,
    reviewers: Sequence[str] = (),
    require_spec_link: bool = False,
    ignore_patterns: Sequence[str] = (),
    strict: bool = False,
) -> List[Finding]:
    if not body.strip():
        return [Finding(ERROR, "empty-body", "PR body is empty")]
    lines = strip_html_comments(body).splitlines()
    mask = fence_mask(lines)
    ignore = [re.compile(p) for p in ignore_patterns]

    findings: List[Finding] = []
    findings += check_placeholders(lines, ignore)
    findings += check_empty_sections(lines, mask)
    findings += check_empty_fields(lines, mask)
    findings += check_links(lines, mask, Path(root), require_spec_link)
    if changed is not None and lane:
        findings += check_tests(changed, lane)
    if author:
        findings += check_review(author, reviewers)

    if strict:
        findings = [replace(f, level=ERROR) for f in findings]
    return sorted(findings, key=lambda f: (f.line is None, f.line or 0, f.code))


def _read_lines(path: str) -> List[str]:
    return [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]


def _git_changed(base: str, root: str) -> List[str]:
    p = subprocess.run(
        ["git", "-C", root, "diff", "--name-only", "-z", f"{base}...HEAD"],
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "git diff failed")
    return [x for x in p.stdout.split("\0") if x]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Heuristic checks on PR evidence (see module docstring).")
    ap.add_argument("--body-file", required=True, help="PR body markdown file, or - for stdin")
    ap.add_argument("--root", default=".", help="repository root for resolving relative links")
    ap.add_argument("--lane", help="Lite | Standard | Critical (enables the test-file check)")
    ap.add_argument("--changed-files", help="file listing changed paths, one per line")
    ap.add_argument("--git-diff", metavar="BASE", help="use `git diff --name-only BASE...HEAD` for changed files")
    ap.add_argument("--author", help="PR author login (enables the independent-reviewer check)")
    ap.add_argument("--reviewer", action="append", default=[], help="reviewer login; repeatable")
    ap.add_argument("--require-spec-link", action="store_true", help="error when the body has no usable link")
    ap.add_argument("--ignore-line", action="append", default=[], metavar="REGEX", help="skip placeholder check on matching lines")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--advisory", action="store_true", help="always exit 0")
    args = ap.parse_args(argv)

    try:
        body = sys.stdin.read() if args.body_file == "-" else Path(args.body_file).read_text(encoding="utf-8")
        changed: Optional[List[str]] = None
        if args.changed_files:
            changed = _read_lines(args.changed_files)
        elif args.git_diff:
            changed = _git_changed(args.git_diff, args.root)
        for pattern in args.ignore_line:
            re.compile(pattern)
    except (OSError, RuntimeError, re.error) as exc:
        print(f"trace_lint: {exc}", file=sys.stderr)
        return 2

    findings = lint(
        body,
        root=args.root,
        changed=changed,
        lane=args.lane,
        author=args.author,
        reviewers=args.reviewer,
        require_spec_link=args.require_spec_link,
        ignore_patterns=args.ignore_line,
        strict=args.strict,
    )
    for f in findings:
        print(f.render())
    errors = sum(1 for f in findings if f.level == ERROR)
    warnings = len(findings) - errors
    print(f"trace_lint: {errors} error(s), {warnings} warning(s)")
    return 0 if args.advisory or errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
