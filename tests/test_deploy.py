# tests/test_deploy.py
import json
import os
import tempfile
import unittest
from unittest import mock

import deploy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDeploy(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_deploy_creates_release_and_current_link(self):
        with mock.patch.dict(os.environ, {"BUILD_NUMBER": "7"}):
            release_dir, output, _ = deploy.deploy(ROOT, self.tmp.name)

        current = os.path.join(self.tmp.name, "current")
        self.assertEqual(os.path.realpath(current),
                         os.path.realpath(release_dir))
        self.assertTrue(os.path.isfile(os.path.join(current, "app.py")))
        with open(os.path.join(current, "release.json")) as f:
            self.assertEqual(json.load(f)["build_number"], "7")
        self.assertEqual(output, "Hello, World from Jad Moharam!")

    def test_old_releases_are_pruned(self):
        for build in range(deploy.KEEP_RELEASES + 2):
            with mock.patch.dict(os.environ, {"BUILD_NUMBER": str(build)}):
                release_dir, _, _ = deploy.deploy(ROOT, self.tmp.name)

        releases = os.listdir(os.path.join(self.tmp.name, "releases"))
        self.assertEqual(len(releases), deploy.KEEP_RELEASES)
        self.assertIn(os.path.basename(release_dir), releases)


if __name__ == "__main__":
    unittest.main()
