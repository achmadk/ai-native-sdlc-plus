import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "skills", "spec-first", "scripts"))
import check_spec as cs  # noqa: E402

HEADER = "# Spec: x\nLane: Standard\nAuthor: Dana Lee\nStatus: approved\nApproved-by: Priya Rao (2026-10-02)\n"
AC = "- AC1: a wrong password is rejected | pass: HTTP 401 and no session cookie set"
TEST = "- AC1 -> tests/test_a.py::test_bad_password | fails-before: the rejection path does not exist yet"


def spec(header=HEADER, intent="Users can sign in safely.", out="- Password reset", criteria=AC, constraints="- No cookie change",
         tests=TEST, assumptions="- none", plan="Add the check.", extra=""):
    parts = [header]
    for title, body in (("Intent", intent), ("Out of scope", out), ("Acceptance criteria", criteria), ("Constraints", constraints),
                        ("Test expectations", tests), ("Assumptions and open questions", assumptions), ("Plan", plan)):
        if body is not None:
            parts.append("## %s\n%s\n" % (title, body))
    if extra:
        parts.append(extra)
    return "\n".join(parts)


class Base(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.repo, "tests"))
        with open(os.path.join(self.repo, "tests", "test_a.py"), "w") as handle:
            handle.write("# test\n")

    def run_check(self, text, kind="spec", lane="Standard", approved=False, exist=False):
        return cs.check(text, kind, lane, self.repo, approved, exist)

    def errors(self, text, **kw):
        return [m for level, _, m in self.run_check(text, **kw)[0] if level == "ERROR"]

    def warns(self, text, **kw):
        return [m for level, _, m in self.run_check(text, **kw)[0] if level == "WARN"]

    def assertError(self, text, fragment, **kw):
        found = self.errors(text, **kw)
        self.assertTrue(any(fragment in m for m in found), "%r not in %r" % (fragment, found))

    def run_main(self, text, *args):
        path = os.path.join(self.repo, "spec.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cs.main([path, "--repo-root", self.repo] + list(args))
        return code, out.getvalue(), err.getvalue()


class Valid(Base):
    def test_a_good_standard_spec_passes(self):
        findings, count = self.run_check(spec())
        self.assertEqual([f for f in findings if f[0] == "ERROR"], [])
        self.assertEqual(count, 1)

    def test_a_minimal_lite_spec_passes_without_a_status(self):
        text = "# Spec: x\n\n## Intent\nFix the footer.\n\n## Acceptance criteria\n" + AC + "\n\n## Test expectations\n" + TEST + "\n"
        self.assertEqual(self.errors(text, lane="Lite"), [])

    def test_guidance_comments_are_ignored(self):
        text = spec(extra="<!-- - AC9: this is only an example | pass: ignore it\n## Fake Section -->")
        self.assertEqual(self.errors(text), [])

    def test_header_placeholders_are_fine_but_not_in_sections(self):
        self.assertEqual(self.errors(spec(header=HEADER.replace("Dana Lee", "___"))), [])
        self.assertError(spec(plan="___"), "unfilled blank")
        self.assertError(spec(plan="TBD after discussion"), "unfilled blank")


class Criteria(Base):
    def test_malformed_criterion(self):
        self.assertError(spec(criteria="- AC1: no pass condition here"), "not in criterion format")
        self.assertError(spec(criteria="- Users can log in | pass: it works"), "not in criterion format")

    def test_a_criteria_section_with_only_prose_is_an_error(self):
        self.assertError(spec(criteria="Users should be able to log in quickly."), "no acceptance criteria found")

    def test_duplicate_ids(self):
        self.assertError(spec(criteria=AC + "\n" + AC), "defined twice")

    def test_pass_condition_boundary(self):
        self.assertEqual(self.errors(spec(criteria=AC.replace("HTTP 401 and no session cookie set", "x" * 8))), [])
        self.assertError(spec(criteria=AC.replace("HTTP 401 and no session cookie set", "x" * 7)), "needs a pass condition")

    def test_vague_wording_warns_only_without_a_number(self):
        vague = "- AC1: login is faster and works properly | pass: it is quick and robust"
        warns = self.warns(spec(criteria=vague, tests=TEST))
        self.assertTrue(any("vague wording" in w for w in warns))
        self.assertEqual(self.errors(spec(criteria=vague)), [])  # a tripwire, not an error
        numeric = "- AC1: login is faster | pass: p95 under 300 ms (was 800 ms)"
        self.assertFalse(any("vague" in w for w in self.warns(spec(criteria=numeric))))

    def test_precise_wording_is_not_flagged(self):
        self.assertFalse(any("vague" in w for w in self.warns(spec())))

    def test_ids_are_case_insensitive(self):
        text = spec(criteria=AC.replace("AC1", "ac1"), tests=TEST.replace("AC1", "ac1"))
        self.assertEqual(self.errors(text), [])


class Traceability(Base):
    def test_every_criterion_needs_a_test(self):
        two = AC + "\n" + AC.replace("AC1", "AC2")
        self.assertError(spec(criteria=two), "AC2 has no test expectation")

    def test_a_test_for_a_missing_criterion(self):
        self.assertError(spec(tests=TEST + "\n" + TEST.replace("AC1", "AC7")), "AC7 has a test expectation but no such")

    def test_one_test_line_can_cover_several_criteria(self):
        two = AC + "\n" + AC.replace("AC1", "AC2")
        both = TEST.replace("AC1", "AC1, AC2")
        self.assertEqual(self.errors(spec(criteria=two, tests=both)), [])

    def test_fails_before_must_be_real(self):
        for why in ("n/a", "none", "short", ""):
            self.assertError(spec(tests=TEST.replace("the rejection path does not exist yet", why)), "fails-before")

    def test_malformed_test_line(self):
        self.assertError(spec(tests="- AC1 tests/test_a.py"), "not in test format")

    def test_manual_checks_warn(self):
        manual = "- AC1 -> manual: check the print dialog | fails-before: the layout overflows today"
        self.assertTrue(any("manual check" in w for w in self.warns(spec(tests=manual))))
        self.assertEqual(self.errors(spec(tests=manual)), [])

    def test_test_files_must_exist_only_when_asked(self):
        missing = TEST.replace("tests/test_a.py", "tests/test_missing.py")
        self.assertEqual(self.errors(spec(tests=missing)), [])
        self.assertError(spec(tests=missing), "does not exist yet", exist=True)
        self.assertEqual(self.errors(spec(), exist=True), [])

    def test_unsafe_test_paths(self):
        for ref, fragment in (("../x_test.py", "safe repo-relative"), ("/etc/passwd.py", "safe repo-relative")):
            self.assertError(spec(tests=TEST.replace("tests/test_a.py::test_bad_password", ref)), fragment, exist=True)

    def test_a_non_path_reference_is_not_checked(self):
        self.assertEqual(self.errors(spec(tests=TEST.replace("tests/test_a.py::test_bad_password", "the login smoke suite")), exist=True), [])

    def test_symlink_escape(self):
        outside = os.path.join(self.repo, "..", "outside-%d.py" % os.getpid())
        with open(outside, "w") as handle:
            handle.write("x")
        os.symlink(outside, os.path.join(self.repo, "tests", "link_test.py"))
        self.assertError(spec(tests=TEST.replace("tests/test_a.py", "tests/link_test.py")), "outside the repository", exist=True)


class Sections(Base):
    def test_required_sections_by_lane(self):
        self.assertError(spec(out=None), "requires a 'Out of scope' section")
        self.assertError(spec(constraints=None), "requires a 'Constraints' section")
        self.assertError(spec(plan=None), "requires a 'Plan' section")
        lite = "# s\n\n## Intent\nx y z\n\n## Acceptance criteria\n" + AC + "\n"
        self.assertError(lite, "requires a 'Test expectations' section", lane="Lite")

    def test_critical_needs_threat_and_rollout(self):
        errors = self.errors(spec(), lane="Critical")
        self.assertTrue(any("Threat considerations" in m for m in errors))
        self.assertTrue(any("Rollout constraints" in m for m in errors))
        extra = "## Threat considerations\n- abuse of old keys\n\n## Rollout constraints\n- keep both keys valid for ten minutes\n"
        self.assertEqual(self.errors(spec(extra=extra), lane="Critical"), [])

    def test_empty_section(self):
        self.assertError(spec(intent=""), "'Intent' is empty")

    def test_unknown_and_duplicate_sections_warn(self):
        self.assertTrue(any("unknown section" in w for w in self.warns(spec(extra="## Random\nx"))))
        self.assertTrue(any("appears twice" in w for w in self.warns(spec(extra="## Plan\nagain"))))

    def test_intent_kind_requirements(self):
        text = "# Intent\nLane: Critical\nStatus: draft\n\n## Intent\nx\n"
        errors = self.errors(text, kind="intent", lane="Critical")
        for label in ("Why", "Out of scope", "Success measures"):
            self.assertTrue(any("'%s'" % label in m for m in errors), label)

    def test_incident_sections_are_recognised(self):
        extra = "## Trigger\n- INC-9\n\n## Impact\nelevated errors\n\n## Mitigation\nrolled back\n\n## Follow-ups\n- audit\n"
        self.assertFalse(any("unknown section" in w for w in self.warns(spec(extra=extra))))

    def test_too_many_criteria(self):
        def many(n):
            return "\n".join("- AC%d: behavior number %d works here | pass: HTTP 200 and body %d" % (i, i, i) for i in range(1, n + 1))

        def tests(n):
            return "\n".join("- AC%d -> tests/test_a.py::t%d | fails-before: it does not exist yet today" % (i, i) for i in range(1, n + 1))

        self.assertFalse(any("cap of" in m for m in self.errors(spec(criteria=many(15), tests=tests(15)))))
        self.assertError(spec(criteria=many(16), tests=tests(16)), "exceeds the Standard cap of 15")
        lite = "# s\n\n## Intent\nx y z\n\n## Acceptance criteria\n%s\n\n## Test expectations\n%s\n"
        self.assertFalse(any("cap of" in m for m in self.errors(lite % (many(5), tests(5)), lane="Lite")))
        self.assertError(lite % (many(6), tests(6)), "exceeds the Lite cap of 5", lane="Lite")


class Approval(Base):
    def header(self, status="approved", approver="Priya Rao (2026-10-02)", lane_line="Lane: Standard", author="Dana Lee"):
        return "# Spec: x\n%s\nAuthor: %s\nStatus: %s\nApproved-by: %s\n" % (lane_line, author, status, approver)

    def test_status_is_required_and_validated(self):
        self.assertError(spec(header="# Spec: x\nLane: Standard\n"), "needs 'Status:")
        self.assertError(spec(header=self.header(status="maybe")), "must be 'draft' or 'approved'")

    def test_approved_needs_a_named_human_and_a_date(self):
        for approver in ("", "Priya Rao", "Priya Rao (yesterday)", "Priya Rao (2026-13-45)", "___ (2026-10-02)", "(2026-10-02)"):
            self.assertError(spec(header=self.header(approver=approver)), "needs 'Approved-by: Name (YYYY-MM-DD)'")

    def test_valid_approval_passes(self):
        self.assertEqual(self.errors(spec(header=self.header())), [])

    def test_draft_is_fine_until_approval_is_required(self):
        draft = spec(header=self.header(status="draft", approver=""))
        self.assertEqual(self.errors(draft), [])
        self.assertError(draft, "needs one human approval before build", approved=True)

    def test_self_approval_warns(self):
        self.assertTrue(any("also the author" in w for w in self.warns(spec(header=self.header(author="Priya Rao")))))

    def test_lite_needs_no_approval(self):
        text = "# s\n\n## Intent\nx y z\n\n## Acceptance criteria\n" + AC + "\n\n## Test expectations\n" + TEST + "\n"
        self.assertEqual(self.errors(text, lane="Lite", approved=True), [])

    def test_declaring_a_lower_lane_than_computed_warns(self):
        self.assertTrue(any("can only go up" in w for w in self.warns(spec(header=self.header(lane_line="Lane: Lite")), lane="Critical")))


class Safety(Base):
    def test_secrets_are_reported_and_never_echoed(self):
        secret = "ghp_" + "a" * 36
        findings, _ = self.run_check(spec(constraints="- token for the fixture is " + secret))
        self.assertTrue(any("GitHub token" in m for level, _, m in findings if level == "ERROR"))
        self.assertFalse(any(secret in m for _, _, m in findings))

    def test_a_secret_inside_a_comment_is_still_caught(self):
        self.assertError(spec(extra="<!-- password = correcthorsebatterystaple -->"), "possible secret")

    def test_hidden_unicode_is_an_error_but_a_bom_is_fine(self):
        self.assertError(spec(intent="Users can sign\u200b in"), "hidden Unicode")
        self.assertEqual(self.errors("\ufeff" + spec()), [])


class Cli(Base):
    def test_exit_codes_and_summary(self):
        code, out, _ = self.run_main(spec())
        self.assertEqual(code, 0)
        self.assertIn("spec (Standard lane): 1 criteria, 0 error(s), 0 warning(s)", out)
        code, out, _ = self.run_main(spec(plan=None))
        self.assertEqual(code, 1)
        self.assertIn("ERROR line", out)

    def test_strict_fails_on_warnings(self):
        text = spec(extra="## Random\nx")
        self.assertEqual(self.run_main(text)[0], 0)
        self.assertEqual(self.run_main(text, "--strict")[0], 1)

    def test_json_is_pure(self):
        code, out, _ = self.run_main(spec(), "--json")
        data = json.loads(out)
        self.assertEqual((code, data["criteria"], data["errors"], data["failed"]), (0, 1, 0, False))

    def test_flags_are_wired_through(self):
        draft = spec(header="# s\nLane: Standard\nStatus: draft\n")
        self.assertEqual(self.run_main(draft)[0], 0)
        self.assertEqual(self.run_main(draft, "--require-approved")[0], 1)
        missing = spec(tests=TEST.replace("tests/test_a.py", "tests/test_gone.py"))
        self.assertEqual(self.run_main(missing)[0], 0)
        self.assertEqual(self.run_main(missing, "--require-tests-exist")[0], 1)

    def test_kind_intent_flag(self):
        text = ("# i\nLane: Critical\nStatus: draft\n\n## Intent\nx y z\n\n## Why\nbecause\n\n## Out of scope\n- a\n\n"
                "## Success measures\n- b\n")
        self.assertEqual(self.run_main(text, "--kind", "intent", "--lane", "Critical")[0], 0)
        self.assertEqual(self.run_main(text, "--lane", "Critical")[0], 1)  # as a spec it is missing everything

    def test_usage_errors(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(cs.main(["/nonexistent/spec.md"]), 2)
        self.assertIn("cannot read spec", err.getvalue())
        code, _, err = self.run_main("x" * (cs.MAX_BYTES + 1))
        self.assertEqual(code, 2)

    def test_findings_are_ordered_by_line(self):
        _, out, _ = self.run_main(spec(criteria="- bad line\n" + AC, plan=None))
        numbers = [int(line.split("line ")[1].split(":")[0]) for line in out.splitlines() if line.startswith("ERROR")]
        self.assertEqual(numbers, sorted(numbers))


if __name__ == "__main__":
    unittest.main()
