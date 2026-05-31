from __future__ import annotations

import sys
from typing import Any, TextIO

from hermes.io import dump_data


def emit(data: Any, fmt: str = "text", stream: TextIO | None = None) -> None:
    target = stream or sys.stdout
    if fmt in {"json", "yaml"}:
        target.write(dump_data(data, fmt))
        return
    text = render_text(data)
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
