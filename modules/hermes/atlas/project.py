from __future__ import annotations

from typing import Any

from hermes.manifest.load import HostManifest
from hermes.manifest.schema import normalized_tag


def render_atlas_host(manifest: HostManifest) -> dict[str, Any]:
    services = list(manifest.services)
    capabilities = list(manifest.capabilities)
    tags = ["managed-daedalus"]
    tags.extend(f"svc-{normalized_tag(service)}" for service in services)
    tags.extend(f"cap-{normalized_tag(capability)}" for capability in capabilities)
    return {
        "name": manifest.name,
        "site": manifest.site,
        "zone": manifest.zone,
        "role": services[0] if services else "host",
        "environment": str(manifest.catalog_tags.get("environment") or "home"),
        "runtime_kind": manifest.platform,
        "tags": sorted(tags),
    }
