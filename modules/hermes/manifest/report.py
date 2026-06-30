from __future__ import annotations

from collections import Counter
from typing import Any

from hermes.manifest.load import HostManifest
from hermes.manifest.validate import validate_host_manifests


def manifest_list_report(
    manifests: list[HostManifest],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    validation = validate_host_manifests(manifests, strict=strict)
    return {
        "kind": "manifest-list",
        "version": "v1",
        "count": len(manifests),
        "hosts": [
            manifest.summary()
            for manifest in sorted(manifests, key=lambda item: (item.site or "", item.name or ""))
        ],
        "warnings": validation["warnings"],
        "errors": validation["errors"],
    }


def manifest_summary_report(
    manifests: list[HostManifest],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    validation = validate_host_manifests(manifests, strict=strict)
    return {
        "kind": "manifest-summary",
        "version": "v1",
        "host_count": len(manifests),
        "sites": _counts(manifest.site for manifest in manifests),
        "lifecycles": _counts(manifest.lifecycle for manifest in manifests),
        "zones": _counts(manifest.zone for manifest in manifests),
        "providers": _counts(manifest.provider for manifest in manifests),
        "platforms": _counts(manifest.platform for manifest in manifests),
        "services": _counts(service for manifest in manifests for service in manifest.services),
        "capabilities": _counts(
            capability for manifest in manifests for capability in manifest.capabilities
        ),
        "warnings": validation["warnings"],
        "errors": validation["errors"],
    }


def host_report(manifests: list[HostManifest], *, strict: bool = False) -> dict[str, Any]:
    summary = manifest_summary_report(manifests, strict=strict)
    return {
        **summary,
        "kind": "host-report",
        "hosts": [
            manifest.summary()
            for manifest in sorted(manifests, key=lambda item: (item.site or "", item.name or ""))
        ],
    }


def _counts(values: Any) -> dict[str, int]:
    counter = Counter(str(value) for value in values if value)
    return dict(sorted(counter.items()))
