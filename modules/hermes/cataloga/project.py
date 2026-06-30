from __future__ import annotations

from typing import Any

from hermes.manifest.load import HostManifest


def render_cataloga_dataset(manifests: list[HostManifest]) -> dict[str, Any]:
    return {
        "version": 1,
        "resources": [
            _resource_for_manifest(manifest) for manifest in _sorted_manifests(manifests)
        ],
    }


def expected_cataloga_resources(
    manifests: list[HostManifest],
) -> dict[str, dict[str, Any]]:
    dataset = render_cataloga_dataset(manifests)
    return {str(resource["id"]): resource for resource in dataset["resources"]}


def _resource_for_manifest(manifest: HostManifest) -> dict[str, Any]:
    tags = {str(key): value for key, value in manifest.catalog_tags.items()}
    tags.update(
        {
            "managed_by": str(tags.get("managed_by") or "daedalus"),
            "site": str(manifest.site),
            "zone": str(manifest.zone),
        }
    )
    return {
        "id": str(manifest.catalog_resource_id),
        "type": "host",
        "name": str(manifest.display_name or manifest.name),
        "description": str(manifest.description or ""),
        "lifecycle": str(manifest.lifecycle),
        "tags": dict(sorted(tags.items())),
        "spec": {
            "daedalus_host": str(manifest.name),
            "address": str(manifest.address),
            "provider": str(manifest.provider),
            "platform": str(manifest.platform),
            "services": list(manifest.services),
            "capabilities": list(manifest.capabilities),
        },
    }


def _sorted_manifests(manifests: list[HostManifest]) -> list[HostManifest]:
    return sorted(manifests, key=lambda item: (item.site or "", item.name or ""))
