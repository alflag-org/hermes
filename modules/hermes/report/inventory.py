from __future__ import annotations

from typing import Any

from hermes.proxmox.normalize import normalize_state


def inventory_report(actual: Any, site: str | None = None) -> dict[str, Any]:
    state = normalize_state(actual, site)
    return {
        "kind": "inventory-report",
        "version": "v1",
        "site": state.get("site"),
        "guest_count": len(state.get("guests", [])),
        "guests": state.get("guests", []),
    }
