"""Offline checks for the deliberately bounded comparison-table format."""

import datetime
import importlib.util
from pathlib import Path
import posixpath
import re
import unittest
from unittest import mock
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("comparison_evidence_parser", ROOT / "scripts/evidence_check.py")
evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evidence)

TOOLS = ("Spec Kit", "OpenSpec", "Kiro", "BMAD", "Superpowers", "Tessl")
HEADERS = ("Tool", "Version / surface", "Documented capabilities", "Fit / limits", "Evidence", "Primary sources", "Checked")
SOURCES = {
    "Spec Kit": {"github.com": ("/github/spec-kit",), "github.github.io": ("/spec-kit",),
                 "pypi.org": ("/project/specify-cli",)},
    "OpenSpec": {"github.com": ("/fission-ai/openspec",), "openspec.dev": ("/docs",)},
    "Kiro": {"kiro.dev": ("/docs", "/changelog")},
    "BMAD": {"github.com": ("/bmad-code-org/bmad-method",), "docs.bmad-method.org": ("/",)},
    "Superpowers": {"github.com": ("/obra/superpowers",)},
    "Tessl": {"docs.tessl.io": ("/",), "tessl.io": ("/",)},
}
LINK = re.compile(r"\[[^\]\n]+\]\(([^()\s]+)\)")
PLACEHOLDERS = {"", "-", "?", "none", "n/a", "todo", "tbd", "unknown", "unverified", "rolling"}


def primary_url(url, tool):
    if "\\" in url or any(character.isspace() or ord(character) < 32 for character in url):
        return False
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443):
            return False
        prefixes = SOURCES.get(tool, {}).get(parsed.hostname, ())
        path = posixpath.normpath(unquote(parsed.path or "/"))
        if parsed.hostname == "github.com":
            path = path.lower()
        return any(prefix == "/" or path == prefix or path.startswith(prefix + "/") for prefix in prefixes)
    except ValueError:
        return False


def comparison_issues(text, heading, tools, today=None):
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    visible = [(number + 1, line) for number, line, hidden in evidence._scan(text) if not hidden]
    headings = [index for index, (_, line) in enumerate(visible) if line.strip() == "## " + heading]
    if len(headings) != 1:
        return ["expected exactly one section: " + heading]
    start = headings[0] + 1
    end = next((index for index in range(start, len(visible))
                if re.match(r"^\s{0,3}#{1,2}\s", visible[index][1])), len(visible))
    lines = [(number, line.strip()) for number, line in visible[start:end] if line.lstrip().startswith("|")]
    if len(lines) < 3:
        return [heading + ": missing or empty comparison table"]

    def cells(line):
        if not line.startswith("|") or not line.endswith("|"):
            return []
        return [cell.strip().replace(r"\|", "|") for cell in re.split(r"(?<!\\)\|", line[1:-1])]

    if tuple(cells(lines[0][1])) != HEADERS:
        return [heading + ": comparison header does not match the required columns"]
    separators = cells(lines[1][1])
    if len(separators) != len(HEADERS) or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separators):
        return [heading + ": invalid table separator"]
    issues, seen = [], set()
    for number, line in lines[2:]:
        row = cells(line)
        if len(row) != len(HEADERS):
            issues.append("line %s: expected %s cells" % (number, len(HEADERS)))
            continue
        tool, version, capabilities, fit, qualification, sources, checked = row
        label = "%s (line %s)" % (tool or "unnamed tool", number)
        if tool not in tools:
            issues.append(label + ": unexpected tool")
            continue
        if tool in seen:
            issues.append(label + ": duplicate tool")
        seen.add(tool)
        for name, value in zip(HEADERS[1:], row[1:]):
            if value.lower() in PLACEHOLDERS or re.search(r"\b(?:TODO|TBD)\b|\{\{|<fill", value, re.I):
                issues.append(label + ": missing or placeholder " + name)
        if re.match(r"^(?:unverified|rolling)\b", version, re.I) and (":" not in version or len(version.split(":", 1)[1].strip()) < 10):
            issues.append(label + ": unverified/rolling version needs a scoped explanation")
        if not {"[report-stated]", "[extrapolated]"}.issubset(set(re.findall(r"\[[^\]]+\]", qualification))):
            issues.append(label + ": qualify documented capabilities and fit judgments")
        links = LINK.findall(sources)
        residue = LINK.sub("", sources).replace("<br>", "").strip()
        if not links or residue or not all(primary_url(url, tool) for url in links):
            issues.append(label + ": primary sources must be reviewed HTTPS links for this tool")
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", checked):
                raise ValueError("date format")
            if datetime.date.fromisoformat(checked) > today:
                raise ValueError("future date")
        except ValueError:
            issues.append(label + ": checked date must be valid ISO and not in the future")
    for tool in tools:
        if tool not in seen:
            issues.append(heading + ": missing required tool " + tool)
    return issues


