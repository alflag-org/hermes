from __future__ import annotations

import os
from typing import Any

from hermes.errors import UsageError
from hermes.proxmox.normalize import normalize_state


def collect(config: dict[str, Any], site: str | None = None) -> dict[str, Any]:
    api = _connect(config)
    guests: list[dict[str, Any]] = []
    for node in api.nodes.get():
        node_name = node["node"]
        for guest in api.nodes(node_name).qemu.get():
            guest = dict(guest)
            guest["node"] = node_name
            guest["type"] = "qemu"
            guests.append(guest)
        for guest in api.nodes(node_name).lxc.get():
            guest = dict(guest)
            guest["node"] = node_name
            guest["type"] = "lxc"
            guests.append(guest)
    return normalize_state(guests, site)


def apply_metadata_plan(config: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, Any]:
    api = _connect(config)
    applied = 0
    details: list[dict[str, Any]] = []
    for action in actions:
        action_name = action.get("action")
        if action_name not in {"update-tags", "update-description"}:
            raise UsageError(f"unsupported Proxmox action: {action_name}")
        vmid = action.get("vmid")
        if vmid is None:
            raise UsageError(f"Proxmox action requires vmid: {action}")
        target = _resolve_guest(api, int(vmid), action.get("node"), action.get("type"))
        payload: dict[str, Any] = {}
        if action_name == "update-tags":
            payload["tags"] = ";".join(str(tag) for tag in action.get("tags", []))
        if action_name == "update-description":
            payload["description"] = action.get("description") or ""
        _guest_config(api, target["node"], target["type"], int(vmid)).put(**payload)
        applied += 1
        details.append(
            {"action": action_name, "vmid": vmid, "node": target["node"], "type": target["type"]}
        )
    return {
        "kind": "apply-result",
        "version": "v1",
        "ok": True,
        "applied": applied,
        "failed": 0,
        "dry_run": False,
        "details": details,
    }


def _connect(config: dict[str, Any]):
    proxmox = config.get("proxmox") or {}
    endpoint = proxmox.get("endpoint")
    token_id_env = proxmox.get("token_id_env")
    token_secret_env = proxmox.get("token_secret_env")
    if not endpoint or not token_id_env or not token_secret_env:
        raise UsageError("proxmox.endpoint, token_id_env, and token_secret_env are required")
    token_id = os.environ.get(str(token_id_env))
    token_secret = os.environ.get(str(token_secret_env))
    if not token_id or not token_secret:
        raise UsageError("configured Proxmox token environment variables are not set")
    try:
        from proxmoxer import ProxmoxAPI
    except ImportError as exc:
        raise UsageError("proxmoxer is required for live Proxmox operations") from exc

    host = endpoint.removeprefix("https://").removeprefix("http://").split(":", 1)[0]
    return ProxmoxAPI(
        host,
        user=token_id.split("!", 1)[0],
        token_name=token_id.split("!", 1)[1] if "!" in token_id else token_id,
        token_value=token_secret,
        verify_ssl=bool(proxmox.get("verify_tls", True)),
    )


def _resolve_guest(api, vmid: int, node: str | None, guest_type: str | None) -> dict[str, str]:
    if node and guest_type:
        return {"node": str(node), "type": _api_guest_type(str(guest_type))}
    for resource in api.cluster.resources.get(type="vm"):
        if int(resource.get("vmid")) == vmid:
            return {
                "node": str(resource["node"]),
                "type": _api_guest_type(str(resource.get("type") or guest_type or "qemu")),
            }
    raise UsageError(f"Proxmox guest not found: vmid={vmid}")


def _guest_config(api, node: str, guest_type: str, vmid: int):
    if _api_guest_type(guest_type) == "lxc":
        return api.nodes(node).lxc(vmid).config
    return api.nodes(node).qemu(vmid).config


def _api_guest_type(value: str) -> str:
    normalized = value.lower()
    if normalized in {"lxc", "container"}:
        return "lxc"
    return "qemu"
