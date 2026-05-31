from __future__ import annotations

from typing import Any

from hermes.cataloga.dataset import normalize_dataset
from hermes.proxmox.normalize import normalize_state


def diff_state(actual_raw: Any, desired_raw: Any, site: str | None = None) -> dict[str, Any]:
    actual = normalize_state(actual_raw, site)
    desired = normalize_dataset(desired_raw)
    actual_by_name = {guest["name"]: guest for guest in actual["guests"]}
    desired_guests = [_desired_guest(resource) for resource in desired["resources"]]
    desired_by_name = {guest["name"]: guest for guest in desired_guests if guest}

    missing = [guest for name, guest in desired_by_name.items() if name not in actual_by_name]
    extra = [guest for name, guest in actual_by_name.items() if name not in desired_by_name]
    changed: list[dict[str, Any]] = []
    for name, desired_guest in desired_by_name.items():
        actual_guest = actual_by_name.get(name)
        if not actual_guest:
            continue
        deltas: dict[str, Any] = {}
        for key in ("tags", "description"):
            if desired_guest.get(key) is not None and desired_guest.get(key) != actual_guest.get(key):
                deltas[key] = {"actual": actual_guest.get(key), "desired": desired_guest.get(key)}
        if deltas:
            changed.append(
                {
                    "name": name,
                    "vmid": actual_guest.get("vmid"),
                    "node": actual_guest.get("node"),
                    "type": actual_guest.get("type"),
                    "changes": deltas,
                }
            )
    return {
        "kind": "proxmox-diff",
        "version": "v1",
        "site": site or actual.get("site"),
        "missing": missing,
        "extra": extra,
        "changed": changed,
    }


def plan_from_diff(diff: dict[str, Any]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    for guest in diff.get("changed", []):
        changes = guest.get("changes") or {}
        if "tags" in changes:
            actions.append(
                {
                    "action": "update-tags",
                    "name": guest["name"],
                    "vmid": guest.get("vmid"),
                    "node": guest.get("node"),
                    "type": guest.get("type"),
                    "tags": changes["tags"]["desired"],
                }
            )
        if "description" in changes:
            actions.append(
                {
                    "action": "update-description",
                    "name": guest["name"],
                    "vmid": guest.get("vmid"),
                    "node": guest.get("node"),
                    "type": guest.get("type"),
                    "description": changes["description"]["desired"],
                }
            )
    for guest in diff.get("missing", []):
        actions.append({"action": "report-missing-guest", "name": guest["name"]})
    return {
        "kind": "sync-plan",
        "version": "v1",
        "site": diff.get("site"),
        "domain": "proxmox",
        "actions": actions,
    }


def _desired_guest(resource: dict[str, Any]) -> dict[str, Any] | None:
    proxmox = resource.get("proxmox") or {}
    if resource.get("type") not in {"vm", "lxc", "host", "guest"} and not proxmox:
        return None
    tags = proxmox.get("tags", resource.get("tags"))
    if isinstance(tags, str):
        tags = [tag for tag in tags.replace(",", ";").split(";") if tag]
    return {
        "name": str(proxmox.get("name") or resource.get("name") or resource["id"]),
        "vmid": proxmox.get("vmid") or resource.get("vmid"),
        "tags": sorted(str(tag) for tag in tags) if tags is not None else None,
        "description": proxmox.get("description") or resource.get("description"),
    }
