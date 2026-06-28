from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DocsContractTest(unittest.TestCase):
    def test_readme_documents_atlas_shim_and_local_development_paths(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("atlas run hermes context", readme)
        self.assertIn("hermes network summary", readme)
        self.assertIn("PYTHONPATH=modules python3 commands/hermes.py --help", readme)
        self.assertIn("Zabbix has been retired", readme)

    def test_command_docs_include_safety_categories(self) -> None:
        commands = (REPO_ROOT / "docs" / "commands.md").read_text(encoding="utf-8")

        self.assertIn("dry-run default mutation", commands)
        self.assertIn("transitional mutation", commands)
        self.assertIn("hermes dns report", commands)


if __name__ == "__main__":
    unittest.main()
