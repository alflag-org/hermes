from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DocsContractTest(unittest.TestCase):
    def test_readme_uses_atlas_or_shim_execution_for_hermes_examples(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("atlas run hermes host check", readme)
        self.assertIn("hermes host check", readme)
        self.assertNotIn("python3 commands/hermes.py", readme)
        self.assertNotIn("python commands/hermes.py", readme)


if __name__ == "__main__":
    unittest.main()
