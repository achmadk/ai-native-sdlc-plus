"""Source-index checks, kept separate from behavioral mutation observers."""

import os
from pathlib import Path
import subprocess
import unittest

if __package__:
    from . import mutate, support
else:
    import mutate
    import support


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_SKILLS = set("ai-sdlc spec-first context-pack review-by-intent decision-trace verify-and-evals "
                     "ship-and-observe learning-mode autonomy-policy ai-readiness-and-metrics".split())
GENERATED_ROOTS = (".agents/skills/", ".claude/skills/", ".kilocode/skills/", ".opencode/skills/")


def git(root, *args, check=True):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(["git", "-C", str(root)] + list(args), env=env, capture_output=True, check=check)


def tracked_paths(root):
    return [path for path in git(root, "ls-files", "-z").stdout.decode("utf-8", "surrogateescape").split("\0") if path]


def excluded(path):
    if "__pycache__" in path.split("/") or path.endswith((".pyc", ".pyo")):
        return True
    if path == "opencode_session.txt" or (path.startswith(".omo/run-continuation/") and path.endswith(".json")):
        return True
    return any(path.startswith(root + "openspec-") and "/" in path[len(root):] for root in GENERATED_ROOTS)


class RepositoryIndex(unittest.TestCase):
    def setUp(self):
        try:
            top = git(ROOT, "rev-parse", "--show-toplevel").stdout.decode().strip()
        except subprocess.CalledProcessError:
            self.skipTest("source Git index unavailable; hygiene not evaluated")
        if Path(top).resolve() != ROOT:
            self.skipTest("copied tree is not the source Git root; hygiene not evaluated")

    def test_no_generated_or_session_files_are_tracked(self):
        self.assertEqual([path for path in tracked_paths(ROOT) if excluded(path)], [],
                         "local/generated artifacts must not be part of the source index")

    def test_product_skill_index_is_exact(self):
        names = {path.split("/")[1] for path in tracked_paths(ROOT)
                 if path.startswith("skills/") and path.endswith("/SKILL.md") and len(path.split("/")) == 3}
        self.assertEqual(names, PRODUCT_SKILLS)


class HygieneRules(unittest.TestCase):
    def test_authored_sources_and_adapters_are_not_excluded(self):
        for path in ("AGENTS.md", ".claude/CLAUDE.md", ".claude/commands/review.md", ".cursorrules",
                     ".github/copilot-instructions.md", ".kilo/command/review.md", "adapters/example.yml",
                     "openspec/specs/ci-security/spec.md", "skills/ai-sdlc/SKILL.md"):
            with self.subTest(path=path):
                self.assertFalse(excluded(path))

    def test_hygiene_checks_are_not_mutation_observers(self):
        for observers in mutate.TESTS.values():
            self.assertFalse(any(name == "tests.test_repository_hygiene" or
                                 name.startswith("tests.test_repository_hygiene.") for name in observers))

    def test_project_ignores_all_excluded_classes(self):
        paths = ["scripts/__pycache__/fixture.pyc", ".omo/run-continuation/fixture.json", "opencode_session.txt"]
        paths += [root + "openspec-propose/SKILL.md" for root in GENERATED_ROOTS]
        with support.TemporaryDirectory(prefix="sdlc-hygiene-") as directory:
            root = Path(directory)
            git(root, "init", "-q")
            (root / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
            for path in paths:
                with self.subTest(path=path):
                    result = git(root, "check-ignore", "--no-index", "--", path, check=False)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout.decode().strip(), path)
            for path in ("AGENTS.md", ".claude/CLAUDE.md", ".claude/commands/review.md", ".kilo/agent/review.md",
                         "skills/ai-sdlc/SKILL.md", "adapters/ci/gitlab-ci.yml",
                         "openspec/specs/ci-security/spec.md", "scripts/scanner-profiles.json"):
                with self.subTest(preserved=path):
                    self.assertEqual(git(root, "check-ignore", "--no-index", "--", path,
                                         check=False).returncode, 1)

    def test_forced_index_addition_cannot_evade_exclusion_detection(self):
        with support.TemporaryDirectory(prefix="sdlc-hygiene-") as directory:
            root = Path(directory)
            git(root, "init", "-q")
            (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
            path = "scripts/__pycache__/fixture.pyc"
            artifact = root / path
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"fixture, not bytecode")
            git(root, "add", "-f", "--", path)
            self.assertEqual([name for name in tracked_paths(root) if excluded(name)], [path])


if __name__ == "__main__":
    unittest.main()
