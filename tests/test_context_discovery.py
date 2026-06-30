from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hermes.context import discover_context


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "daedalus-simple"


class ContextDiscoveryTest(unittest.TestCase):
    def test_explicit_workspace_detects_site_inventory(self) -> None:
        context = discover_context(workspace=str(FIXTURE), config_path="/tmp/hermes.yml")

        self.assertEqual(context["site"], "kanagawa01")
        self.assertTrue(context["inventory_path"].endswith("ansible/inventory/sites/kanagawa01"))
        self.assertEqual(context["workspace"], str(FIXTURE.resolve()))

    def test_hermes_workspace_environment_is_used(self) -> None:
        with patch.dict(os.environ, {"HERMES_WORKSPACE": str(FIXTURE)}):
            context = discover_context(
                config_path="/tmp/hermes.yml", cwd=Path(tempfile.gettempdir())
            )

        self.assertEqual(context["workspace"], str(FIXTURE.resolve()))

    def test_upward_discovery_finds_workspace_marker(self) -> None:
        child = FIXTURE / "ansible" / "inventory" / "sites" / "kanagawa01"

        context = discover_context(cwd=child, config_path="/tmp/hermes.yml")

        self.assertEqual(context["workspace"], str(FIXTURE.resolve()))

    def test_missing_workspace_reports_warning(self) -> None:
        missing = FIXTURE / "missing"

        context = discover_context(workspace=str(missing), config_path="/tmp/hermes.yml")

        self.assertIsNone(context["inventory_path"])
        self.assertIn("workspace-missing", {item["code"] for item in context["warnings"]})


if __name__ == "__main__":
    unittest.main()
