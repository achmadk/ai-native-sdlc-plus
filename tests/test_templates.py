"""Consistency tests across the whole toolkit: do the shipped templates actually work with the gate,
does every file a skill mentions exist, and are the shared secret patterns identical everywhere?"""

import glob
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for sub in ("scripts", "skills/spec-first/scripts", "skills/context-pack/scripts", "skills/verify-and-evals/scripts"):
    sys.path.insert(0, os.path.join(ROOT, sub))
import check_brief  # noqa: E402
import check_spec  # noqa: E402
import evidence_check as ec  # noqa: E402
import lane  # noqa: E402
import redgreen  # noqa: E402

FILLER = "a real sentence with enough characters to count as content here"
EXPECTED_SKILLS = {"ai-readiness-and-metrics", "ai-sdlc", "autonomy-policy", "context-pack", "decision-trace",
                   "learning-mode", "review-by-intent", "ship-and-observe", "spec-first", "verify-and-evals"}

# template path -> the gate evidence its heading must satisfy
GATE_TEMPLATES = {
    "skills/decision-trace/assets/trace-block.md": "trace_block",
    "skills/review-by-intent/assets/review-notes-template.md": "review_notes",
    "skills/ship-and-observe/assets/rollout-plan-template.md": "rollout_plan",
    "skills/spec-first/assets/threat-note-template.md": "threat_note",
    ".github/pull_request_template.md": None,
}


