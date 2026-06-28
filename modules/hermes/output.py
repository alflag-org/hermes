from __future__ import annotations

import sys
from typing import Any, TextIO

from hermes.io import dump_data


def emit(data: Any, fmt: str = "text", stream: TextIO | None = None) -> None:
    target = stream or sys.stdout
    if fmt in {"json", "yaml"}:
        target.write(dump_data(data, fmt))
        return
    text = render_markdown(data) if fmt == "markdown" else render_text(data)
    target.write(text)
    if not text.endswith("\n"):
        target.write("\n")


def render_text(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return "\n".join(render_text(item) for item in data)
    if not isinstance(data, dict):
        return str(data)

    kind = data.get("kind")
    if kind == "host-check":
        lines = ["ok: " + str(data.get("ok", False)).lower()]
        lines.extend(f"- {item}" for item in data.get("checks", []))
        lines.extend(f"! {item}" for item in data.get("errors", []))
        return "\n".join(lines)
    if kind == "dns-zone-check":
        lines = [f"zone: {data.get('zone')}", f"ok: {str(data.get('ok')).lower()}"]
        lines.extend(f"! {error}" for error in data.get("errors", []))
        return "\n".join(lines)
    if kind == "context":
        lines = [
            f"workspace: {data.get('workspace')}",
            f"site: {data.get('site')}",
            f"inventory_path: {data.get('inventory_path')}",
            f"atlas_context_available: {str(data.get('atlas_context_available')).lower()}",
            f"config_path: {data.get('config_path')}",
            f"mode: {data.get('mode')}",
        ]
        lines.extend(_warning_lines(data.get("warnings", [])))
        return "\n".join(lines)
    if kind == "network-summary":
        lines = [f"site: {data.get('site')}", "active:"]
        lines.extend(_network_lines(data.get("active_networks", [])))
        lines.append("deprecated:")
        lines.extend(_network_lines(data.get("deprecated_networks", [])))
        lines.append(str(data.get("statement")))
        lines.extend(_warning_lines(data.get("warnings", [])))
        return "\n".join(lines)
    if kind == "host-list":
        lines = [f"hosts: {data.get('count', 0)}"]
        for host in data.get("hosts", []):
            lines.append(
                "- "
                + " ".join(
                    [
                        str(host.get("name")),
                        f"zone={host.get('zone')}",
                        f"ansible_host={host.get('ansible_host') or '-'}",
                        f"groups={','.join(host.get('groups', [])) or '-'}",
                        f"services={','.join(host.get('services', [])) or '-'}",
                    ]
                )
            )
        lines.extend(_warning_lines(data.get("warnings", [])))
        return "\n".join(lines)
    if kind == "host-summary":
        lines = [f"hosts: {data.get('host_count', 0)}"]
        lines.extend(_count_lines("zones", data.get("zones", {})))
        lines.extend(_count_lines("groups", data.get("groups", {})))
        lines.extend(_count_lines("services", data.get("services", {})))
        lines.extend(_warning_lines(data.get("warnings", [])))
        return "\n".join(lines)
    if kind == "dns-report" and "authoritative_hosts" in data:
        lines = [
            "authoritative_hosts: " + _join_or_dash(data.get("authoritative_hosts", [])),
            "recursive_hosts: " + _join_or_dash(data.get("recursive_hosts", [])),
            "dns_groups: " + _join_or_dash(data.get("dns_groups", [])),
            "zone_files: " + _join_or_dash(data.get("zone_files", [])),
        ]
        lines.extend(_warning_lines(data.get("warnings", [])))
        return "\n".join(lines)
    if kind == "operations-summary":
        lines = [
            "Hermes operations summary",
            f"workspace: {(data.get('context') or {}).get('workspace')}",
            f"site: {(data.get('context') or {}).get('site')}",
            f"hosts: {(data.get('host_summary') or {}).get('host_count', 0)}",
            "active_networks: " + _join_or_dash(n.get("name") for n in (data.get("networks") or {}).get("active_networks", [])),
            "deprecated_networks: "
            + _join_or_dash(n.get("name") for n in (data.get("networks") or {}).get("deprecated_networks", [])),
            "authoritative_dns: " + _join_or_dash((data.get("dns") or {}).get("authoritative_hosts", [])),
            "recursive_dns: " + _join_or_dash((data.get("dns") or {}).get("recursive_hosts", [])),
        ]
        lines.extend(_warning_lines(data.get("warnings", [])))
        return "\n".join(lines)
    if kind in {"dns-zone-diff", "sync-plan", "proxmox-diff", "drift-report"}:
        lines = [
            f"kind: {kind}",
            f"site: {data.get('site', '-')}",
            f"zone: {data.get('zone', '-')}",
            f"actions: {len(data.get('actions', []))}",
        ]
        for action in data.get("actions", []):
            lines.append("- " + " ".join(f"{k}={v}" for k, v in action.items()))
        for name in ("missing", "extra", "changed"):
            if data.get(name):
                lines.append(f"{name}: {len(data[name])}")
        return "\n".join(lines)
    if kind == "apply-result":
        return "\n".join(
            [
                f"ok: {str(data.get('ok')).lower()}",
                f"applied: {data.get('applied', 0)}",
                f"failed: {data.get('failed', 0)}",
                f"dry_run: {str(data.get('dry_run', False)).lower()}",
            ]
        )

    return "\n".join(f"{key}: {value}" for key, value in data.items())


def render_markdown(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return "\n\n".join(render_markdown(item) for item in data)
    if not isinstance(data, dict):
        return str(data)

    kind = data.get("kind")
    if kind == "context":
        return "\n".join(
            [
                "# Hermes Context",
                "",
                f"- Workspace: `{data.get('workspace')}`",
                f"- Site: `{data.get('site')}`",
                f"- Inventory path: `{data.get('inventory_path')}`",
                f"- Atlas context available: `{str(data.get('atlas_context_available')).lower()}`",
                f"- Config path: `{data.get('config_path')}`",
                f"- Mode: `{data.get('mode')}`",
                "",
                *_markdown_warnings(data.get("warnings", [])),
            ]
        )
    if kind == "network-summary":
        return "\n".join(
            [
                "# KANAGAWA01 Network Summary",
                "",
                "## Active Networks",
                "",
                _network_table(data.get("active_networks", [])),
                "",
                "## Deprecated Networks",
                "",
                _network_table(data.get("deprecated_networks", [])),
                "",
                data.get("statement") or "",
                "",
                *_markdown_warnings(data.get("warnings", [])),
            ]
        )
    if kind == "host-list":
        return "\n".join(
            [
                "# Host List",
                "",
                f"Host count: `{data.get('count', 0)}`",
                "",
                _host_table(data.get("hosts", [])),
                "",
                *_markdown_warnings(data.get("warnings", [])),
            ]
        )
    if kind == "host-summary":
        return "\n".join(
            [
                "# Host Summary",
                "",
                f"Host count: `{data.get('host_count', 0)}`",
                "",
                "## Zones",
                "",
                _count_table(data.get("zones", {})),
                "",
                "## Groups",
                "",
                _count_table(data.get("groups", {})),
                "",
                "## Services",
                "",
                _count_table(data.get("services", {})),
                "",
                *_markdown_warnings(data.get("warnings", [])),
            ]
        )
    if kind == "dns-report" and "authoritative_hosts" in data:
        return "\n".join(
            [
                "# DNS Report",
                "",
                "## Authoritative Hosts",
                "",
                _bullet_list(data.get("authoritative_hosts", [])),
                "",
                "## Recursive Hosts",
                "",
                _bullet_list(data.get("recursive_hosts", [])),
                "",
                "## DNS Groups",
                "",
                _bullet_list(data.get("dns_groups", [])),
                "",
                "## Zone Files",
                "",
                _bullet_list(data.get("zone_files", [])),
                "",
                *_markdown_warnings(data.get("warnings", [])),
            ]
        )
    if kind == "operations-summary":
        context = data.get("context") or {}
        networks = data.get("networks") or {}
        dns = data.get("dns") or {}
        host_summary = data.get("host_summary") or {}
        return "\n".join(
            [
                "# Hermes Operations Summary",
                "",
                "## Context",
                "",
                f"- Workspace: `{context.get('workspace')}`",
                f"- Site: `{context.get('site')}`",
                f"- Inventory path: `{context.get('inventory_path')}`",
                f"- Mode: `{context.get('mode')}`",
                "",
                "## Networks",
                "",
                "### Active",
                "",
                _network_table(networks.get("active_networks", [])),
                "",
                "### Deprecated",
                "",
                _network_table(networks.get("deprecated_networks", [])),
                "",
                "## Hosts",
                "",
                f"Host count: `{host_summary.get('host_count', 0)}`",
                "",
                "### Zones",
                "",
                _count_table(host_summary.get("zones", {})),
                "",
                "## DNS",
                "",
                f"- Authoritative hosts: {_join_or_dash(dns.get('authoritative_hosts', []))}",
                f"- Recursive hosts: {_join_or_dash(dns.get('recursive_hosts', []))}",
                f"- DNS groups: {_join_or_dash(dns.get('dns_groups', []))}",
                f"- Zone files: {_join_or_dash(dns.get('zone_files', []))}",
                "",
                "## Deprecated Concepts",
                "",
                _bullet_list(data.get("deprecated_concepts", [])),
                "",
                "## Warnings",
                "",
                _warning_table(data.get("warnings", [])),
                "",
                "## Suggested Manual Checks",
                "",
                _bullet_list(data.get("suggested_manual_checks", [])),
            ]
        )
    return render_text(data)


def _network_lines(networks: list[dict[str, Any]]) -> list[str]:
    return [
        f"- {network.get('name')} vlan={network.get('vlan_id')} cidr={network.get('cidr')} gateway={network.get('gateway')}"
        for network in networks
    ]


def _count_lines(title: str, counts: dict[str, int]) -> list[str]:
    lines = [f"{title}:"]
    lines.extend(f"- {name}: {count}" for name, count in counts.items())
    return lines


def _warning_lines(warnings: list[dict[str, Any]]) -> list[str]:
    if not warnings:
        return []
    return [
        f"! {item.get('severity', 'warning')} {item.get('code')}: {item.get('message')}"
        + (f" ({item.get('source')})" if item.get("source") else "")
        for item in warnings
    ]


def _join_or_dash(values: Any) -> str:
    selected = [str(value) for value in values if value is not None]
    return ", ".join(selected) if selected else "-"


def _network_table(networks: list[dict[str, Any]]) -> str:
    if not networks:
        return "_None._"
    lines = ["| Name | VLAN | CIDR | Gateway | Purpose | Status | Reason |", "| --- | ---: | --- | --- | --- | --- | --- |"]
    for network in networks:
        lines.append(
            "| {name} | {vlan} | {cidr} | {gateway} | {purpose} | {status} | {reason} |".format(
                name=network.get("name") or "",
                vlan=network.get("vlan_id") if network.get("vlan_id") is not None else "",
                cidr=network.get("cidr") or "",
                gateway=network.get("gateway") or "",
                purpose=network.get("purpose") or "",
                status=network.get("status") or "",
                reason=network.get("reason") or "",
            )
        )
    return "\n".join(lines)


def _host_table(hosts: list[dict[str, Any]]) -> str:
    if not hosts:
        return "_None._"
    lines = ["| Name | Ansible Host | Zone | Groups | Services |", "| --- | --- | --- | --- | --- |"]
    for host in hosts:
        lines.append(
            "| {name} | {ansible_host} | {zone} | {groups} | {services} |".format(
                name=host.get("name") or "",
                ansible_host=host.get("ansible_host") or "",
                zone=host.get("zone") or "",
                groups=", ".join(host.get("groups", [])),
                services=", ".join(host.get("services", [])),
            )
        )
    return "\n".join(lines)


def _count_table(counts: dict[str, int]) -> str:
    if not counts:
        return "_None._"
    lines = ["| Name | Count |", "| --- | ---: |"]
    lines.extend(f"| {name} | {count} |" for name, count in counts.items())
    return "\n".join(lines)


def _bullet_list(items: list[Any]) -> str:
    if not items:
        return "_None._"
    return "\n".join(f"- {item}" for item in items)


def _markdown_warnings(warnings: list[dict[str, Any]]) -> list[str]:
    if not warnings:
        return []
    return ["## Warnings", "", _warning_table(warnings)]


def _warning_table(warnings: list[dict[str, Any]]) -> str:
    if not warnings:
        return "_None._"
    lines = ["| Severity | Code | Message | Source |", "| --- | --- | --- | --- |"]
    for item in warnings:
        lines.append(
            "| {severity} | {code} | {message} | {source} |".format(
                severity=item.get("severity") or "",
                code=item.get("code") or "",
                message=item.get("message") or "",
                source=item.get("source") or "",
            )
        )
    return "\n".join(lines)
