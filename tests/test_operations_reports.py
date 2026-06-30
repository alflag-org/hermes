from __future__ import annotations

import unittest
from pathlib import Path

from hermes.context import discover_context
from hermes.inventory.daedalus import host_list_report, host_summary_report, load_hosts
from hermes.inventory.network import network_summary
from hermes.output import render_markdown
from hermes.report.dns import dns_inventory_report
from hermes.report.summary import operations_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "daedalus-simple"


class OperationsReportsTest(unittest.TestCase):
    def test_kanagawa01_network_model_has_active_and_deprecated_networks(self) -> None:
        report = network_summary("kanagawa01")
        active = {network["name"] for network in report["active_networks"]}
        deprecated = {network["name"] for network in report["deprecated_networks"]}

        self.assertEqual(active, {"CLIENT", "MGMT", "DMZ", "TRANSIT", "UNUSED_NATIVE"})
        self.assertEqual(deprecated, {"INTERNAL", "STORAGE", "OVERLAY", "IOT"})
        self.assertTrue(active.isdisjoint(deprecated))

    def test_inventory_reader_infers_zones_and_services(self) -> None:
        context = discover_context(workspace=str(FIXTURE), config_path="/tmp/hermes.yml")

        hosts, warnings = load_hosts(context["inventory_path"])
        by_name = {host["name"]: host for host in hosts}

        self.assertEqual(by_name["kng01-mgmt-recursive-dns-01"]["zone"], "mgmt")
        self.assertEqual(by_name["kng01-dmz-authoritative-dns-01"]["zone"], "dmz")
        self.assertIn("dns", by_name["kng01-mgmt-recursive-dns-01"]["services"])
        self.assertIn("host-zone-unknown", {item["code"] for item in warnings})

    def test_host_list_filters_by_zone_and_service(self) -> None:
        context = discover_context(workspace=str(FIXTURE), config_path="/tmp/hermes.yml")
        hosts, warnings = load_hosts(context["inventory_path"])

        report = host_list_report(hosts, warnings, zone="mgmt", service="dns")

        self.assertEqual(report["count"], 1)
        self.assertEqual(report["hosts"][0]["name"], "kng01-mgmt-recursive-dns-01")

    def test_dns_report_detects_hosts_groups_and_zone_files_without_writes(self) -> None:
        context = discover_context(workspace=str(FIXTURE), config_path="/tmp/hermes.yml")
        hosts, warnings = load_hosts(context["inventory_path"])

        report = dns_inventory_report(
            workspace=context["workspace"], hosts=hosts, inventory_warnings=warnings
        )

        self.assertEqual(report["authoritative_hosts"], ["kng01-dmz-authoritative-dns-01"])
        self.assertEqual(report["recursive_hosts"], ["kng01-mgmt-recursive-dns-01"])
        self.assertIn("dns", report["dns_groups"])
        self.assertTrue(any(path.endswith("alflag.internal.zone") for path in report["zone_files"]))

    def test_operations_summary_contains_stable_markdown_sections(self) -> None:
        context = discover_context(workspace=str(FIXTURE), config_path="/tmp/hermes.yml")
        hosts, warnings = load_hosts(context["inventory_path"])
        host_summary = host_summary_report(hosts, warnings)
        dns = dns_inventory_report(
            workspace=context["workspace"], hosts=hosts, inventory_warnings=warnings
        )
        summary = operations_summary(
            context=context,
            networks=network_summary("kanagawa01"),
            hosts=hosts,
            host_summary=host_summary,
            dns=dns,
        )

        markdown = render_markdown(summary)

        self.assertIn("# Hermes Operations Summary", markdown)
        self.assertIn("## Context", markdown)
        self.assertIn("## Networks", markdown)
        self.assertIn("## DNS", markdown)
        self.assertEqual(summary["host_summary"]["host_count"], 4)


if __name__ == "__main__":
    unittest.main()
