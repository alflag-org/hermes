from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from jsonschema import validate


REPO_ROOT = Path(__file__).resolve().parents[1]


class SchemaExamplesTest(unittest.TestCase):
    def test_examples_match_published_schemas(self) -> None:
        pairs = [
            (
                "schemas/hermes-config.v1.schema.json",
                yaml.safe_load((REPO_ROOT / "examples/hermes.yml").read_text(encoding="utf-8")),
            ),
            (
                "schemas/proxmox-state.v1.schema.json",
                json.loads((REPO_ROOT / "examples/proxmox-state.json").read_text(encoding="utf-8")),
            ),
            (
                "schemas/sync-plan.v1.schema.json",
                json.loads((REPO_ROOT / "examples/dns-zone-plan.json").read_text(encoding="utf-8")),
            ),
            (
                "schemas/dns-zone-plan.v1.schema.json",
                json.loads((REPO_ROOT / "examples/dns-zone-plan.json").read_text(encoding="utf-8")),
            ),
        ]

        for schema_path, instance in pairs:
            with self.subTest(schema=schema_path):
                schema = json.loads((REPO_ROOT / schema_path).read_text(encoding="utf-8"))
                validate(instance=instance, schema=schema)


if __name__ == "__main__":
    unittest.main()
