from __future__ import annotations

from typing import Any

from hermes.manifest.load import HostManifest


def render_daedalus_inventory(manifests: list[HostManifest]) -> dict[str, Any]:
    grouped: dict[str, dict[str, dict[str, str]]] = {}
    for manifest in _sorted_manifests(manifests):
        name = str(manifest.name)
        _add_host(grouped, str(manifest.zone), name, {"ansible_host": str(manifest.address)})
        _add_host(grouped, f"provider_{manifest.provider}", name, {})
        _add_host(grouped, f"platform_{manifest.platform}", name, {})
        for service in manifest.services:
            _add_host(grouped, f"svc_{service}", name, {})
        for capability in manifest.capabilities:
            _add_host(grouped, f"cap_{capability}", name, {})

    children = {
        group: {"hosts": dict(sorted(hosts.items()))}
        for group, hosts in sorted(grouped.items(), key=lambda item: _group_sort_key(item[0]))
    }
    return {"all": {"children": {"default": {"children": children}}}}


def expected_daedalus_hosts(manifests: list[HostManifest]) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        groups = {
            str(manifest.zone),
            f"provider_{manifest.provider}",
            f"platform_{manifest.platform}",
            *(f"svc_{service}" for service in manifest.services),
            *(f"cap_{capability}" for capability in manifest.capabilities),
        }
        expected[str(manifest.name)] = {
            "name": str(manifest.name),
            "ansible_host": str(manifest.address),
            "groups": sorted(groups, key=_group_sort_key),
        }
    return dict(sorted(expected.items()))


def _add_host(
    grouped: dict[str, dict[str, dict[str, str]]],
    group: str,
    host: str,
    vars_: dict[str, str],
) -> None:
    grouped.setdefault(group, {})[host] = vars_


def _sorted_manifests(manifests: list[HostManifest]) -> list[HostManifest]:
    return sorted(manifests, key=lambda item: (item.site or "", item.name or ""))


def _group_sort_key(group: str) -> tuple[int, str]:
    if group in {"client", "mgmt", "dmz", "transit", "unused_native"}:
        return (0, group)
    if group.startswith("provider_"):
        return (1, group)
    if group.startswith("platform_"):
        return (2, group)
    if group.startswith("svc_"):
        return (3, group)
    if group.startswith("cap_"):
        return (4, group)
    return (5, group)
