from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes.models import warning


DNS_HINTS = ("dns", "nsd", "unbound", "authoritative", "recursive")
AUTHORITATIVE_HINTS = ("authoritative-dns", "authoritative", "nsd")
RECURSIVE_HINTS = ("recursive-dns", "recursive", "unbound")
ZONE_FILE_SUFFIXES = (".zone", ".db")


def dns_inventory_report(
    *,
    workspace: str | None,
    hosts: list[dict[str, Any]],
    inventory_warnings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    authoritative_hosts: set[str] = set()
    recursive_hosts: set[str] = set()
    dns_groups: set[str] = set()

    for host in hosts:
        name = str(host.get("name") or "")
        groups = [str(group) for group in host.get("groups", [])]
        services = [str(service) for service in host.get("services", [])]
        lowered_tokens = [name.lower(), *(group.lower() for group in groups), *(service.lower() for service in services)]
        if any(_contains_hint(token, AUTHORITATIVE_HINTS) for token in lowered_tokens):
            authoritative_hosts.add(name)
        if any(_contains_hint(token, RECURSIVE_HINTS) for token in lowered_tokens):
            recursive_hosts.add(name)
        for group in groups:
            if _contains_hint(group.lower(), DNS_HINTS):
                dns_groups.add(group)

    zone_files = _detect_zone_files(workspace)
    warnings = list(inventory_warnings or [])
    if not authoritative_hosts:
        warnings.append(warning("dns-authoritative-unknown", "no authoritative DNS hosts were inferred"))
    if not recursive_hosts:
        warnings.append(warning("dns-recursive-unknown", "no recursive DNS hosts were inferred"))
    if not dns_groups:
        warnings.append(warning("dns-groups-unknown", "no DNS-related inventory groups were inferred"))
    if workspace is None:
        warnings.append(warning("dns-workspace-missing", "zone files cannot be detected without a workspace"))
    elif not zone_files:
        warnings.append(warning("dns-zone-files-unknown", "no likely zone files were detected", source=workspace))

    return {
        "kind": "dns-report",
        "version": "v1",
        "authoritative_hosts": sorted(authoritative_hosts),
        "recursive_hosts": sorted(recursive_hosts),
        "dns_groups": sorted(dns_groups),
        "zone_files": zone_files,
        "warnings": warnings,
    }


def _contains_hint(value: str, hints: tuple[str, ...]) -> bool:
    return any(hint in value for hint in hints)


def _detect_zone_files(workspace: str | None) -> list[str]:
    if workspace is None:
        return []
    root = Path(workspace)
    if not root.exists():
        return []
    files: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or _skip_path(path):
            continue
        name = path.name.lower()
        parts = tuple(part.lower() for part in path.parts)
        if name.endswith(ZONE_FILE_SUFFIXES) or (
            any(part in {"dns", "nsd", "unbound", "zones", "zone"} for part in parts)
            and path.suffix.lower() in {".conf", ".zone", ".db", ".yml", ".yaml"}
        ):
            files.append(str(path))
    return sorted(files)


def _skip_path(path: Path) -> bool:
    return any(part in {".git", "__pycache__", ".pytest_cache", ".ruff_cache"} for part in path.parts)
