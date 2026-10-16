import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def slurp(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
        return handle.read()


class CiAdapters(unittest.TestCase):
    def test_all_ci_adapter_files_exist(self):
        for rel in (
            "adapters/ci/gitlab-ci.yml",
            "adapters/ci/azure-pipelines.yml",
            "adapters/ci/bitbucket-pipelines.yml",
            "adapters/ci/README.md",
        ):
            path = os.path.join(ROOT, rel)
            self.assertTrue(os.path.isfile(path), "%s missing" % rel)
            self.assertGreater(os.path.getsize(path), 50, "%s too small" % rel)

    def test_gitlab_ci_configuration(self):
        text = slurp("adapters/ci/gitlab-ci.yml")
        self.assertIn("ci-generic.sh", text)
        self.assertIn("GIT_DEPTH: 0", text)
        self.assertIn("SDLC_BASE", text)
        self.assertIn("SDLC_HEAD", text)
        self.assertIn("SDLC_PR_BODY_FILE", text)

    def test_azure_devops_configuration(self):
        text = slurp("adapters/ci/azure-pipelines.yml")
        self.assertIn("ci-generic.sh", text)
        self.assertIn("fetchDepth: 0", text)
        self.assertIn("SDLC_BASE", text)
        self.assertIn("SDLC_HEAD", text)
        self.assertIn("SDLC_PR_BODY_FILE", text)

    def test_bitbucket_configuration(self):
        text = slurp("adapters/ci/bitbucket-pipelines.yml")
        self.assertIn("ci-generic.sh", text)
        self.assertIn("depth: full", text)
        self.assertIn("SDLC_BASE", text)
        self.assertIn("SDLC_HEAD", text)
        self.assertIn("SDLC_PR_BODY_FILE", text)


if __name__ == "__main__":
    unittest.main()
