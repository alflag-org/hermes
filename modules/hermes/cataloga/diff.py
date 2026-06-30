from __future__ import annotations

from typing import Any

from hermes.cataloga.project import expected_cataloga_resources
from hermes.manifest.load import HostManifest
from hermes.models import warning


def diff_cataloga_projection(
    manifests: list[HostManifest],
    catalog_data: Any,
) -> dict[str, Any]:
    expected = expected_cataloga_resources(manifests)
    actual_resources = _resource_list(catalog_data)
    actual = {
        str(resource.get("id")): resource
        for resource in actual_resources
        if resource.get("id") is not None
    }
    mismatches: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    wrong_id_actual_ids: set[str] = set()

    for expected_id, expected_resource in expected.items():
        actual_resource = actual.get(expected_id)
        if actual_resource is None:
            host_name = str(expected_resource["spec"]["daedalus_host"])
            wrong_id = _find_by_daedalus_host(actual_resources, host_name)
            if wrong_id is not None:
                wrong_id_actual_ids.add(str(wrong_id.get("id")))
                mismatches.append(
                    _mismatch(
                        "wrong-resource-id",
                        f"{host_name} resource id expected {expected_id} got {wrong_id.get('id')}",
                        host_name,
                    )
                )
                actual_resource = wrong_id
            else:
                mismatches.append(
                    _mismatch(
                        "missing-host-resource",
                        f"missing host resource: {expected_id}",
                        str(expected_resource["spec"]["daedalus_host"]),
                    )
                )
                continue
        _compare_resource(expected_resource, actual_resource, mismatches)

    for resource in actual_resources:
        resource_id = str(resource.get("id"))
        if resource_id in expected or resource_id in wrong_id_actual_ids:
            continue
        if _is_managed_host(resource):
            mismatches.append(
                _mismatch(
                    "extra-managed-host-resource",
                    f"extra managed host resource: {resource_id}",
                    resource_id,
                )
            )
        else:
            warnings.append(
                warning(
                    "extra-unmanaged-catalog-resource",
                    f"extra unmanaged Cataloga resource: {resource_id}",
                    source=resource_id,
                )
            )

    ok = not mismatches
    return {
        "kind": "cataloga-diff",
        "version": "v1",
        "ok": ok,
        "expected_resource_count": len(expected),
        "actual_resource_count": len(actual_resources),
        "mismatches": mismatches,
        "warnings": warnings,
        "_exit_code": 0 if ok else 2,
    }


def _compare_resource(
    expected: dict[str, Any],
    actual: dict[str, Any],
    mismatches: list[dict[str, Any]],
) -> None:
    source = str(expected["spec"]["daedalus_host"])
    expected_spec = expected["spec"]
    actual_spec = _spec(actual)
    checks = [
        ("wrong-resource-name", "resource name", expected.get("name"), actual.get("name")),
        (
            "wrong-description",
            "description",
            expected.get("description") or "",
            actual.get("description") or "",
        ),
        ("wrong-lifecycle", "lifecycle", expected.get("lifecycle"), _resource_lifecycle(actual)),
        (
            "wrong-daedalus-host",
            "daedalus_host",
            expected_spec.get("daedalus_host"),
            actual_spec.get("daedalus_host"),
        ),
        ("wrong-site-tag", "site tag", _tags(expected).get("site"), _tags(actual).get("site")),
        ("wrong-zone-tag", "zone tag", _tags(expected).get("zone"), _tags(actual).get("zone")),
        (
            "wrong-provider-field",
            "provider",
            expected_spec.get("provider"),
            actual_spec.get("provider"),
        ),
        (
            "wrong-platform-field",
            "platform",
            expected_spec.get("platform"),
            actual_spec.get("platform"),
        ),
        (
            "wrong-services-field",
            "services",
            expected_spec.get("services"),
            actual_spec.get("services") or [],
        ),
    ]
    for code, label, expected_value, actual_value in checks:
        if expected_value != actual_value:
            mismatches.append(
                _mismatch(
                    code,
                    f"{source} {label} expected {expected_value!r} got {actual_value!r}",
                    source,
                )
            )


def _resource_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        resources = data
    elif isinstance(data, dict):
        resources = data.get("resources") or data.get("items") or []
    else:
        resources = []
    return [resource for resource in resources if isinstance(resource, dict)]


def _find_by_daedalus_host(
    resources: list[dict[str, Any]],
    hostname: str,
) -> dict[str, Any] | None:
    for resource in resources:
        if _spec(resource).get("daedalus_host") == hostname:
            return resource
    return None


def _is_managed_host(resource: dict[str, Any]) -> bool:
    if str(resource.get("type") or "") != "host":
        return False
    tags = _tags(resource)
    spec = _spec(resource)
    return (
        tags.get("managed_by") == "daedalus"
        or bool(spec.get("daedalus_host"))
        or str(resource.get("id", "")).startswith("host-")
    )


def _resource_lifecycle(resource: dict[str, Any]) -> Any:
    return (
        resource.get("lifecycle")
        or _spec(resource).get("lifecycle")
        or _tags(resource).get("lifecycle")
    )


def _tags(resource: dict[str, Any]) -> dict[str, Any]:
    tags = resource.get("tags")
    return tags if isinstance(tags, dict) else {}


def _spec(resource: dict[str, Any]) -> dict[str, Any]:
    spec = resource.get("spec")
    return spec if isinstance(spec, dict) else {}


def _mismatch(code: str, message: str, source: str) -> dict[str, Any]:
    return warning(code, message, severity="error", source=source)
