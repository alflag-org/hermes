from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hermes.atlas.diff import diff_atlas_host
from hermes.atlas.project import render_atlas_host
from hermes.cataloga.diff import diff_cataloga_projection
from hermes.cataloga.plan import cataloga_plan
from hermes.cataloga.project import render_cataloga_dataset
from hermes.daedalus.diff import diff_daedalus_projection
from hermes.daedalus.project import render_daedalus_inventory
from hermes.io import load_data
from hermes.manifest import load_checked_manifests, load_host_manifests, validate_host_manifests
from hermes.output import render_markdown, render_text
from hermes.report.hosts import manifest_hosts_report
from hermes.report.projections import projection_report


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "manifest-goal"
MANIFESTS = FIXTURE / "manifests" / "hosts" / "kanagawa01"
INVENTORY = FIXTURE / "ansible" / "inventories" / "default" / "hosts.yml"
CATALOG = FIXTURE / "catalog" / "cataloga-hosts.yaml"
ATLAS_WEB01 = FIXTURE / "atlas" / "web01-host.yml"


class ManifestGoalTest(unittest.TestCase):
    def test_valid_manifests_load_and_validate(self) -> None:
        manifests = load_host_manifests(MANIFESTS)
        validation = validate_host_manifests(manifests)

        self.assertTrue(validation["ok"], validation)
        self.assertEqual([manifest.name for manifest in manifests], ["control01", "web01"])
        self.assertEqual({manifest.zone for manifest in manifests}, {"mgmt", "dmz"})

    def test_invalid_manifests_reject_policy_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "web01.yml").write_text(
                _invalid_manifest("web01", "internal", "10.10.30.21", "host-dupe"),
                encoding="utf-8",
            )
            (root / "web02.yml").write_text(
                _invalid_manifest("web01", "dmz", "10.10.30.21", "host-dupe"),
                encoding="utf-8",
            )
            (root / "web03.yml").write_text(
                _invalid_manifest("web03", "dmz", "10.10.10.99", "host-web03"),
                encoding="utf-8",
            )

            validation = validate_host_manifests(load_host_manifests(root))

        codes = {item["code"] for item in validation["errors"]}
        self.assertFalse(validation["ok"])
        self.assertIn("deprecated-zone-active", codes)
        self.assertIn("zabbix-active-value", codes)
        self.assertIn("duplicate-host-name", codes)
        self.assertIn("duplicate-catalog-resource-id", codes)
        self.assertIn("duplicate-address", codes)
        self.assertIn("address-outside-zone-cidr", codes)

    def test_daedalus_projection_render_and_diff(self) -> None:
        manifests = load_checked_manifests(str(MANIFESTS))

        rendered = render_daedalus_inventory(manifests)
        diff = diff_daedalus_projection(manifests, INVENTORY)

        web01 = rendered["all"]["children"]["default"]["children"]["dmz"]["hosts"]["web01"]
        self.assertEqual(
            web01["ansible_host"],
            "10.10.30.21",
        )
        self.assertTrue(diff["ok"], diff)

    def test_daedalus_diff_detects_projection_drift(self) -> None:
        manifests = load_checked_manifests(str(MANIFESTS))
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "hosts.yml"
            inventory.write_text(
                INVENTORY.read_text(encoding="utf-8").replace("10.10.30.21", "10.10.30.99"),
                encoding="utf-8",
            )

            diff = diff_daedalus_projection(manifests, inventory)

        self.assertFalse(diff["ok"])
        self.assertIn("wrong-ansible-host", {item["code"] for item in diff["mismatches"]})

    def test_cataloga_projection_render_diff_and_plan(self) -> None:
        manifests = load_checked_manifests(str(MANIFESTS))

        dataset = render_cataloga_dataset(manifests)
        diff = diff_cataloga_projection(manifests, load_data(CATALOG))
        plan = cataloga_plan(manifests, load_data(CATALOG))

        self.assertEqual(dataset["version"], 1)
        self.assertEqual(dataset["resources"][1]["spec"]["daedalus_host"], "web01")
        self.assertTrue(diff["ok"], diff)
        self.assertEqual(plan["kind"], "cataloga-import-plan")
        self.assertIn("import_dataset", plan)

    def test_cataloga_diff_detects_wrong_fields(self) -> None:
        manifests = load_checked_manifests(str(MANIFESTS))
        catalog = load_data(CATALOG)
        catalog["resources"][1]["tags"]["zone"] = "mgmt"

        diff = diff_cataloga_projection(manifests, catalog)

        self.assertFalse(diff["ok"])
        self.assertIn("wrong-zone-tag", {item["code"] for item in diff["mismatches"]})

    def test_atlas_projection_render_and_diff(self) -> None:
        manifest = load_checked_manifests(str(MANIFESTS / "web01.yml"))[0]

        rendered = render_atlas_host(manifest)
        diff = diff_atlas_host(manifest, load_data(ATLAS_WEB01))

        self.assertEqual(rendered["runtime_kind"], "vm")
        self.assertIn("svc-web", rendered["tags"])
        self.assertTrue(diff["ok"], diff)

    def test_manifest_reports_render_text_and_markdown(self) -> None:
        manifests = load_checked_manifests(str(MANIFESTS))

        host_report = manifest_hosts_report(manifests)
        projection = projection_report(
            manifests,
            inventory=INVENTORY,
            catalog_data=load_data(CATALOG),
        )

        self.assertIn("hosts: 2", render_text(host_report))
        self.assertIn("# Projection Report", render_markdown(projection))
        self.assertTrue(projection["ok"], projection)


def _invalid_manifest(name: str, zone: str, address: str, resource_id: str) -> str:
    return f"""
version: 1
kind: host
metadata:
  name: {name}
  site: {Path.cwd().name}
  lifecycle: active
spec:
  zone: {zone}
  address: {address}
  provider:
    type: proxmox
  platform:
    type: vm
  services:
    - zabbix
  capabilities: []
catalog:
  resource_id: {resource_id}
  display_name: {name}
  description: invalid fixture
  tags:
    managed_by: daedalus
    site: {Path.cwd().name}
    zone: {zone}
""".lstrip()


if __name__ == "__main__":
    unittest.main()
