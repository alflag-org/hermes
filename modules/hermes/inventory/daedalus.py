from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from hermes.models import warning


SERVICE_PREFIXES = ("svc_", "cap_", "platform_", "provider_")
ZONE_NAMES = ("mgmt", "dmz", "client", "transit")


def load_hosts(
    inventory_path: str | Path | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    if inventory_path is None:
        return [], [warning("inventory-missing", "no inventory path was discovered")]
    root = Path(inventory_path)
    if not root.exists():
        return [], [warning("inventory-missing", "inventory path does not exist", source=str(root))]

    hosts: dict[str, dict[str, Any]] = {}
    for source in _inventory_files(root):
        try:
            data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            warnings.append(
                warning("inventory-yaml-error", str(exc), severity="error", source=str(source))
            )
            continue
        if not isinstance(data, dict):
            warnings.append(
                warning("inventory-ignored", "inventory file is not a mapping", source=str(source))
            )
            continue
        _walk_inventory(data, source, hosts)

    records = [_finalize_host(record) for record in hosts.values()]
    for record in records:
        warnings.extend(record.get("warnings", []))
    return sorted(records, key=lambda item: item["name"]), warnings


def filter_hosts(
    hosts: list[dict[str, Any]],
    *,
    zone: str | None = None,
    group: str | None = None,
    service: str | None = None,
) -> list[dict[str, Any]]:
    selected = hosts
    if zone:
        selected = [host for host in selected if host.get("zone") == zone]
    if group:
        selected = [host for host in selected if group in host.get("groups", [])]
    if service:
        selected = [host for host in selected if service in host.get("services", [])]
    return selected


def host_list_report(
    hosts: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    *,
    zone: str | None = None,
    group: str | None = None,
    service: str | None = None,
) -> dict[str, Any]:
    selected = filter_hosts(hosts, zone=zone, group=group, service=service)
    return {
        "kind": "host-list",
        "version": "v1",
        "count": len(selected),
        "filters": {"zone": zone, "group": group, "service": service},
        "hosts": selected,
        "warnings": warnings,
    }


def host_summary_report(
    hosts: list[dict[str, Any]], warnings: list[dict[str, Any]]
) -> dict[str, Any]:
    zones: dict[str, int] = {}
    groups: dict[str, int] = {}
    services: dict[str, int] = {}
    for host in hosts:
        zones[str(host.get("zone") or "unknown")] = (
            zones.get(str(host.get("zone") or "unknown"), 0) + 1
        )
        for group in host.get("groups", []):
            groups[group] = groups.get(group, 0) + 1
        for service in host.get("services", []):
            services[service] = services.get(service, 0) + 1
    return {
        "kind": "host-summary",
        "version": "v1",
        "host_count": len(hosts),
        "zones": dict(sorted(zones.items())),
        "groups": dict(sorted(groups.items())),
        "services": dict(sorted(services.items())),
        "warnings": warnings,
    }


def _inventory_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".yml", ".yaml"}
        and "group_vars" not in path.parts
    )


def _walk_inventory(data: dict[str, Any], source: Path, hosts: dict[str, dict[str, Any]]) -> None:
    if "all" in data and isinstance(data["all"], dict):
        _walk_group("all", data["all"], (), {}, source, hosts)
        return
    if "hosts" in data or "children" in data:
        _walk_group("all", data, (), {}, source, hosts)
        return
    for group_name, group_data in data.items():
        if isinstance(group_data, dict):
            _walk_group(str(group_name), group_data, (), {}, source, hosts)


def _walk_group(
    group_name: str,
    data: dict[str, Any],
    inherited_groups: tuple[str, ...],
    inherited_vars: dict[str, Any],
    source: Path,
    hosts: dict[str, dict[str, Any]],
) -> None:
    groups = inherited_groups if group_name == "all" else (*inherited_groups, group_name)
    group_vars = dict(inherited_vars)
    if isinstance(data.get("vars"), dict):
        group_vars.update(data["vars"])

    raw_hosts = data.get("hosts") or {}
    if isinstance(raw_hosts, dict):
        for host_name, host_vars in raw_hosts.items():
            merged_vars = dict(group_vars)
            if isinstance(host_vars, dict):
                merged_vars.update(host_vars)
            _merge_host(str(host_name), merged_vars, groups, source, hosts)
    elif isinstance(raw_hosts, list):
        for host_name in raw_hosts:
            _merge_host(str(host_name), dict(group_vars), groups, source, hosts)

    children = data.get("children") or {}
    if isinstance(children, dict):
        for child_name, child_data in children.items():
            if isinstance(child_data, dict):
                _walk_group(str(child_name), child_data, groups, group_vars, source, hosts)


def _merge_host(
    name: str,
    vars_: dict[str, Any],
    groups: tuple[str, ...],
    source: Path,
    hosts: dict[str, dict[str, Any]],
) -> None:
    existing = hosts.setdefault(
        name,
        {
            "name": name,
            "ansible_host": None,
            "groups": set(),
            "services": set(),
            "source": str(source),
            "warnings": [],
        },
    )
    if vars_.get("ansible_host") is not None:
        existing["ansible_host"] = str(vars_["ansible_host"])
    existing["groups"].update(str(group) for group in groups)
    existing["services"].update(_service_hints(vars_, groups))
    if not existing.get("source"):
        existing["source"] = str(source)


def _finalize_host(record: dict[str, Any]) -> dict[str, Any]:
    groups = tuple(sorted(record.get("groups") or ()))
    services = tuple(sorted(record.get("services") or ()))
    zone = _infer_zone(str(record["name"]), groups)
    warnings = list(record.get("warnings") or [])
    if zone == "unknown":
        warnings.append(
            warning(
                "host-zone-unknown",
                "could not infer host zone from hostname or groups",
                source=str(record["name"]),
            )
        )
    return {
        "name": str(record["name"]),
        "ansible_host": record.get("ansible_host"),
        "groups": list(groups),
        "zone": zone,
        "services": list(services),
        "source": record.get("source"),
        "warnings": warnings,
    }


def _infer_zone(hostname: str, groups: tuple[str, ...]) -> str:
    lowered_name = hostname.lower()
    for zone in ZONE_NAMES:
        if f"-{zone}-" in lowered_name or lowered_name.endswith(f"-{zone}"):
            return zone
    lowered_groups = [group.lower() for group in groups]
    for zone in ZONE_NAMES:
        if any(
            group == zone or group == f"zone_{zone}" or zone in group.split("_")
            for group in lowered_groups
        ):
            return zone
    return "unknown"


def _service_hints(vars_: dict[str, Any], groups: tuple[str, ...]) -> set[str]:
    hints: set[str] = set()
    for key, value in vars_.items():
        key_text = str(key)
        for prefix in SERVICE_PREFIXES:
            if key_text.startswith(prefix) and _truthy(value):
                hints.add(key_text.removeprefix(prefix))
        if key_text in {"service", "services", "capability", "capabilities"}:
            hints.update(_string_values(value))
    for group in groups:
        group_text = str(group)
        for prefix in SERVICE_PREFIXES:
            if group_text.startswith(prefix):
                hints.add(group_text.removeprefix(prefix))
    return hints


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.lower() not in {"", "false", "no", "off", "0"}
    return bool(value)


def _string_values(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    if isinstance(value, list | tuple | set):
        return {str(item) for item in value}
    return {str(value)}
