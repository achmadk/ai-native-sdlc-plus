"""Contract tests for OpenSpec and Spec Kit specification interoperability.

Verifies that the canonical spec checker (skills/spec-first/scripts/check_spec.py)
and front door accept supported upstream change/feature folders as specification inputs,
preserve native source identities and test mappings, and retain full native file compatibility.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

if __package__:
    from . import support
else:
    import support

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SPEC_FIRST_DIR = os.path.join(ROOT, "skills", "spec-first", "scripts")
if SPEC_FIRST_DIR not in sys.path:
    sys.path.insert(0, SPEC_FIRST_DIR)
import check_spec as cs  # noqa: E402
try:
    import spec_inputs  # noqa: F401, E402
except ImportError:
    spec_inputs = None

FIXTURES_DIR = os.path.join(ROOT, "tests", "fixtures", "interop")


class SpecInteropContract(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.mkdtemp()
        self.addCleanup(support.remove_tree, self.workspace)
        self.repo = os.path.join(self.workspace, "repo")
        self._bundle_idx = 0
        os.makedirs(os.path.join(self.repo, "tests"))
        # Create dummy test files referenced by fixtures
        for tname in ("test_widget.py", "test_auth.py", "test_profile.py", "test_payment.py", "test_ops.py"):
            with open(os.path.join(self.repo, "tests", tname), "w", encoding="utf-8") as handle:
                handle.write("# dummy test file for spec verification\n")

    def run_check_main(self, target_path, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cs.main([target_path, "--repo-root", self.repo] + list(args))
        return code, out.getvalue(), err.getvalue()

    def make_bundle(self, files_dict):
        self._bundle_idx += 1
        bdir = os.path.join(self.workspace, "bundle_%d" % self._bundle_idx)
        os.makedirs(bdir, exist_ok=True)
        for rel, content in files_dict.items():
            full = os.path.join(bdir, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            if isinstance(content, bytes):
                with open(full, "wb") as h:
                    h.write(content)
            else:
                with open(full, "w", encoding="utf-8") as h:
                    h.write(content)
        return bdir

    def test_native_file_input_still_passes(self):
        native_spec = os.path.join(self.repo, "spec.md")
        content = (
            "# Spec: Native Feature\n"
            "Lane: Standard\n"
            "Status: approved\n"
            "Approved-by: Dana Lee (2026-11-10)\n\n"
            "## Intent\nStandard feature intent.\n\n"
            "## Out of scope\n- None\n\n"
            "## Acceptance criteria\n"
            "- AC1: widget created | pass: HTTP 201 created\n\n"
            "## Constraints\n- Standard limits\n\n"
            "## Test expectations\n"
            "- AC1 -> tests/test_widget.py::test_create | fails-before: endpoint does not exist yet\n\n"
            "## Assumptions and open questions\n- None\n\n"
            "## Plan\nImplement widget endpoint.\n"
        )
        with open(native_spec, "w", encoding="utf-8") as handle:
            handle.write(content)
        code, stdout, stderr = self.run_check_main(native_spec, "--lane", "Standard")
        self.assertEqual(code, 0, "Native file check failed: %s %s" % (stdout, stderr))
        self.assertIn("1 criteria, 0 error(s)", stdout)

    def test_openspec_standard_fixture_passes(self):
        fixture_dir = os.path.join(FIXTURES_DIR, "openspec_standard")
        code, stdout, stderr = self.run_check_main(fixture_dir, "--lane", "Standard", "--json")
        self.assertEqual(code, 0, "OpenSpec standard bundle rejected: %s %s" % (stdout, stderr))
        data = json.loads(stdout)
        self.assertEqual(data.get("errors"), 0)
        self.assertEqual(data.get("criteria"), 3)
        self.assertFalse(data.get("failed"))

    def test_speckit_standard_fixture_passes(self):
        fixture_dir = os.path.join(FIXTURES_DIR, "speckit_standard")
        code, stdout, stderr = self.run_check_main(fixture_dir, "--lane", "Standard", "--json")
        self.assertEqual(code, 0, "Spec Kit standard bundle rejected: %s %s" % (stdout, stderr))
        data = json.loads(stdout)
        self.assertEqual(data.get("errors"), 0)
        self.assertEqual(data.get("criteria"), 2)
        self.assertFalse(data.get("failed"))

    def test_openspec_critical_fixture_passes_with_risk_artifacts(self):
        fixture_dir = os.path.join(FIXTURES_DIR, "openspec_critical")
        code, stdout, stderr = self.run_check_main(
            fixture_dir, "--lane", "Critical", "--require-approved", "--json")
        self.assertEqual(code, 0, "OpenSpec critical bundle rejected: %s %s" % (stdout, stderr))
        data = json.loads(stdout)
        self.assertEqual(data.get("errors"), 0)
        self.assertEqual(data.get("criteria"), 2)

    def test_speckit_critical_fixture_passes_with_risk_artifacts(self):
        fixture_dir = os.path.join(FIXTURES_DIR, "speckit_critical")
        code, stdout, stderr = self.run_check_main(
            fixture_dir, "--lane", "Critical", "--require-approved", "--json")
        self.assertEqual(code, 0, "Spec Kit critical bundle rejected: %s %s" % (stdout, stderr))
        data = json.loads(stdout)
        self.assertEqual(data.get("errors"), 0)
        self.assertEqual(data.get("criteria"), 2)

    def test_unmapped_spec_unit_fails(self):
        files = {
            "proposal.md": "# Proposal\n## Why\nWhy.\n## What Changes\n- x\n",
            "specs/a/spec.md": (
                "# Delta\n## ADDED Requirements\n"
                "### Requirement: R1\n#### Scenario: S1\n- **WHEN** x\n- **THEN** y\n"
                "#### Scenario: S2\n- **WHEN** x2\n- **THEN** y2\n"
            ),
            "design.md": "# Design\n## Context\nContext.\n",
            "tasks.md": (
                "# Tasks\n- [x] 1.1 Do work\n\n## SDLC evidence\nStatus: approved\nApproved-by: Dana Lee (2026-11-10)\n\n"
                "| Source | Unit | Test | Fails before | Expected result |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| specs/a/spec.md | [\"ADDED\", \"R1\", \"S1\"] | tests/test_ops.py::t | missing today | y |\n"
            ),
        }
        bdir = self.make_bundle(files)
        code, stdout, _ = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertEqual(code, 1)
        data = json.loads(stdout)
        self.assertGreater(data.get("errors", 0), 0)
        messages = [f.get("message", "") for f in data.get("findings", [])]
        self.assertTrue(any("has no test expectation in tasks.md" in m for m in messages), messages)

    def test_openspec_missing_critical_risk_artifacts_fails(self):
        # Missing threat-note.md
        files = {
            "proposal.md": "# Proposal\n## Why\nWhy.\n## What Changes\n- x\n",
            "specs/a/spec.md": "# Delta\n## ADDED Requirements\n### Requirement: R1\n#### Scenario: S1\n- **WHEN** x\n- **THEN** y\n",
            "design.md": "# Design\n## Context\nContext.\n",
            "tasks.md": (
                "# Tasks\n- [x] 1.1 Do work\n\n## SDLC evidence\nStatus: approved\nApproved-by: Dana Lee (2026-11-10)\n\n"
                "| Source | Unit | Test | Fails before | Expected result |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| specs/a/spec.md | [\"ADDED\", \"R1\", \"S1\"] | tests/test_ops.py::t | missing today | y |\n"
            ),
            "rollout-plan.md": "# Rollout\n" + ("Valid rollout plan text. " * 5),
        }
        bdir = self.make_bundle(files)
        code, stdout, _ = self.run_check_main(bdir, "--lane", "Critical", "--json")
        self.assertNotEqual(code, 0)
        data = json.loads(stdout)
        self.assertTrue(any("Critical bundle requires 'threat-note.md'" in f["message"] for f in data["findings"]))

        # Also test when both threat-note.md and rollout-plan.md are missing
        del files["rollout-plan.md"]
        bdir2 = self.make_bundle(files)
        code2, stdout2, _ = self.run_check_main(bdir2, "--lane", "Critical", "--json")
        self.assertNotEqual(code2, 0)
        data2 = json.loads(stdout2)
        msgs = [f["message"] for f in data2["findings"]]
        self.assertTrue(any("Critical bundle requires 'threat-note.md'" in m for m in msgs))
        self.assertTrue(any("Critical bundle requires 'rollout-plan.md'" in m for m in msgs))

    def test_removal_and_rename_delta_operations_supported(self):
        files = {
            "proposal.md": "# Proposal\n## Why\nClean up legacy endpoints.\n## What Changes\n- Remove legacy\n- Rename v1\n",
            "specs/legacy/spec.md": (
                "# Delta\n\n## REMOVED Requirements\n\n"
                "### Requirement: Legacy Export\n"
                "**Reason**: Superseded by v2 export\n"
                "**Migration**: Use GET /api/v2/export\n\n"
                "## RENAMED Requirements\n\n"
                "### Requirement: FROM: Old Query TO: New Query\n"
            ),
            "design.md": "# Design\n## Context\nContext.\n",
            "tasks.md": (
                "# Tasks\n- [x] 1.1 Remove export\n\n## SDLC evidence\nStatus: approved\nApproved-by: Dana Lee (2026-11-10)\n\n"
                "| Source | Unit | Test | Fails before | Expected result |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| specs/legacy/spec.md | [\"REMOVED\", \"Legacy Export\"] | tests/test_ops.py::test_removed | regression check | legacy endpoint returns 410 Gone |\n"
                "| specs/legacy/spec.md | [\"RENAMED\", \"Old Query\", \"New Query\"] | tests/test_ops.py::test_renamed | rename check | redirects old query to new query |\n"
            ),
        }
        bdir = self.make_bundle(files)
        code, stdout, stderr = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertEqual(code, 0, "Removal and rename bundle failed: %s %s" % (stdout, stderr))
        data = json.loads(stdout)
        self.assertEqual(data.get("criteria"), 2)

    def test_removal_without_reason_or_migration_fails(self):
        files = {
            "proposal.md": "# Proposal\n## Why\nWhy.\n## What Changes\n- Remove\n",
            "specs/legacy/spec.md": (
                "# Delta\n\n## REMOVED Requirements\n\n"
                "### Requirement: Incomplete Removal\n"
            ),
            "design.md": "# Design\n## Context\nContext.\n",
            "tasks.md": (
                "# Tasks\n- [x] 1.1 Task\n\n## SDLC evidence\nStatus: approved\nApproved-by: Dana Lee (2026-11-10)\n\n"
                "| Source | Unit | Test | Fails before | Expected result |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| specs/legacy/spec.md | [\"REMOVED\", \"Incomplete Removal\"] | tests/test_ops.py::test_rem | missing today | 410 |\n"
            ),
        }
        bdir = self.make_bundle(files)
        code, stdout, _ = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertNotEqual(code, 0)
        data = json.loads(stdout)
        self.assertTrue(any("requires both **Reason** and **Migration**" in f["message"] for f in data["findings"]))

    def test_evidence_in_comments_or_fences_is_ignored(self):
        # Scenario defined only inside a comment
        files = {
            "proposal.md": "# Proposal\n## Why\nWhy.\n## What Changes\n- X\n",
            "specs/a/spec.md": (
                "# Delta\n\n"
                "<!--\n## ADDED Requirements\n### Requirement: Hidden Req\n#### Scenario: Hidden Scenario\n- **WHEN** x\n- **THEN** y\n-->\n"
            ),
            "design.md": "# Design\n## Context\nContext.\n",
            "tasks.md": (
                "# Tasks\n\n## SDLC evidence\nStatus: approved\nApproved-by: Dana Lee (2026-11-10)\n\n"
                "| Source | Unit | Test | Fails before | Expected result |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| specs/a/spec.md | [\"ADDED\", \"Hidden Req\", \"Hidden Scenario\"] | tests/test_ops.py::t | missing today | y |\n"
            ),
        }
        bdir = self.make_bundle(files)
        code, stdout, _ = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertNotEqual(code, 0)
        data = json.loads(stdout)
        self.assertTrue(any("unknown source unit" in f["message"] for f in data["findings"]))

    def test_mapping_cannot_replace_source_then_outcome(self):
        files = {
            "proposal.md": "# Proposal\n## Why\nWhy.\n## What Changes\n- X\n",
            "specs/a/spec.md": (
                "# Delta\n\n## ADDED Requirements\n### Requirement: Req1\n#### Scenario: Scen1\n"
                "- **WHEN** valid request is sent\n- **THEN** status code is 201 Created\n"
            ),
            "design.md": "# Design\n## Context\nContext.\n",
            "tasks.md": (
                "# Tasks\n\n## SDLC evidence\nStatus: approved\nApproved-by: Dana Lee (2026-11-10)\n\n"
                "| Source | Unit | Test | Fails before | Expected result |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| specs/a/spec.md | [\"ADDED\", \"Req1\", \"Scen1\"] | tests/test_ops.py::t | missing today | status code is 500 Server Error |\n"
            ),
        }
        bdir = self.make_bundle(files)
        code, stdout, _ = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertNotEqual(code, 0)
        data = json.loads(stdout)
        self.assertTrue(any("cannot replace source THEN outcome" in f["message"] for f in data["findings"]))

    def test_escaped_pipe_in_table_cell_survives(self):
        files = {
            "proposal.md": "# Proposal\n## Why\nWhy.\n## What Changes\n- X\n",
            "specs/a/spec.md": (
                "# Delta\n\n## ADDED Requirements\n### Requirement: Pipe Req\n#### Scenario: Pipe Scen\n"
                "- **WHEN** input with pipe | is processed\n- **THEN** output contains option A | option B\n"
            ),
            "design.md": "# Design\n## Context\nContext.\n",
            "tasks.md": (
                "# Tasks\n\n## SDLC evidence\nStatus: approved\nApproved-by: Dana Lee (2026-11-10)\n\n"
                "| Source | Unit | Test | Fails before | Expected result |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| specs/a/spec.md | [\"ADDED\", \"Pipe Req\", \"Pipe Scen\"] | tests/test_ops.py::t | missing today | output contains option A \\| option B |\n"
            ),
        }
        bdir = self.make_bundle(files)
        code, stdout, stderr = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertEqual(code, 0, "Escaped pipe handling failed: %s %s" % (stdout, stderr))
        data = json.loads(stdout)
        self.assertEqual(data.get("errors"), 0)

    def test_secrets_detected_and_never_echoed(self):
        secret = "ghp_" + "a" * 36
        files = {
            "proposal.md": "# Proposal\n## Why\nWhy.\n## What Changes\n- X\n",
            "specs/a/spec.md": "# Delta\n## ADDED Requirements\n### Requirement: R1\n#### Scenario: S1\n- **WHEN** x\n- **THEN** y\n",
            "design.md": "# Design\n## Context\nSecret key is " + secret + "\n",
            "tasks.md": (
                "# Tasks\n\n## SDLC evidence\nStatus: approved\nApproved-by: Dana Lee (2026-11-10)\n\n"
                "| Source | Unit | Test | Fails before | Expected result |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| specs/a/spec.md | [\"ADDED\", \"R1\", \"S1\"] | tests/test_ops.py::t | missing today | y |\n"
            ),
        }
        bdir = self.make_bundle(files)
        code, stdout, _ = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertNotEqual(code, 0)
        data = json.loads(stdout)
        self.assertTrue(any("GitHub token" in f["message"] for f in data["findings"]))
        self.assertNotIn(secret, stdout)

    def test_hidden_unicode_control_characters_detected(self):
        files = {
            "proposal.md": "# Proposal\n## Why\nWhy.\n## What Changes\n- X\n",
            "specs/a/spec.md": "# Delta\n## ADDED Requirements\n### Requirement: R1\n#### Scenario: S1\n- **WHEN** x\u200bhidden\n- **THEN** y\n",
            "design.md": "# Design\n## Context\nContext.\n",
            "tasks.md": (
                "# Tasks\n\n## SDLC evidence\nStatus: approved\nApproved-by: Dana Lee (2026-11-10)\n\n"
                "| Source | Unit | Test | Fails before | Expected result |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| specs/a/spec.md | [\"ADDED\", \"R1\", \"S1\"] | tests/test_ops.py::t | missing today | y |\n"
            ),
        }
        bdir = self.make_bundle(files)
        code, stdout, _ = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertNotEqual(code, 0)
        data = json.loads(stdout)
        self.assertTrue(any("hidden Unicode control" in f["message"] for f in data["findings"]))

    def test_invalid_utf8_encoding_fails(self):
        files = {
            "proposal.md": b"# Proposal\n\xff\xfe\x00 Invalid UTF-8 bytes\n",
            "specs/a/spec.md": b"# Delta\n## ADDED Requirements\n### Requirement: R1\n#### Scenario: S1\n- **WHEN** x\n- **THEN** y\n",
            "design.md": b"# Design\n## Context\nContext.\n",
            "tasks.md": b"# Tasks\n",
        }
        bdir = self.make_bundle(files)
        code, stdout, _ = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertNotEqual(code, 0)
        data = json.loads(stdout)
        self.assertTrue(any("invalid UTF-8 encoding" in f["message"] for f in data["findings"]))

    def test_missing_required_openspec_member_fails(self):
        # Missing proposal.md
        files = {
            "specs/a/spec.md": "# Delta\n## ADDED Requirements\n### Requirement: R1\n#### Scenario: S1\n- **WHEN** x\n- **THEN** y\n",
            "design.md": "# Design\n## Context\nContext.\n",
            "tasks.md": "# Tasks\n",
        }
        bdir = self.make_bundle(files)
        code, stdout, _ = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertNotEqual(code, 0)
        data = json.loads(stdout)
        self.assertTrue(any("missing proposal.md" in f["message"] for f in data["findings"]))

    def test_missing_required_speckit_member_fails(self):
        # Spec Kit missing plan.md
        files = {
            "spec.md": "# Feature: Test\n",
            "tasks.md": "# Tasks\n",
        }
        bdir = self.make_bundle(files)
        code, stdout, _ = self.run_check_main(bdir, "--lane", "Standard", "--json")
        self.assertNotEqual(code, 0)
        data = json.loads(stdout)
        self.assertTrue(any("missing plan.md" in f["message"] for f in data["findings"]))


def _read_text(path):
    with open(path, "r", encoding="utf-8") as h:
        return h.read()


class EvidenceInteropContract(unittest.TestCase):
    """Verifies that evidence_check.py evaluates upstream specification bundles at git revision."""

    def setUp(self):
        self.workspace = tempfile.mkdtemp()
        self.addCleanup(support.remove_tree, self.workspace)
        self.repo = os.path.join(self.workspace, "repo")
        os.makedirs(self.repo, exist_ok=True)
        self.git("init", "-q", "-b", "main")
        # Base commit
        self.put("README.md", "# Test repo\n")
        self.put("scripts/lane-config.yaml", _read_text(os.path.join(ROOT, "scripts", "lane-config.yaml")))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.base_sha = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "-b", "feature")

    def git(self, *args):
        proc = subprocess.run(["git", "-C", self.repo, "-c", "user.name=Test", "-c", "user.email=test@test"] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return proc.stdout

    def put(self, rel_path, content):
        full = os.path.join(self.repo, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if isinstance(content, bytes):
            with open(full, "wb") as h:
                h.write(content)
        else:
            with open(full, "w", encoding="utf-8") as h:
                h.write(content)

    def run_evidence_check(self, pr_body, lane="Standard", extra_args=None):
        body_file = os.path.join(self.workspace, "pr_body.md")
        with open(body_file, "w", encoding="utf-8") as h:
            h.write(pr_body)
        head_sha = self.git("rev-parse", "HEAD").strip()
        cmd = [
            sys.executable, "-B", os.path.join(ROOT, "scripts", "evidence_check.py"),
            "--ci",
            "--config", os.path.join(ROOT, "scripts", "lane-config.yaml"),
            "--repo-root", self.repo,
            "--base", self.base_sha,
            "--head", head_sha,
            "--pr-body-file", body_file,
            "--json"
        ]
        if extra_args:
            cmd.extend(extra_args)
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return proc.returncode, proc.stdout, proc.stderr

    def test_evidence_check_standard_openspec_bundle_passes(self):
        # Copy openspec_standard fixture into repository
        src = os.path.join(FIXTURES_DIR, "openspec_standard")
        for dp, _, fnames in os.walk(src):
            for fn in fnames:
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, src).replace("\\", "/")
                self.put("openspec/changes/widget-management/" + rel, _read_text(full))
        self.put("src/widget.py", "def make_widget(): pass\n")
        self.put("tests/test_widget.py", "def test_create_widget(): pass\ndef test_create_invalid(): pass\ndef test_query_widget(): pass\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "add widget management")

        body = (
            "## Summary\nAdds widget management.\n\n"
            "Spec: openspec/changes/widget-management\n\n"
            "## Trace\nUsed standard tooling to draft and build widget api.\n\n"
            "## Review notes\nVerified all 3 acceptance criteria on fixture.\n"
        )
        code, stdout, stderr = self.run_evidence_check(body, lane="Standard")
        self.assertEqual(code, 0, "Standard evidence check rejected: %s %s" % (stdout, stderr))
        data = json.loads(stdout)
        self.assertEqual(data.get("missing"), [])

    def test_evidence_check_critical_openspec_bundle_resolves_proposal_and_risk_artifacts(self):
        src = os.path.join(FIXTURES_DIR, "openspec_critical")
        for dp, _, fnames in os.walk(src):
            for fn in fnames:
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, src).replace("\\", "/")
                self.put("openspec/changes/auth-service/" + rel, _read_text(full))
        self.put("auth/token.py", "def sign_token(): pass\n")
        self.put("tests/test_auth.py", "def test_login_valid(): pass\ndef test_login_invalid(): pass\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "critical auth service")

        # Note: No explicit Intent link, no explicit ## Threat note or ## Rollout plan in body
        # The OpenSpec bundle proposal.md, threat-note.md, and rollout-plan.md must resolve them!
        body = (
            "## Summary\nCritical auth service.\n\n"
            "Spec: openspec/changes/auth-service\n\n"
            "## Trace\nUsed agent to implement security token service.\n\n"
            "## Review notes\nVerified 2 criteria; two reviewers verified threat model.\n"
        )
        code, stdout, stderr = self.run_evidence_check(body, lane="Critical")
        self.assertEqual(code, 0, "Critical evidence check rejected: %s %s" % (stdout, stderr))
        data = json.loads(stdout)
        self.assertEqual(data.get("missing"), [])

    def test_evidence_check_critical_invalid_explicit_intent_link_fails(self):
        src = os.path.join(FIXTURES_DIR, "openspec_critical")
        for dp, _, fnames in os.walk(src):
            for fn in fnames:
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, src).replace("\\", "/")
                self.put("openspec/changes/auth-service/" + rel, _read_text(full))
        self.put("auth/token.py", "def sign_token(): pass\n")
        self.put("tests/test_auth.py", "def test_login_valid(): pass\ndef test_login_invalid(): pass\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "critical auth service")

        body = (
            "## Summary\nCritical auth service.\n\n"
            "Spec: openspec/changes/auth-service\n"
            "Intent link: nonexistent_intent.md\n\n"
            "## Trace\nUsed agent to implement security token service.\n\n"
            "## Review notes\nVerified 2 criteria; two reviewers verified threat model.\n"
        )
        code, stdout, stderr = self.run_evidence_check(body, lane="Critical")
        self.assertNotEqual(code, 0)
        data = json.loads(stdout)
        self.assertIn("intent_link", data.get("missing", []))

    def test_evidence_check_working_tree_cannot_repair_bad_commit(self):
        # Commit a bundle missing tasks.md
        src = os.path.join(FIXTURES_DIR, "openspec_standard")
        for dp, _, fnames in os.walk(src):
            for fn in fnames:
                if fn == "tasks.md":
                    continue
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, src).replace("\\", "/")
                self.put("openspec/changes/widget-management/" + rel, _read_text(full))
        self.put("src/widget.py", "def make_widget(): pass\n")
        self.put("tests/test_widget.py", "def test_create_widget(): pass\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "commit with incomplete bundle")

        # Now put tasks.md in working tree, UNCOMMITTED!
        tasks_full = os.path.join(src, "tasks.md")
        self.put("openspec/changes/widget-management/tasks.md", _read_text(tasks_full))

        body = (
            "Spec: openspec/changes/widget-management\n\n"
            "## Trace\nTrace content.\n\n"
            "## Review notes\nReview content.\n"
        )
        code, stdout, _ = self.run_evidence_check(body, lane="Standard")
        self.assertNotEqual(code, 0, "Working tree uncommitted repair must be rejected")
        data = json.loads(stdout)
        self.assertIn("spec_link", data.get("missing", []))


if __name__ == "__main__":
    unittest.main()