class ComparisonContract(unittest.TestCase):
    TODAY = datetime.date(2026, 11, 9)

    def rows(self, tools=TOOLS):
        rows = []
        for tool in tools:
            host, prefixes = next(iter(SOURCES[tool].items()))
            rows.append([tool, "1.0.0 snapshot", "Documented capability", "Evaluate this workflow fit",
                         "[report-stated] capabilities; [extrapolated] fit",
                         "[primary](https://%s%s)" % (host, prefixes[0]), "2026-11-09"])
        return rows

    def table(self, rows, heading="Tool comparison"):
        return ("## " + heading + "\n\n| " + " | ".join(HEADERS) + " |\n| " +
                " | ".join(["---"] * len(HEADERS)) + " |\n" +
                "\n".join("| " + " | ".join(row) + " |" for row in rows) + "\n")

    def issues(self, text, heading="Tool comparison", tools=TOOLS):
        return comparison_issues(text, heading, tools, self.TODAY)

    def test_valid_detailed_and_summary_tables(self):
        self.assertEqual(self.issues(self.table(self.rows())), [])
        self.assertEqual(self.issues(self.table(self.rows(TOOLS[:-1]), "How This Compares"),
                                     "How This Compares", TOOLS[:-1]), [])

    def test_absent_empty_duplicate_or_wrong_sections_fail(self):
        valid = self.table(self.rows())
        for text in ("", self.table([]), self.table(self.rows()[:-1]), valid + valid,
                     valid.replace("## Tool comparison", "## Other section"), valid.replace("---", "--", 1)):
            with self.subTest(text=text[:60]):
                self.assertTrue(self.issues(text))

    def test_missing_or_placeholder_metadata_fails(self):
        for column in range(1, len(HEADERS)):
            for value in ("", "TBD", "-"):
                with self.subTest(column=HEADERS[column], value=value):
                    rows = self.rows()
                    rows[0][column] = value
                    issues = self.issues(self.table(rows))
                    self.assertTrue(issues)
                    self.assertIn("Spec Kit", "\n".join(issues))

    def test_duplicate_unknown_and_malformed_rows_fail(self):
        for kind in ("duplicate", "unknown", "short", "long"):
            rows = self.rows()
            if kind == "duplicate":
                rows.append(rows[0])
            elif kind == "unknown":
                rows[0][0] = "Unknown product"
            elif kind == "short":
                rows[0].pop()
            else:
                rows[0].append("extra")
            with self.subTest(kind=kind):
                self.assertTrue(self.issues(self.table(rows)))

    def test_bad_dates_fail_against_a_fixed_clock(self):
        for date in ("2026-02-30", "20261109", "today", "2026-11-10"):
            with self.subTest(date=date):
                rows = self.rows()
                rows[0][-1] = date
                self.assertTrue(self.issues(self.table(rows)))

    def test_primary_source_authority_is_not_a_substring_match(self):
        for url in ("http://github.com/github/spec-kit", "https://github.com.evil.invalid/github/spec-kit",
                    "https://github.com@evil.invalid/github/spec-kit", "https://github.com/unrelated/spec-kit",
                    "https://github.com/github/spec-kit-extra", "https://github.com/github/spec-kit/../other",
                    "https://github.com/github/spec-kit/%2e%2e/other", "https://github.com:bad/github/spec-kit",
                    "docs/spec-kit.md", "javascript:alert", "https://github.com\\evil.invalid/github/spec-kit"):
            with self.subTest(url=url):
                rows = self.rows()
                rows[0][-2] = "[source](%s)" % url
                self.assertTrue(self.issues(self.table(rows)))

    def test_tables_hidden_in_comments_or_code_do_not_count(self):
        table = self.table(self.rows())
        for text in ("<!--\n" + table + "-->\n", "```markdown\n" + table + "```\n",
                     "~~~\n" + table + "~~~\n"):
            self.assertTrue(self.issues(text))

    def test_escaped_pipes_do_not_create_extra_cells(self):
        rows = self.rows()
        rows[0][2] = r"Workflows \| gates"
        self.assertEqual(self.issues(self.table(rows)), [])

    def test_rolling_or_unverified_versions_need_context(self):
        for version in ("rolling", "unverified", "Unverified: ?"):
            rows = self.rows()
            rows[0][1] = version
            self.assertTrue(self.issues(self.table(rows)))
        rows[0][1] = "Rolling: no fixed release on the reviewed page"
        self.assertEqual(self.issues(self.table(rows)), [])

    def test_metadata_check_does_not_fetch_sources(self):
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network call")), \
                mock.patch("socket.create_connection", side_effect=AssertionError("network call")):
            self.assertEqual(self.issues(self.table(self.rows())), [])


class PublishedComparison(unittest.TestCase):
    def test_detailed_comparison_meets_contract(self):
        path = ROOT / "docs/COMPARISON.md"
        self.assertTrue(path.is_file(), "docs/COMPARISON.md is missing")
        issues = comparison_issues(path.read_text(encoding="utf-8"), "Tool comparison", TOOLS)
        self.assertEqual(issues, [], "docs/COMPARISON.md:\n" + "\n".join(issues))

    def test_readme_summary_meets_contract(self):
        issues = comparison_issues((ROOT / "README.md").read_text(encoding="utf-8"), "How This Compares", TOOLS[:-1])
        self.assertEqual(issues, [], "README.md:\n" + "\n".join(issues))


if __name__ == "__main__":
    unittest.main()
