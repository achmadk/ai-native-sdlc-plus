import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import evidence_check as ec  # noqa: E402

CONFIG = """\
version: 1
critical:
  - "auth/**"
standard:
  - "src/**"
lite:
  - "docs/**"
  - "notes/**"
"""

GOOD_LITE = """\
## Intent
Fix the typo in the install guide so the command is copy-pasteable.

## Trace
Used an agent to find the typo; rejected rewriting the whole paragraph, kept the change minimal.

Tests: none - documentation only, no behaviour change
"""

GOOD_STANDARD = """\
## Intent
Add retry to the sync client.

Spec: docs/spec.md

## Trace
Agent drafted the retry loop; I rejected exponential backoff without jitter and added jitter.

## Review notes
Check the retry cap against the intent and confirm idempotency of the sync call.
"""

GOOD_CRITICAL = GOOD_STANDARD + """
Intent link: docs/intent.md

## Threat note
Replayed requests could double-charge; we dedupe on idempotency key before retry.

## Rollout plan
Ship behind a flag to 5 percent, watch error rate for a day, roll back by disabling the flag.
"""


def run_main(argv, env=None, stdin=None):
    out, err = io.StringIO(), io.StringIO()
    old_env = dict(os.environ)
    if env:
        os.environ.update(env)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ec.main(argv)
    finally:
        os.environ.clear()
        os.environ.update(old_env)
    return code, out.getvalue(), err.getvalue()


