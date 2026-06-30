from __future__ import annotations

from typing import Any

from hermes.plan import now_iso


def normalize_state(raw: Any, site: str | None = None) -> dict[str, Any]:
    if isinstance(raw, dict) and raw.get("kind") == "proxmox-state":
        state = dict(raw)
        state["guests"] = [
            _normalize_guest(guest, site or state.get("site")) for guest in state.get("guests", [])
        ]
        return state
    guests = _extract_guests(raw)
    return {
        "kind": "proxmox-state",
        "version": "v1",
        "site": site,
        "collected_at": now_iso(),
        "guests": [_normalize_guest(guest, site) for guest in guests],
    }


def _extract_guests(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [guest for guest in raw if isinstance(guest, dict)]
    if not isinstance(raw, dict):
        return []
    if isinstance(raw.get("guests"), list):
        return raw["guests"]
    if isinstance(raw.get("data"), list):
        return raw["data"]
    result: list[dict[str, Any]] = []
    for node in raw.get("nodes", []):
        node_name = node.get("node") or node.get("name")
        for guest in node.get("guests", []):
            merged = dict(guest)
            merged.setdefault("node", node_name)
            result.append(merged)
    return result


def _normalize_guest(guest: dict[str, Any], site: str | None) -> dict[str, Any]:
    vmid = guest.get("vmid") or guest.get("id")
    tags = guest.get("tags") or []
    if isinstance(tags, str):
        tags = [tag for tag in tags.replace(",", ";").split(";") if tag]
    return {
        "vmid": int(vmid) if str(vmid or "").isdigit() else vmid,
        "name": str(guest.get("name") or guest.get("hostname") or vmid),
        "node": guest.get("node"),
        "type": str(guest.get("type") or guest.get("kind") or "qemu"),
        "status": guest.get("status"),
        "site": guest.get("site") or site,
        "tags": sorted(str(tag) for tag in tags),
        "description": guest.get("description") or guest.get("notes"),
        "ip_addresses": _normalize_ips(
            guest.get("ip_addresses") or guest.get("ips") or guest.get("ip")
        ),
    }


def _normalize_ips(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
