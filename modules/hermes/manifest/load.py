from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from hermes.errors import UsageError


@dataclass(frozen=True)
class HostManifest:
    path: str
    data: Any
    load_error: str | None
    version: Any
    kind: Any
    name: str | None
    site: str | None
    lifecycle: str | None
    zone: str | None
    address: str | None
    provider: str | None
    platform: str | None
    services: tuple[str, ...]
    capabilities: tuple[str, ...]
    catalog_resource_id: str | None
    display_name: str | None
    description: str | None
    catalog_tags: dict[str, Any]

    @property
    def filename_name(self) -> str:
        return Path(self.path).stem

    @property
    def directory_site(self) -> str:
        return Path(self.path).parent.name

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "site": self.site,
            "lifecycle": self.lifecycle,
            "zone": self.zone,
            "address": self.address,
            "provider": self.provider,
            "platform": self.platform,
            "services": list(self.services),
            "capabilities": list(self.capabilities),
            "catalog_resource_id": self.catalog_resource_id,
            "source": self.path,
        }


def load_host_manifests(path: str | Path) -> list[HostManifest]:
    return [_load_manifest_file(source) for source in _manifest_files(Path(path))]


def _manifest_files(root: Path) -> list[Path]:
    if not root.exists():
        raise UsageError(f"manifest path does not exist: {root}")
    if root.is_file():
        if root.suffix.lower() not in {".yml", ".yaml"}:
            raise UsageError(f"manifest file must be YAML: {root}")
        return [root]

    direct = sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}
    )
    if direct:
        return direct

    nested = sorted(path for path in root.glob("*/*.yml") if path.is_file())
    nested.extend(sorted(path for path in root.glob("*/*.yaml") if path.is_file()))
    if nested:
        return sorted(nested)
    raise UsageError(f"no host manifest YAML files found under: {root}")


def _load_manifest_file(path: Path) -> HostManifest:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        load_error = None
    except yaml.YAMLError as exc:
        data = {}
        load_error = str(exc)

    if not isinstance(data, dict):
        return HostManifest(
            path=str(path),
            data=data,
            load_error=load_error,
            version=None,
            kind=None,
            name=None,
            site=None,
            lifecycle=None,
            zone=None,
            address=None,
            provider=None,
            platform=None,
            services=(),
            capabilities=(),
            catalog_resource_id=None,
            display_name=None,
            description=None,
            catalog_tags={},
        )

    metadata = _mapping(data.get("metadata"))
    spec = _mapping(data.get("spec"))
    catalog = _mapping(data.get("catalog"))
    provider = _mapping(spec.get("provider"))
    platform = _mapping(spec.get("platform"))

    return HostManifest(
        path=str(path),
        data=data,
        load_error=load_error,
        version=data.get("version"),
        kind=data.get("kind"),
        name=_optional_str(metadata.get("name")),
        site=_optional_str(metadata.get("site")),
        lifecycle=_optional_str(metadata.get("lifecycle")),
        zone=_optional_str(spec.get("zone")),
        address=_optional_str(spec.get("address")),
        provider=_optional_str(provider.get("type")),
        platform=_optional_str(platform.get("type")),
        services=tuple(_string_list(spec.get("services"))),
        capabilities=tuple(_string_list(spec.get("capabilities"))),
        catalog_resource_id=_optional_str(catalog.get("resource_id")),
        display_name=_optional_str(catalog.get("display_name")),
        description=_optional_str(catalog.get("description")),
        catalog_tags=dict(_mapping(catalog.get("tags"))),
    )


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return []