class Repo(unittest.TestCase):
    """A tiny repo with a base commit; tests add a change commit on top."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.g("init", "-q", "-b", "main")
        self.write("docs/spec.md", "# Spec\nsomething real\n")
        self.write("docs/intent.md", "# Intent\nsomething real\n")
        self.write("auth/login.py", "x = 1\n")
        self.write("src/app.py", "x = 1\n")
        self.cfg = os.path.join(self.repo, "..", "lane-config-%d.yaml" % id(self))
        with open(self.cfg, "w") as handle:
            handle.write(CONFIG)
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "base")
        self.base = self.g("rev-parse", "HEAD").strip()

    def g(self, *args):
        proc = subprocess.run(["git", "-C", self.repo, "-c", "user.email=t@t", "-c", "user.name=t", *args],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return proc.stdout.decode()

    def write(self, rel, text):
        full = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as handle:
            handle.write(text)

    def change(self, **files):
        for rel, text in files.items():
            self.write(rel.replace("__", "/").replace("_dot_", "."), text)
        self.g("add", "-A")
        self.g("commit", "-q", "--allow-empty", "-m", "change")

    def ci(self, body, *extra, **kw):
        body_file = os.path.join(self.repo, "..", "body-%d.md" % id(self))
        with open(body_file, "w") as handle:
            handle.write(body)
        argv = ["--ci", "--config", self.cfg, "--repo-root", self.repo, "--base", self.base,
                "--head", "HEAD", "--pr-body-file", body_file] + list(extra)
        argv[argv.index("--base") + 1] = "--base=" + self.base
        del argv[argv.index("--base")]
        return run_main(argv, **kw)


class CiFlow(Repo):
    def test_lite_docs_change_with_real_evidence_passes(self):
        self.change(docs__guide_dot_md="fixed\n")
        code, out, _ = self.ci(GOOD_LITE)
        self.assertEqual(code, 0, out)
        self.assertIn("evidence ok for Lite", out)

    def test_empty_pr_description_fails_closed(self):
        # The shipped workflow used to fail EVERY pr; now it fails only when evidence is absent.
        self.change(docs__guide_dot_md="fixed\n")
        code, out, _ = self.ci("")
        self.assertEqual(code, 1)
        self.assertIn("FAIL: missing evidence for Lite: intent_block, trace_block", out)

    def test_standard_passes_with_spec_and_sections(self):
        self.change(src__app_dot_py="x = 2\n", tests__test_app_dot_py="assert True\n")
        code, out, _ = self.ci(GOOD_STANDARD)
        self.assertEqual(code, 0, out)
        self.assertIn("Standard", out)

    def test_critical_needs_everything(self):
        self.change(auth__login_dot_py="x = 2\n", tests__test_login_dot_py="assert True\n")
        code, out, _ = self.ci(GOOD_STANDARD)
        self.assertEqual(code, 1)
        for name in ("intent_link", "threat_note", "rollout_plan"):
            self.assertIn(name, out)
        code, out, _ = self.ci(GOOD_CRITICAL)
        self.assertEqual(code, 0, out)

    def test_mixed_docs_and_unmatched_code_is_not_lite(self):
        self.change(docs__a_dot_md="x\n", lib__pay_dot_py="x\n", tests__test_pay_dot_py="x\n")
        code, out, _ = self.ci(GOOD_LITE)
        self.assertEqual(code, 1)
        self.assertIn("evidence for Standard", out)

    def test_section_threshold_is_exactly_20_characters(self):
        self.change(docs__guide_dot_md="fixed\n")
        def body(trace):
            return "## Intent\n" + "i" * 25 + "\n\n## Trace\n" + trace + "\n\nTests: none - documentation only change\n"
        self.assertEqual(self.ci(body("t" * 19))[0], 1)
        self.assertEqual(self.ci(body("t" * 20))[0], 0)

    def test_key_lines_do_not_fill_an_empty_section(self):
        # Loophole found by the threshold test: a trailing "Tests: none - <reason>" line used to
        # count as content of whatever heading preceded it.
        self.change(auth__login_dot_py="x = 5\n")
        body = GOOD_CRITICAL.replace(
            "Ship behind a flag to 5 percent, watch error rate for a day, roll back by disabling the flag.", "")
        body += "\nTests: none - infra-only, validated by dry run plan\nSpec: docs/spec.md\n"
        code, out, _ = self.ci(body)
        self.assertEqual(code, 1)
        self.assertIn("rollout_plan", out)

    def test_lane_floor_flag_escalates_in_auto_mode(self):
        self.change(docs__guide_dot_md="fixed\n")
        code, out, _ = self.ci(GOOD_LITE, "--lane", "Critical")
        self.assertEqual(code, 1)
        self.assertIn("missing evidence for Critical", out)

    def test_lane_line_inside_code_fence_does_not_escalate(self):
        self.change(docs__guide_dot_md="fixed\n")
        code, out, _ = self.ci("```\nLane: Critical\n```\n" + GOOD_LITE)
        self.assertEqual(code, 0, out)

    def test_declared_lane_escalates_but_never_downgrades(self):
        self.change(docs__a_dot_md="x\n")
        code, out, _ = self.ci("Lane: Critical\n" + GOOD_LITE)
        self.assertEqual(code, 1)
        self.assertIn("missing evidence for Critical", out)
        self.change(auth__login_dot_py="x = 3\n", tests__test_login_dot_py="x\n")
        code, out, _ = self.ci("Lane: Lite\n" + GOOD_CRITICAL)
        self.assertEqual(code, 0, out)
        self.assertIn("ignored", out)

    def test_changing_the_gate_itself_is_critical(self):
        self.change(scripts__evidence_check_dot_py="# weakened\n")
        code, out, _ = self.ci(GOOD_LITE)
        self.assertEqual(code, 1)
        self.assertIn("Critical", out)

    def test_rename_out_of_critical_directory_is_still_critical(self):
        self.g("mv", "auth/login.py", "docs/login.py")
        self.g("commit", "-q", "-m", "mv")
        code, out, _ = self.ci(GOOD_LITE)
        self.assertEqual(code, 1)
        self.assertIn("Critical", out)

    def test_bad_base_is_tooling_error_not_a_pass(self):
        self.base = "deadbeef" * 5
        code, out, _ = self.ci(GOOD_LITE)
        self.assertEqual(code, 3)
        self.assertIn("tooling error", out)

    def test_unsafe_base_ref_rejected(self):
        self.base = "--output=/tmp/pwned"
        code, out, _ = self.ci(GOOD_LITE)
        self.assertEqual(code, 3)
        self.assertFalse(os.path.exists("/tmp/pwned"))

    def test_bad_config_fails_closed_in_ci(self):
        with open(self.cfg, "w") as handle:
            handle.write("version: 1\ncritcal:\n  - x\n")
        self.change(docs__a_dot_md="x\n")
        code, out, _ = self.ci(GOOD_LITE)
        self.assertEqual(code, 3)

    def test_local_mode_warns_and_never_blocks(self):
        self.change(docs__a_dot_md="x\n")
        argv = ["--config", self.cfg, "--repo-root", self.repo, "--base", self.base]
        code, out, _ = run_main(argv)
        self.assertEqual(code, 0)
        self.assertIn("WARNING: missing evidence for Lite", out)
        self.assertIn("(local, not blocking)", out)

    def test_event_payload_body(self):
        self.change(docs__a_dot_md="x\n")
        event = os.path.join(self.repo, "..", "event-%d.json" % id(self))
        with open(event, "w") as handle:
            json.dump({"pull_request": {"body": GOOD_LITE}}, handle)
        argv = ["--ci", "--config", self.cfg, "--repo-root", self.repo, "--base", self.base,
                "--event-path", event]
        self.assertEqual(run_main(argv)[0], 0)
        with open(event, "w") as handle:
            json.dump({"pull_request": {"body": None}}, handle)
        self.assertEqual(run_main(argv)[0], 1)

    def test_event_path_falls_back_to_env_in_ci(self):
        self.change(docs__a_dot_md="x\n")
        event = os.path.join(self.repo, "..", "event2-%d.json" % id(self))
        with open(event, "w") as handle:
            json.dump({"pull_request": {"body": GOOD_LITE}}, handle)
        argv = ["--ci", "--config", self.cfg, "--repo-root", self.repo, "--base", self.base]
        self.assertEqual(run_main(argv, env={"GITHUB_EVENT_PATH": event})[0], 0)

    def test_malformed_event_json_is_tooling_error(self):
        self.change(docs__a_dot_md="x\n")
        event = os.path.join(self.repo, "..", "event3-%d.json" % id(self))
        with open(event, "w") as handle:
            handle.write("{not json")
        argv = ["--ci", "--config", self.cfg, "--repo-root", self.repo, "--base", self.base, "--event-path", event]
        self.assertEqual(run_main(argv)[0], 3)

    def test_json_output(self):
        self.change(docs__a_dot_md="x\n")
        code, out, _ = self.ci(GOOD_LITE, "--json")
        data = json.loads(out)
        self.assertEqual((code, data["lane"], data["missing"]), (0, "Lite", []))

    def test_step_summary_written(self):
        self.change(docs__a_dot_md="x\n")
        summary = os.path.join(self.repo, "..", "summary-%d.md" % id(self))
        if os.path.exists(summary):
            os.remove(summary)
        self.ci(GOOD_LITE, env={"GITHUB_STEP_SUMMARY": summary})
        with open(summary) as handle:
            self.assertIn("sdlc-gate: Lite lane", handle.read())


class SpecLinks(Repo):
    def standard(self, spec_line):
        return GOOD_STANDARD.replace("Spec: docs/spec.md", spec_line)

    def run_standard(self, spec_line):
        self.change(src__app_dot_py="x = 9\n", tests__test_app_dot_py="x\n")
        return self.ci(self.standard(spec_line))

    def test_missing_file(self):
        code, out, _ = self.run_standard("Spec: docs/nope.md")
        self.assertEqual(code, 1)
        self.assertIn("no such file", out)

    def test_traversal_and_absolute(self):
        for line in ("Spec: ../secret.md", "Spec: /etc/passwd", "Spec: docs/../../x"):
            self.assertEqual(self.run_standard(line)[0], 1, line)

    def test_symlink_escape(self):
        outside = os.path.join(self.repo, "..", "outside-%d.md" % id(self))
        with open(outside, "w") as handle:
            handle.write("secret\n")
        os.symlink(outside, os.path.join(self.repo, "docs", "link.md"))
        code, out, _ = self.run_standard("Spec: docs/link.md")
        self.assertEqual(code, 1)
        self.assertIn("outside the repository", out)

    def test_empty_file(self):
        self.write("docs/empty.md", "")
        self.assertEqual(self.run_standard("Spec: docs/empty.md")[0], 1)

    def test_url_accepted_but_flagged_unverified(self):
        code, out, _ = self.run_standard("Spec: https://example.com/spec")
        self.assertEqual(code, 0, out)
        self.assertIn("not verified", out)

    def test_markdown_link_bold_and_bullet_forms(self):
        for line in ("Spec: [the spec](docs/spec.md)", "**Spec:** docs/spec.md", "- Spec: `docs/spec.md`",
                     "Spec: docs/spec.md#section"):
            self.assertEqual(self.run_standard(line)[0], 0, line)

    def test_spec_inside_code_fence_or_comment_does_not_count(self):
        body = GOOD_STANDARD.replace("Spec: docs/spec.md", "```\nSpec: docs/spec.md\n```\n<!-- Spec: docs/spec.md -->")
        self.change(src__app_dot_py="x = 9\n", tests__test_app_dot_py="x\n")
        code, out, _ = self.ci(body)
        self.assertEqual(code, 1)
        self.assertIn("spec_link", out)


class Sections(unittest.TestCase):
    def chars(self, body, alias="trace"):
        return ec.find_section(ec.parse_sections(body), (alias,))

    def test_boundary_is_20_meaningful_characters(self):
        self.assertEqual(self.chars("## Trace\n" + "a" * 19), 19)
        self.assertEqual(self.chars("## Trace\n" + "a" * 20), 20)

    def test_template_filler_does_not_count(self):
        for filler in ("", "TBD", "TODO", "N/A", "none", "...", "- ", "<!-- describe what you did -->",
                       "{{ trace }}", "<fill in the trace>", "- [ ]"):
            self.assertLess(self.chars("## Trace\n" + filler) or 0, ec.MIN_SECTION_CHARS, repr(filler))

    def test_real_text_containing_todo_still_counts(self):
        text = "Rejected polling; TODO follow-up ticket for the websocket variant is filed."
        self.assertGreaterEqual(self.chars("## Trace\n" + text), ec.MIN_SECTION_CHARS)

    def test_heading_in_code_fence_ignored(self):
        body = "```\n## Trace\nthis is a code comment, not a heading, long enough\n```\n"
        self.assertIsNone(self.chars(body))

    def test_missing_section_is_none_and_heading_suffix_tolerated(self):
        self.assertIsNone(self.chars("## Intent\nhello there friend of mine\n"))
        self.assertGreaterEqual(self.chars("## Trace (AI-assisted)\n" + "b" * 25), 25)

    def test_subsections_belong_to_parent(self):
        body = "## Review\n### Risks\n" + "c" * 30 + "\n## Trace\nx\n"
        self.assertGreaterEqual(self.chars(body, "review"), 30)

    def test_sub_heading_titles_are_structure_not_content(self):
        # Found by auditing a real template: "### Change / ### Why / ..." made an EMPTY Trace look 100+ characters long.
        body = "## Trace\n### Change\n### Why\n### Alternatives rejected\n### Risk accepted\n"
        self.assertEqual(self.chars(body) or 0, 0)

    def test_sub_section_content_still_counts_for_the_parent(self):
        body = "## Trace\n### Why\n" + "w" * 30 + "\n### Risk accepted\n"
        self.assertGreaterEqual(self.chars(body), 30)

    def test_sub_headings_are_still_findable_as_their_own_sections(self):
        body = "## Trace\nsome text that is long enough here\n### Threat note\n" + "t" * 25 + "\n"
        self.assertGreaterEqual(ec.find_section(ec.parse_sections(body), ("threat note",)), 25)

    def test_next_same_level_heading_ends_section(self):
        body = "## Trace\nshort\n## Review notes\n" + "d" * 40
        self.assertLess(self.chars(body), 20)

    def test_case_and_punctuation_insensitive(self):
        self.assertGreaterEqual(self.chars("##  REVIEW-NOTES:\n" + "e" * 25, "review notes"), 25)


class TestEvidence(Repo):
    def test_changed_test_path_counts(self):
        self.change(src__app_dot_py="x = 2\n", tests__test_app_dot_py="x\n")
        body = GOOD_STANDARD
        code, out, _ = self.ci(body)
        self.assertEqual(code, 0, out)

    def test_no_tests_and_no_waiver_fails(self):
        self.change(src__app_dot_py="x = 2\n")
        code, out, _ = self.ci(GOOD_STANDARD)
        self.assertEqual(code, 1)
        self.assertIn("test_changes", out)

    def test_waiver_needs_a_real_reason(self):
        self.change(src__app_dot_py="x = 2\n")
        for waiver in ("Tests: none", "Tests: none - ok", "Tests: n/a"):
            self.assertEqual(self.ci(GOOD_STANDARD + "\n" + waiver)[0], 1, waiver)
        code, out, _ = self.ci(GOOD_STANDARD + "\nTests: none - pure refactor, covered by existing suite")
        self.assertEqual(code, 0, out)
        self.assertIn("waived", out)

    def test_ordinary_tests_line_is_not_a_waiver(self):
        self.change(src__app_dot_py="x = 2\n")
        code, _, _ = self.ci(GOOD_STANDARD + "\nTests: added a lot of coverage elsewhere honestly")
        self.assertEqual(code, 1)

    def test_docs_only_change_needs_no_tests(self):
        self.change(docs__guide_dot_md="x\n")
        body = GOOD_LITE.replace("Tests: none - documentation only, no behaviour change\n", "")
        code, out, _ = self.ci(body)
        self.assertEqual(code, 0, out)
        self.assertIn("only non-executable paths", out)

    def test_non_executable_exemption_does_not_apply_when_code_changes(self):
        self.change(docs__guide_dot_md="x\n", notes__n_dot_py="x\n")
        body = GOOD_LITE.replace("Tests: none - documentation only, no behaviour change\n", "")
        code, out, _ = self.ci(body)
        self.assertEqual(code, 1)
        self.assertIn("test_changes", out)

    def test_critical_gets_no_automatic_test_exemption(self):
        # Escalated to Critical by declaration: docs-only is not enough without tests or a waiver.
        self.change(docs__guide_dot_md="x\n")
        body = "Lane: Critical\n" + GOOD_CRITICAL
        code, out, _ = self.ci(body)
        self.assertEqual(code, 1)
        self.assertIn("test_changes", out)

    def test_critical_waiver_is_flagged(self):
        self.change(auth__login_dot_py="x = 4\n")
        code, out, _ = self.ci(GOOD_CRITICAL + "\nTests: none - infra-only, validated by dry run plan")
        self.assertEqual(code, 0, out)
        self.assertIn("WAIVER on a Critical change", out)
        self.assertIn("a human reviewer must confirm", out)


class Safety(Repo):
    def test_attacker_text_cannot_inject_workflow_commands(self):
        self.change(src__app_dot_py="x = 2\n")
        body = GOOD_STANDARD + "\nTests: none - ::error::pwned ::set-output name=x::y and more words\n"
        code, out, _ = self.ci(body, env={"GITHUB_ACTIONS": "true"})
        for line in out.splitlines():
            if line.startswith("::"):
                self.assertTrue(line.startswith("::error title=sdlc-gate::"), line)
        self.assertNotIn("::set-output", out)
        self.assertNotIn("pwned ::", out)

    def test_filename_cannot_inject_workflow_commands(self):
        self.change(**{"docs__::error::x_dot_md": "x\n"})
        code, out, _ = self.ci("", env={"GITHUB_ACTIONS": "true"})
        self.assertNotIn("::error::x", out)

    def test_oversized_body_is_a_tooling_error(self):
        self.change(docs__a_dot_md="x\n")
        code, out, _ = self.ci("a" * (ec.MAX_BODY_BYTES + 10))
        self.assertEqual(code, 3)

    def test_ci_rejects_manual_attestation(self):
        self.change(docs__a_dot_md="x\n")
        code, _, err = self.ci(GOOD_LITE, "--present", "intent_block", "test_changes", "trace_block")
        self.assertEqual(code, 2)
        self.assertIn("rejected", err)

    def test_ci_requires_a_computed_lane(self):
        code, _, err = run_main(["--ci", "--lane", "Lite"])
        self.assertEqual(code, 2)


class DiffOnly(Repo):
    """--diff-only is for local hooks: it checks only what the diff proves and says so."""

    def diff(self, *extra, **kw):
        argv = ["--diff-only", "--config", self.cfg, "--repo-root", self.repo, "--base=" + self.base,
                "--head", "HEAD"] + list(extra)
        return run_main(argv, **kw)

    def test_test_change_passes_and_does_not_claim_full_evidence(self):
        self.change(src__app_dot_py="x = 2\n", tests__test_app_dot_py="x\n")
        code, out, _ = self.diff()
        self.assertEqual(code, 0)
        self.assertIn("diff checks ok for Standard (PR description items are checked in CI)", out)
        self.assertNotIn("evidence ok", out)
        self.assertIn("must carry: spec_link, trace_block, review_notes", out)

    def test_missing_tests_warn_but_never_block(self):
        self.change(src__app_dot_py="x = 2\n")
        code, out, _ = self.diff()
        self.assertEqual(code, 0)
        self.assertIn("WARNING: missing evidence for Standard: test_changes (local, not blocking)", out)
        self.assertIn("if that is intended, add 'Tests: none - <reason>' to the PR description", out)

    def test_does_not_read_the_pr_description(self):
        self.change(src__app_dot_py="x = 2\n", tests__test_app_dot_py="x\n")
        code, out, _ = self.diff("--pr-body-file", "/nonexistent/body.md")
        self.assertEqual(code, 0)
        self.assertNotIn("tooling error", out)

    def test_docs_only_change_needs_no_tests(self):
        self.change(docs__guide_dot_md="x\n")
        code, out, _ = self.diff()
        self.assertIn("diff checks ok for Lite", out)

    def test_owed_list_follows_the_lane(self):
        self.change(auth__login_dot_py="x = 2\n", tests__test_login_dot_py="x\n")
        _, out, _ = self.diff()
        self.assertIn("must carry: intent_link, spec_link, threat_note, trace_block, review_notes, rollout_plan", out)

    def test_lane_floor_applies(self):
        self.change(docs__guide_dot_md="x\n")
        _, out, _ = self.diff("--lane", "Critical")
        self.assertIn("lane Critical", out)

    def test_rejected_with_ci_and_needs_a_diff(self):
        self.change(docs__guide_dot_md="x\n")
        code, _, err = self.diff("--ci")
        self.assertEqual(code, 2)
        self.assertIn("rejected with --ci", err)
        code, _, err = run_main(["--diff-only", "--config", self.cfg])
        self.assertEqual(code, 2)
        self.assertIn("needs --base", err)

    def test_json_is_pure(self):
        self.change(src__app_dot_py="x = 2\n")
        code, out, _ = self.diff("--json")
        data = json.loads(out)
        self.assertEqual((code, data["lane"], data["missing"]), (0, "Standard", ["test_changes"]))

    def test_tooling_errors_are_warnings_locally(self):
        self.change(docs__guide_dot_md="x\n")
        with open(self.cfg, "w") as handle:
            handle.write("version: 1\ncritcal:\n  - x\n")
        code, out, _ = self.diff()
        self.assertEqual(code, 0)
        self.assertIn("WARNING: tooling error", out)


class PullRequestTemplate(unittest.TestCase):
    """The shipped template and the gate must agree, or every PR fails for a silly reason."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".github", "pull_request_template.md")
        with open(path) as handle:
            cls.template = handle.read()

    def test_every_evidence_section_has_a_matching_heading(self):
        titles = {title for title, _ in ec.parse_sections(self.template)}
        for name, aliases in ec.SECTION_ALIASES.items():
            self.assertTrue(titles & {ec.norm(a) for a in aliases}, name)

    def test_link_keys_appear_in_template(self):
        for name, keys in ec.LINK_KEYS.items():
            self.assertTrue(any(k.lower() + ":" in self.template.lower() for k in keys), name)

    def test_unfilled_template_never_passes(self):
        for lane in ec.REQUIRED:
            for name, aliases in ec.SECTION_ALIASES.items():
                chars = ec.find_section(ec.parse_sections(self.template), aliases)
                self.assertLess(chars or 0, ec.MIN_SECTION_CHARS, "%s/%s" % (lane, name))
        for keys in ec.LINK_KEYS.values():
            self.assertIsNone(ec.find_key_value(self.template, keys))  # value lives only in comments


class LegacyManualMode(unittest.TestCase):
    def test_complete_attestation_passes(self):
        code, out, _ = run_main(["--lane", "Standard", "--present", "spec_link", "test_changes",
                                 "trace_block", "review_notes"])
        self.assertEqual(code, 0)
        self.assertIn("evidence ok for Standard", out)

    def test_incomplete_attestation_warns_locally(self):
        code, out, _ = run_main(["--lane", "Standard", "--present", "spec_link", "test_changes"])
        self.assertEqual(code, 0)
        self.assertIn("WARNING: missing evidence for Standard: trace_block, review_notes (local, not blocking)", out)

    def test_check_helper_backward_compatible(self):
        self.assertEqual(ec.check("Lite", {"intent_block", "test_changes"}), ["trace_block"])
        self.assertEqual(ec.check("Nonsense", set()), ec.REQUIRED["Standard"])

    def test_unknown_lane_rejected(self):
        with self.assertRaises(SystemExit):
            run_main(["--lane", "Nonsense"])


if __name__ == "__main__":
    unittest.main()
