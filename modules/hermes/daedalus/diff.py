from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes.daedalus.project import expected_daedalus_hosts
from hermes.inventory.daedalus import load_hosts
from hermes.manifest.load import HostManifest
from hermes.manifest.schema import DEPRECATED_ZONES, ZABBIX_VALUES
from hermes.models import warning


def diff_daedalus_projection(
    manifests: list[HostManifest],
    inventory_path: str | Path,
) -> dict[str, Any]:
    expected = expected_daedalus_hosts(manifests)
    actual_hosts, inventory_warnings = load_hosts(inventory_path)
    actual = {str(host["name"]): host for host in actual_hosts}
    mismatches: list[dict[str, Any]] = []

    for name, expected_host in expected.items():
        actual_host = actual.get(name)
        if actual_host is None:
            mismatches.append(
                _mismatch("missing-inventory-host", f"missing host in inventory: {name}", name)
            )
            continue
        if str(actual_host.get("ansible_host")) != expected_host["ansible_host"]:
            actual_address = actual_host.get("ansible_host")
            mismatches.append(
                _mismatch(
                    "wrong-ansible-host",
                    f"{name} ansible_host expected {expected_host['ansible_host']} "
                    f"got {actual_address}",
                    name,
                )
            )
        expected_groups = set(expected_host["groups"])
        actual_groups = {
            str(group) for group in actual_host.get("groups", []) if group not in {"all", "default"}
        }
        for group in sorted(expected_groups - actual_groups):
            mismatches.append(
                _mismatch(_missing_group_code(group), f"{name} missing group: {group}", name)
            )
        for group in sorted(actual_groups - expected_groups):
            mismatches.append(
                _mismatch(_extra_group_code(group), f"{name} extra group: {group}", name)
            )
        for group in sorted(actual_groups):
            lowered = group.lower()
            if _deprecated_group(lowered):
                mismatches.append(
                    _mismatch(
                        "deprecated-group-usage",
                        f"{name} uses deprecated group: {group}",
                        name,
                    )
                )
            if any(value in lowered for value in ZABBIX_VALUES):
                mismatches.append(
                    _mismatch(
                        "zabbix-group-usage",
                        f"{name} uses Zabbix group: {group}",
                        name,
                    )
                )

    for name in sorted(set(actual) - set(expected)):
        mismatches.append(
            _mismatch("extra-inventory-host", f"extra host in inventory: {name}", name)
        )

    error_warnings = [item for item in inventory_warnings if item.get("severity") == "error"]
    mismatches.extend(error_warnings)
    ok = not mismatches
    return {
        "kind": "daedalus-diff",
        "version": "v1",
        "ok": ok,
        "expected_host_count": len(expected),
        "actual_host_count": len(actual),
        "mismatches": mismatches,
        "warnings": [item for item in inventory_warnings if item.get("severity") != "error"],
        "_exit_code": 0 if ok else 2,
    }


def _missing_group_code(group: str) -> str:
    if group.startswith("provider_"):
        return "wrong-provider-group"
    if group.startswith("platform_"):
        return "wrong-platform-group"
    if group.startswith("svc_"):
        return "wrong-service-group"
    if group.startswith("cap_"):
        return "wrong-capability-group"
    return "wrong-zone-group"


def _extra_group_code(group: str) -> str:
    if group.startswith("provider_"):
        return "extra-provider-group"
    if group.startswith("platform_"):
        return "extra-platform-group"
    if group.startswith("svc_"):
        return "extra-service-group"
    if group.startswith("cap_"):
        return "extra-capability-group"
    return "extra-group"


def _deprecated_group(group: str) -> bool:
    return group in DEPRECATED_ZONES or any(group == f"zone_{zone}" for zone in DEPRECATED_ZONES)


def _mismatch(code: str, message: str, source: str) -> dict[str, Any]:
    return warning(code, message, severity="error", source=source)
