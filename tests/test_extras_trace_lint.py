import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import trace_lint as tl  # noqa: E402


def codes(findings):
    return [f.code for f in findings]


class PlaceholderTests(unittest.TestCase):
    def test_html_comments_are_ignored(self):
        body = "## Intent\n<!-- TODO: explain the change -->\nFix the parser.\n"
        self.assertEqual(codes(tl.lint(body)), [])

    def test_todo_is_an_error(self):
        findings = tl.lint("## Intent\nTODO fill this in\n")
        self.assertIn("placeholder", codes(findings))
        self.assertEqual(findings[0].level, tl.ERROR)

    def test_angle_and_template_placeholders(self):
        for text in ("Spec: <link to spec>", "Model: {{model}}", "Notes: lorem ipsum", "Risk: ..."):
            with self.subTest(text=text):
                self.assertIn("placeholder", codes(tl.lint("## A\n" + text + "\n")))

    def test_real_html_tags_are_not_placeholders(self):
        body = "## Notes\n<details><summary>Logs</summary>ok</details>\n"
        self.assertNotIn("placeholder", codes(tl.lint(body)))

    def test_ignore_line_pattern(self):
        body = "## Notes\nRemoved TODO comments from the parser\n"
        self.assertIn("placeholder", codes(tl.lint(body)))
        self.assertNotIn("placeholder", codes(tl.lint(body, ignore_patterns=[r"Removed TODO"])))

    def test_empty_body(self):
        self.assertEqual(codes(tl.lint("  \n")), ["empty-body"])


class StructureTests(unittest.TestCase):
    def test_empty_section_is_a_warning(self):
        findings = tl.lint("## Intent\n\n## Lane\nLite\n")
        self.assertEqual(codes(findings), ["empty-section"])
        self.assertEqual(findings[0].level, tl.WARNING)

    def test_parent_heading_with_child_is_not_empty(self):
        self.assertEqual(codes(tl.lint("## Trace\n### Prompts\nused model X\n")), [])

    def test_headings_inside_fences_are_ignored(self):
        body = "## Run\n```\n# not a heading\n```\n"
        self.assertEqual(codes(tl.lint(body)), [])

    def test_empty_field(self):
        self.assertEqual(codes(tl.lint("## Trace\nModel:\nPrompt: refactor\n")), ["empty-field"])

    def test_field_with_value_or_bullets_is_fine(self):
        body = "## Trace\nModel: sonnet\nRejected alternatives:\n- regex\n- parser generator\n"
        self.assertEqual(codes(tl.lint(body)), [])

    def test_sibling_bullet_fields_flag_the_empty_one(self):
        body = "## Trace\n- Model:\n- Prompt: refactor\n"
        self.assertEqual(codes(tl.lint(body)), ["empty-field"])

    def test_bold_labels_are_recognised(self):
        self.assertEqual(codes(tl.lint("## Trace\n**Model:**\n")), ["empty-field"])


class LinkTests(unittest.TestCase):
    def test_missing_and_existing_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "docs").mkdir()
            (Path(tmp) / "docs" / "spec.md").write_text("spec", encoding="utf-8")
            ok = tl.lint("## Spec\nSee [spec](docs/spec.md#ac1)\n", root=tmp)
            bad = tl.lint("## Spec\nSee [spec](docs/nope.md)\n", root=tmp)
            self.assertEqual(codes(ok), [])
            self.assertEqual(codes(bad), ["bad-link"])

    def test_link_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            findings = tl.lint("## Spec\n[x](../../etc/passwd)\n", root=tmp)
            self.assertEqual(codes(findings), ["bad-link"])
            self.assertIn("escapes", findings[0].message)

    def test_require_spec_link(self):
        self.assertIn("no-spec-link", codes(tl.lint("## Spec\nNone\n", require_spec_link=True)))
        body = "## Spec\n[issue](https://github.com/o/r/issues/1)\n"
        self.assertNotIn("no-spec-link", codes(tl.lint(body, require_spec_link=True)))

    def test_links_in_code_fences_are_skipped(self):
        body = "## Spec\n```\n[x](missing.md)\n```\n"
        self.assertEqual(codes(tl.lint(body)), [])


class LaneAndReviewTests(unittest.TestCase):
    BODY = "## Intent\nFix it\n"

    def test_standard_without_tests_is_an_error(self):
        findings = tl.lint(self.BODY, lane="Standard", changed=["src/app.py"])
        self.assertEqual(codes(findings), ["no-tests"])

    def test_standard_with_tests_passes(self):
        findings = tl.lint(self.BODY, lane="Standard", changed=["src/app.py", "tests/test_app.py"])
        self.assertEqual(codes(findings), [])

    def test_lite_and_docs_only_do_not_need_tests(self):
        self.assertEqual(codes(tl.lint(self.BODY, lane="Lite", changed=["src/app.py"])), [])
        self.assertEqual(codes(tl.lint(self.BODY, lane="Critical", changed=["docs/a.md", "README.md"])), [])

    def test_windows_paths_are_normalised(self):
        findings = tl.lint(self.BODY, lane="Critical", changed=["src\\a.py", "tests\\test_a.py"])
        self.assertEqual(codes(findings), [])

    def test_self_review_warns(self):
        findings = tl.lint(self.BODY, author="Alice", reviewers=["alice"])
        self.assertEqual(codes(findings), ["no-independent-reviewer"])
        self.assertEqual(codes(tl.lint(self.BODY, author="alice", reviewers=["alice", "bob"])), [])
        self.assertEqual(codes(tl.lint(self.BODY, author="alice")), ["no-independent-reviewer"])

    def test_strict_promotes_warnings(self):
        findings = tl.lint("## Intent\n\n## Lane\nLite\n", strict=True)
        self.assertTrue(findings and all(f.level == tl.ERROR for f in findings))


class CliTests(unittest.TestCase):
    def run_main(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = tl.main(argv)
        return rc, buf.getvalue()

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.md"
            bad = Path(tmp) / "bad.md"
            good.write_text("## Intent\nFix the parser\n", encoding="utf-8")
            bad.write_text("## Intent\nTODO\n", encoding="utf-8")
            self.assertEqual(self.run_main(["--body-file", str(good)])[0], 0)
            rc, out = self.run_main(["--body-file", str(bad)])
            self.assertEqual(rc, 1)
            self.assertIn("[placeholder]", out)
            self.assertEqual(self.run_main(["--body-file", str(bad), "--advisory"])[0], 0)

    def test_missing_body_file_is_exit_2(self):
        buf = io.StringIO()
        old = sys.stderr
        sys.stderr = buf
        try:
            rc = tl.main(["--body-file", "/nonexistent/body.md"])
        finally:
            sys.stderr = old
        self.assertEqual(rc, 2)

    def test_changed_files_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "b.md"
            changed = Path(tmp) / "c.txt"
            body.write_text("## Intent\nFix\n", encoding="utf-8")
            changed.write_text("src/a.py\n", encoding="utf-8")
            rc, out = self.run_main(["--body-file", str(body), "--changed-files", str(changed), "--lane", "Standard"])
            self.assertEqual(rc, 1)
            self.assertIn("[no-tests]", out)


if __name__ == "__main__":
    unittest.main()
