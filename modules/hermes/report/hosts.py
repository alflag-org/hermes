from __future__ import annotations

from typing import Any

from hermes.manifest.load import HostManifest
from hermes.manifest.report import host_report


def manifest_hosts_report(manifests: list[HostManifest], *, strict: bool = False) -> dict[str, Any]:
    return host_report(manifests, strict=strict)
