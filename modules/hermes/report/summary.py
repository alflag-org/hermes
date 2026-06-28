from __future__ import annotations

from typing import Any


def operations_summary(
    *,
    context: dict[str, Any],
    networks: dict[str, Any],
    hosts: list[dict[str, Any]],
    host_summary: dict[str, Any],
    dns: dict[str, Any],
) -> dict[str, Any]:
    warnings = _dedupe_warnings(
        [
            *context.get("warnings", []),
            *networks.get("warnings", []),
            *host_summary.get("warnings", []),
            *dns.get("warnings", []),
        ]
    )
    return {
        "kind": "operations-summary",
        "version": "v1",
        "context": context,
        "networks": networks,
        "host_summary": host_summary,
        "hosts": hosts,
        "dns": dns,
        "deprecated_concepts": [
            "Zabbix is retired and is not an active Hermes integration.",
            "Dangerous cutover, failover, rollback, and break-glass operations belong to future Ares scope.",
            "Strict read-only probes and preflight validation belong to future Themis scope.",
        ],
        "warnings": warnings,
        "suggested_manual_checks": [
            "Review unknown-zone hosts and add explicit groups or naming where needed.",
            "Review DNS zone files before using dns diff-zone or the transitional apply-zone command.",
            "Review generated plans before passing --apply to any transitional mutation command.",
        ],
    }


def _dedupe_warnings(warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str | None]] = set()
    result: list[dict[str, Any]] = []
    for item in warnings:
        key = (str(item.get("code")), str(item.get("message")), item.get("source"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
