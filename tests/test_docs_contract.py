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
        self.assertIn("hermes manifest check", commands)
        self.assertIn("hermes report projections", commands)

    def test_required_manifest_model_docs_exist(self) -> None:
        source_of_truth = (REPO_ROOT / "docs" / "source-of-truth.md").read_text(encoding="utf-8")
        host_manifest = (REPO_ROOT / "docs" / "host-manifest.md").read_text(encoding="utf-8")

        self.assertIn("host manifest = source of truth", source_of_truth)
        self.assertIn("Daedalus inventory = convergence projection", source_of_truth)
        self.assertIn("manifests/hosts/<site>/*.yml", host_manifest)
        self.assertIn("Zabbix-related values are rejected", host_manifest)


if __name__ == "__main__":
    unittest.main()
