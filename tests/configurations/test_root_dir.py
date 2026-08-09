import os.path
from unittest import TestCase

from app.configurations.root_dir import root_dir


class TestRoot(TestCase):
    def test_root_resolves_to_the_app_source_directory(self):
        # root_dir() must resolve to the `app` package directory itself,
        # independent of what the checked-out repository folder is named
        # (local `lavs`, CI `lavs-core`, …) — hardcoding that name is brittle.
        result = root_dir()

        self.assertEqual(os.path.basename(result), "app")
        self.assertTrue(os.path.isdir(result))
        self.assertTrue(os.path.isfile(os.path.join(result, "main.py")))