def slurp(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
        return handle.read()


def fill(text):
    return re.sub(r"<!--.*?-->", FILLER, text, flags=re.S)


class GateTemplates(unittest.TestCase):
    def sections(self, rel):
        return ec.parse_sections(slurp(rel))

    def test_each_template_heading_is_recognised_by_the_gate(self):
        for rel, name in GATE_TEMPLATES.items():
            if name is None:
                continue
            chars = ec.find_section(self.sections(rel), ec.SECTION_ALIASES[name])
            self.assertIsNotNone(chars, "%s: the gate does not recognise its heading for %s" % (rel, name))

    def test_unfilled_templates_never_satisfy_the_gate(self):
        # Found by auditing a real template: boilerplate and sub-heading titles made an EMPTY trace look filled.
        for rel, name in GATE_TEMPLATES.items():
            if name is None:
                continue
            chars = ec.find_section(self.sections(rel), ec.SECTION_ALIASES[name])
            self.assertEqual(chars, 0, "%s has %s characters of content before anyone fills it in" % (rel, chars))

    def test_filled_templates_do_satisfy_the_gate(self):
        for rel, name in GATE_TEMPLATES.items():
            if name is None:
                continue
            chars = ec.find_section(ec.parse_sections(fill(slurp(rel))), ec.SECTION_ALIASES[name])
            self.assertGreaterEqual(chars, ec.MIN_SECTION_CHARS, rel)

    def test_trace_block_has_the_documented_fields(self):
        titles = {title for title, _ in self.sections("skills/decision-trace/assets/trace-block.md")}
        for field in ("change", "why", "alternativesrejected", "testevidence", "riskaccepted", "provenance"):
            self.assertIn(field, titles)

    def test_trace_block_does_not_swallow_the_critical_sections(self):
        # Critical needs Threat note and Rollout plan as their OWN sections; the old "Threat / rollout" field could never match.
        titles = {title for title, _ in self.sections("skills/decision-trace/assets/trace-block.md")}
        self.assertNotIn("threatrollout", titles)


class EndToEnd(unittest.TestCase):
    """A PR assembled from the shipped templates must pass the gate, lane by lane."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        for rel in ("docs/spec.md", "docs/intent.md"):
            os.makedirs(os.path.join(self.repo, "docs"), exist_ok=True)
            with open(os.path.join(self.repo, rel), "w") as handle:
                handle.write("# real document\n")
        with open(os.path.join(ROOT, "scripts/lane-config.yaml")) as handle:
            self.rules = lane.parse_config(handle.read())

    def body(self, *templates, **extra):
        parts = ["## Intent\n" + FILLER + "\n"]
        if extra.get("spec"):
            parts.append("Spec: docs/spec.md\n")
        if extra.get("intent_link"):
            parts.append("Intent link: docs/intent.md\n")
        parts += [fill(slurp(t)) for t in templates]
        return "\n".join(parts)

    def missing(self, body, paths, lane_name):
        found = ec.detect(body, paths, self.repo, self.rules, lane_name)
        return [name for name in ec.REQUIRED[lane_name] if not found[name][0]]

    def test_lite_pr_from_templates(self):
        body = self.body("skills/decision-trace/assets/trace-block.md")
        self.assertEqual(self.missing(body, ["docs/a.md", "tests/test_x.py"], "Lite"), [])

    def test_standard_pr_from_templates(self):
        body = self.body("skills/decision-trace/assets/trace-block.md",
                         "skills/review-by-intent/assets/review-notes-template.md", spec=True)
        self.assertEqual(self.missing(body, ["src/app.py", "tests/test_app.py"], "Standard"), [])

    def test_critical_pr_from_templates(self):
        body = self.body("skills/decision-trace/assets/trace-block.md",
                         "skills/review-by-intent/assets/review-notes-template.md",
                         "skills/spec-first/assets/threat-note-template.md",
                         "skills/ship-and-observe/assets/rollout-plan-template.md", spec=True, intent_link=True)
        self.assertEqual(self.missing(body, ["auth/login.py", "tests/test_login.py"], "Critical"), [])

    def test_unfilled_templates_pasted_into_a_critical_pr_fail_every_section(self):
        templates = ("skills/decision-trace/assets/trace-block.md", "skills/review-by-intent/assets/review-notes-template.md",
                     "skills/spec-first/assets/threat-note-template.md", "skills/ship-and-observe/assets/rollout-plan-template.md")
        body = "\n".join(slurp(t) for t in templates)
        missing = self.missing(body, ["auth/login.py", "tests/test_login.py"], "Critical")
        for name in ("trace_block", "review_notes", "threat_note", "rollout_plan"):
            self.assertIn(name, missing)


class SpecTemplates(unittest.TestCase):
    def check(self, rel, kind, lane_name):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(slurp(rel))
        self.addCleanup(os.remove, handle.name)
        findings, _ = check_spec.check(slurp(rel), kind, lane_name, ROOT, False, False)
        return [m for level, _, m in findings if level == "ERROR"]

    def test_unfilled_spec_templates_are_rejected(self):
        for rel, kind, lane_name in (("skills/spec-first/assets/intent-template.md", "spec", "Standard"),
                                     ("skills/spec-first/assets/spec-critical-template.md", "spec", "Critical"),
                                     ("skills/spec-first/assets/intent-critical-template.md", "intent", "Critical"),
                                     ("skills/ship-and-observe/assets/incident-intent-template.md", "spec", "Standard")):
            errors = self.check(rel, kind, lane_name)
            self.assertTrue(errors, "%s passes while completely empty" % rel)
            self.assertTrue(any("empty" in m or "no acceptance criteria" in m for m in errors), rel)

    def test_template_guidance_comments_are_not_parsed_as_content(self):
        # The comments contain example criterion lines; they must not be validated or counted.
        errors = self.check("skills/spec-first/assets/intent-template.md", "spec", "Standard")
        self.assertFalse(any("format" in m for m in errors), errors)

    def test_the_worked_example_in_the_references_passes(self):
        block = re.search(r"```spec\n(.*?)```", slurp("skills/spec-first/references/examples.md"), re.S).group(1)
        findings, count = check_spec.check(block, "spec", "Standard", ROOT, True, False)
        self.assertEqual([f for f in findings if f[0] in ("ERROR", "WARN")], [])
        self.assertEqual(count, 2)

    def test_a_filled_critical_pair_passes(self):
        intent = ("# Intent statement: x\nLane: Critical\nAuthor: A B\nStatus: approved\nApproved-by: C D (2026-10-01)\n\n"
                  "## Intent\nUsers can rotate API keys.\n\n## Why\nKeys cannot be rotated today.\n\n"
                  "## Out of scope\n- Automatic rotation\n\n## Success measures\n- 100% of keys rotatable within 30 days\n")
        self.assertEqual(check_spec.check(intent, "intent", "Critical", ROOT, True, False)[0], [])
        spec = ("# Spec: x\nLane: Critical\nAuthor: A B\nStatus: approved\nApproved-by: C D (2026-10-01)\n\n"
                "## Intent\nUsers can rotate API keys.\n\n## Out of scope\n- Automatic rotation\n\n"
                "## Acceptance criteria\n- AC1: a rotated key stops working | pass: old key returns HTTP 401 within 60 s\n\n"
                "## Constraints\n- No downtime\n\n## Threat considerations\n- Old keys stay valid: covered by AC1\n\n"
                "## Rollout constraints\n- Both keys valid during a 10 minute overlap\n\n"
                "## Test expectations\n- AC1 -> tests/test_keys.py::test_old_key_rejected | fails-before: rotation does not exist yet\n\n"
                "## Plan\nAdd the rotate endpoint behind a flag.\n")
        self.assertEqual(check_spec.check(spec, "spec", "Critical", ROOT, True, False)[0], [])


class References(unittest.TestCase):
    """Every assets/, references/ or scripts/ path a skill document mentions must exist."""

    PATH = re.compile(r"(?<![\w/.-])((?:assets|references|scripts)/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)")

    def documents(self):
        for skill in sorted(glob.glob(os.path.join(ROOT, "skills", "*"))):
            for path in glob.glob(os.path.join(skill, "**", "*.md"), recursive=True):
                yield skill, path

    def test_every_mentioned_file_exists(self):
        problems = []
        for skill, path in self.documents():
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            for ref in set(self.PATH.findall(text)):
                ref = ref.rstrip(".")
                if not (os.path.exists(os.path.join(skill, ref)) or os.path.exists(os.path.join(ROOT, ref))):
                    problems.append("%s mentions %s" % (os.path.relpath(path, ROOT), ref))
        self.assertEqual(problems, [])

    def test_the_references_check_actually_catches_a_missing_file(self):
        self.assertEqual(self.PATH.findall("see `references/nope.md` and scripts/x.py."), ["references/nope.md", "scripts/x.py."])


class SkillHygiene(unittest.TestCase):
    def skills(self):
        return sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))

    def test_the_expected_skills_are_all_present(self):
        self.assertEqual({os.path.basename(os.path.dirname(p)) for p in self.skills()}, EXPECTED_SKILLS)

    def test_frontmatter_is_valid_and_matches_the_directory(self):
        for path in self.skills():
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            match = re.match(r'---\nname: (\S+)\ndescription: "(.*)"\n---\n', text, re.S)
            self.assertTrue(match, path)
            self.assertEqual(match.group(1), os.path.basename(os.path.dirname(path)), path)
            self.assertLess(len(match.group(2)), 1024, path)
            self.assertNotIn('"', match.group(2), path)
            self.assertIn("Triggers:", match.group(2), "%s: description should list trigger phrases" % path)

    def test_skill_files_stay_small_so_the_footprint_stays_small(self):
        for path in self.skills():
            with open(path, encoding="utf-8") as handle:
                self.assertLessEqual(handle.read().count("\n"), 120, path)

    def test_survey_figures_are_always_tagged_as_report_stated(self):
        for path in self.skills():
            with open(path, encoding="utf-8") as handle:
                for number, line in enumerate(handle, 1):
                    if re.search(r"\b\d{2}%", line) and "report" not in line.lower() and "heuristic" not in line.lower() \
                            and "evidence" not in line.lower() and "share" not in line.lower():
                        self.fail("%s:%d states a percentage without saying where it comes from: %s" % (path, number, line.strip()[:80]))


class LearningMode(unittest.TestCase):
    """learning-mode must stay consistent with review-by-intent and with the metrics guardrails."""

    def test_the_review_notes_template_has_the_field_learning_mode_feeds(self):
        self.assertIn("### Explain-back", slurp("skills/review-by-intent/assets/review-notes-template.md"))
        note = slurp("skills/learning-mode/assets/understanding-note-template.md")
        self.assertIn("### Explain-back", note)
        self.assertIn("## Review notes", note)

    def test_the_two_skills_point_at_each_other(self):
        self.assertIn("`learning-mode`", slurp("skills/review-by-intent/SKILL.md"))
        self.assertIn("`review-by-intent`", slurp("skills/learning-mode/SKILL.md"))
        self.assertIn("`learning-mode`", slurp("skills/ai-sdlc/SKILL.md"))

    def test_the_non_assessment_and_opt_out_rules_cannot_be_edited_away(self):
        text = slurp("skills/learning-mode/SKILL.md")
        self.assertIn("not a performance evaluation", text)
        self.assertIn("never report a learner's answers", text)
        self.assertIn('"Just do it"', text)
        self.assertIn("never turn them into a metric", text)

    def test_the_hint_ladder_has_four_levels_and_ends_in_the_answer(self):
        text = slurp("skills/learning-mode/SKILL.md")
        for level in ("Level 1", "Level 2", "Level 3", "Level 4"):
            self.assertIn(level, text)
        self.assertIn("Never withhold level 4 for good", text)

    def test_the_question_bank_covers_ai_specific_checks(self):
        bank = slurp("skills/learning-mode/references/question-bank.md")
        for heading in ("## Predict", "## Break it", "## Test it", "## Evaluate the AI", "## Security and operations"):
            self.assertIn(heading, bank)

    def test_the_learner_owned_note_is_not_something_the_gate_parses(self):
        # The note is private. If its headings ever matched a gate alias it would invite pasting it into the PR whole.
        titles = {title for title, _ in ec.parse_sections(slurp("skills/learning-mode/assets/understanding-note-template.md"))}
        aliases = {ec.norm(a) for names in ec.SECTION_ALIASES.values() for a in names}
        self.assertEqual(titles & aliases - {"review"}, set())


class Overview(unittest.TestCase):
    def test_the_overview_lists_every_skill_and_only_real_ones(self):
        text = slurp("docs/OVERVIEW.md")
        listed = set(re.findall(r"^\| [A-Za-z]+ \| `([a-z-]+)` \|", text, re.M))
        self.assertEqual(listed, EXPECTED_SKILLS)

    def test_headings_the_overview_names_are_the_ones_the_gate_reads(self):
        text = slurp("docs/OVERVIEW.md")
        for name, aliases in (("intent_block", "## Intent"), ("trace_block", "## Trace"), ("review_notes", "## Review notes"),
                              ("threat_note", "## Threat note"), ("rollout_plan", "## Rollout plan")):
            self.assertIn(aliases, text)
            self.assertIn(ec.norm(aliases.lstrip("# ")), {ec.norm(a) for a in ec.SECTION_ALIASES[name]})


class SharedPatterns(unittest.TestCase):
    def test_secret_patterns_are_identical_in_every_script_that_carries_a_copy(self):
        reference = [(label, p.pattern) for label, p in check_brief.SECRETS]
        self.assertEqual([(label, p.pattern) for label, p in check_spec.SECRETS], reference)
        self.assertEqual([(label, p.pattern) for label, p in redgreen.SECRETS], reference)


if __name__ == "__main__":
    unittest.main()
