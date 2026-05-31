from __future__ import annotations

from typing import Any

from hermes.proxmox.diff import diff_state


def drift_report(actual: Any, desired: Any, site: str | None = None) -> dict[str, Any]:
    proxmox = diff_state(actual, desired, site)
    return {
        "kind": "drift-report",
        "version": "v1",
        "site": proxmox.get("site"),
        "proxmox": proxmox,
        "missing": proxmox.get("missing", []),
        "extra": proxmox.get("extra", []),
        "changed": proxmox.get("changed", []),
    }
