from __future__ import annotations

from collections import Counter
from ipaddress import ip_address, ip_network
from typing import Any

from hermes.errors import UsageError
from hermes.inventory.network import active_networks
from hermes.manifest.load import HostManifest, load_host_manifests
from hermes.manifest.schema import (
    ACTIVE_ZONES,
    DEPRECATED_ZONES,
    KNOWN_LIFECYCLES,
    KNOWN_PLATFORM_TYPES,
    KNOWN_PROVIDER_TYPES,
    ZABBIX_VALUES,
    is_normalized_slug,
)
from hermes.models import warning


def load_checked_manifests(path: str, *, strict: bool = False) -> list[HostManifest]:
    manifests = load_host_manifests(path)
    result = validate_host_manifests(manifests, strict=strict)
    if not result["ok"]:
        first = (result["errors"] or result.get("warnings") or [{}])[0]
        raise UsageError(f"manifest validation failed: {first.get('message', 'unknown error')}")
    return manifests


def validate_host_manifests(
    manifests: list[HostManifest],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for manifest in manifests:
        host_errors, host_warnings = _validate_single(manifest)
        errors.extend(host_errors)
        warnings.extend(host_warnings)

    errors.extend(
        _duplicate_errors("duplicate-host-name", "duplicate host name", _names(manifests))
    )
    errors.extend(
        _duplicate_errors(
            "duplicate-catalog-resource-id",
            "duplicate catalog resource id",
            [manifest.catalog_resource_id for manifest in manifests],
        )
    )
    errors.extend(
        _duplicate_errors(
            "duplicate-address",
            "duplicate address",
            [manifest.address for manifest in manifests],
        )
    )

    ok = not errors and not (strict and warnings)
    return {
        "kind": "manifest-validation",
        "version": "v1",
        "ok": ok,
        "strict": strict,
        "host_count": len(manifests),
        "errors": errors,
        "warnings": warnings,
        "_exit_code": 0 if ok else 2,
    }


def _validate_single(
    manifest: HostManifest,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    source = manifest.path

    if manifest.load_error:
        errors.append(_error("invalid-yaml", manifest.load_error, source))
        return errors, warnings
    if not isinstance(manifest.data, dict):
        errors.append(_error("invalid-schema", "manifest must be a mapping", source))
        return errors, warnings

    errors.extend(_required_errors(manifest))

    if manifest.version != 1:
        errors.append(_error("invalid-version", "version must be 1", source))
    if manifest.kind != "host":
        errors.append(_error("invalid-kind", "kind must be host", source))
    if manifest.name and manifest.name != manifest.filename_name:
        errors.append(
            _error(
                "manifest-name-mismatch",
                f"metadata.name must match filename {manifest.filename_name}",
                source,
            )
        )
    if manifest.site and manifest.site != manifest.directory_site:
        errors.append(
            _error(
                "manifest-site-mismatch",
                f"metadata.site must match parent directory {manifest.directory_site}",
                source,
            )
        )

    _validate_lifecycle(manifest, errors)
    _validate_zone_and_address(manifest, errors)
    _validate_enum("provider", manifest.provider, KNOWN_PROVIDER_TYPES, errors, source)
    _validate_enum("platform", manifest.platform, KNOWN_PLATFORM_TYPES, errors, source)
    _validate_string_list("services", manifest.services, errors, source)
    _validate_string_list("capabilities", manifest.capabilities, errors, source)

    if not manifest.description:
        warnings.append(
            warning("manifest-description-missing", "missing description", source=source)
        )
    if not manifest.services:
        warnings.append(warning("manifest-services-empty", "empty services", source=source))
    if not manifest.capabilities:
        warnings.append(warning("manifest-capabilities-empty", "empty capabilities", source=source))
    if manifest.lifecycle and manifest.lifecycle != "active":
        warnings.append(
            warning(
                "manifest-lifecycle-not-active",
                f"lifecycle is {manifest.lifecycle}",
                source=source,
            )
        )

    if manifest.lifecycle == "active":
        zabbix_hits = sorted(_zabbix_values(manifest.data))
        for hit in zabbix_hits:
            errors.append(
                _error(
                    "zabbix-active-value",
                    f"active Zabbix-related value is not allowed: {hit}",
                    source,
                )
            )

    return errors, warnings


def _required_errors(manifest: HostManifest) -> list[dict[str, Any]]:
    required = {
        "metadata.name": manifest.name,
        "metadata.site": manifest.site,
        "metadata.lifecycle": manifest.lifecycle,
        "spec.zone": manifest.zone,
        "spec.address": manifest.address,
        "spec.provider.type": manifest.provider,
        "spec.platform.type": manifest.platform,
        "spec.services": _spec_value(manifest, "services"),
        "spec.capabilities": _spec_value(manifest, "capabilities"),
        "catalog.resource_id": manifest.catalog_resource_id,
        "catalog.display_name": manifest.display_name,
    }
    return [
        _error("missing-required-field", f"missing required field: {field}", manifest.path)
        for field, value in required.items()
        if value is None
    ]


def _validate_lifecycle(manifest: HostManifest, errors: list[dict[str, Any]]) -> None:
    lifecycle = manifest.lifecycle
    if not lifecycle:
        return
    if lifecycle not in KNOWN_LIFECYCLES:
        errors.append(_error("invalid-lifecycle", f"unknown lifecycle: {lifecycle}", manifest.path))
    if lifecycle != lifecycle.lower():
        errors.append(
            _error(
                "lifecycle-not-normalized",
                f"lifecycle must be lowercase: {lifecycle}",
                manifest.path,
            )
        )


def _validate_zone_and_address(manifest: HostManifest, errors: list[dict[str, Any]]) -> None:
    zone = manifest.zone
    if not zone:
        return
    if zone != zone.lower():
        errors.append(
            _error("zone-not-normalized", f"zone must be lowercase: {zone}", manifest.path)
        )
        return
    if zone in DEPRECATED_ZONES:
        if manifest.lifecycle == "active":
            errors.append(
                _error(
                    "deprecated-zone-active",
                    f"deprecated zone is not allowed for active host: {zone}",
                    manifest.path,
                )
            )
        return
    if zone not in ACTIVE_ZONES:
        errors.append(_error("invalid-zone", f"unknown active zone: {zone}", manifest.path))
        return

    if not manifest.address:
        return
    try:
        address = ip_address(manifest.address)
    except ValueError:
        errors.append(
            _error("invalid-address", f"invalid address: {manifest.address}", manifest.path)
        )
        return

    network = active_networks().get(zone, {})
    cidr = network.get("cidr")
    if not cidr:
        errors.append(
            _error("zone-cidr-missing", f"zone has no active CIDR: {zone}", manifest.path)
        )
        return
    if address not in ip_network(str(cidr)):
        errors.append(
            _error(
                "address-outside-zone-cidr",
                f"{manifest.address} is outside {zone} CIDR {cidr}",
                manifest.path,
            )
        )


def _validate_enum(
    field: str,
    value: str | None,
    allowed: tuple[str, ...],
    errors: list[dict[str, Any]],
    source: str,
) -> None:
    if not value:
        return
    if value != value.lower() or not is_normalized_slug(value):
        errors.append(
            _error(f"{field}-not-normalized", f"{field} must be normalized: {value}", source)
        )
        return
    if value not in allowed:
        errors.append(_error(f"unknown-{field}", f"unknown {field}: {value}", source))


def _validate_string_list(
    field: str,
    values: tuple[str, ...],
    errors: list[dict[str, Any]],
    source: str,
) -> None:
    for value in values:
        if not is_normalized_slug(value):
            errors.append(
                _error(
                    f"{field}-not-normalized",
                    f"{field} value must be normalized: {value}",
                    source,
                )
            )


def _zabbix_values(value: Any) -> set[str]:
    hits: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            hits.update(_zabbix_values(str(key)))
            hits.update(_zabbix_values(item))
    elif isinstance(value, list):
        for item in value:
            hits.update(_zabbix_values(item))
    elif isinstance(value, str):
        lowered = value.lower()
        for disallowed in ZABBIX_VALUES:
            if disallowed in lowered:
                hits.add(disallowed)
    return hits


def _names(manifests: list[HostManifest]) -> list[str | None]:
    return [manifest.name for manifest in manifests]


def _duplicate_errors(
    code: str,
    message: str,
    values: list[str | None],
) -> list[dict[str, Any]]:
    counts = Counter(value for value in values if value)
    return [
        _error(code, f"{message}: {value}", str(value))
        for value, count in sorted(counts.items())
        if count > 1
    ]


def _error(code: str, message: str, source: str) -> dict[str, Any]:
    return warning(code, message, severity="error", source=source)


def _spec_value(manifest: HostManifest, key: str) -> Any:
    spec = manifest.data.get("spec") if isinstance(manifest.data, dict) else None
    return spec.get(key) if isinstance(spec, dict) else None
