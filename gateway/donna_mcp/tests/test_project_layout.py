from __future__ import annotations

from pathlib import Path
import unittest

from scripts.python import compare_versions


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProjectLayoutTests(unittest.TestCase):
    def test_comparator_covers_only_canonical_files(self) -> None:
        self.assertNotIn("src/donna_mcp/sentry.py", compare_versions.COMMON_FILES)
        for relative_path in compare_versions.COMMON_FILES:
            with self.subTest(path=relative_path):
                self.assertTrue((PROJECT_ROOT / relative_path).is_file())

    def test_versioned_provider_examples_exist(self) -> None:
        for relative_path in compare_versions.VERSION_PROVIDER.values():
            with self.subTest(path=relative_path):
                self.assertTrue((PROJECT_ROOT / relative_path).is_file())


if __name__ == "__main__":
    unittest.main()
