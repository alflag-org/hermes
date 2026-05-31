from __future__ import annotations

from typing import Any

from hermes.errors import UsageError


def normalize_dataset(data: Any) -> dict[str, Any]:
    if data is None:
        data = {}
    if isinstance(data, list):
        resources = data
    elif isinstance(data, dict):
        resources = data.get("resources")
        if resources is None and "items" in data:
            resources = data["items"]
        if resources is None:
            resources = _mapping_to_resources(data)
    else:
        raise UsageError("dataset must be a mapping or list")

    normalized = [_normalize_resource(resource) for resource in resources or []]
    normalized.sort(key=lambda item: (item.get("site") or "", item.get("type") or "", item["id"]))
    return {"kind": "desired-dataset", "version": "v1", "resources": normalized}


def validate_dataset(data: Any) -> dict[str, Any]:
    normalized = normalize_dataset(data)
    errors: list[str] = []
    seen: set[str] = set()
    for index, resource in enumerate(normalized["resources"]):
        resource_id = resource.get("id")
        if not resource_id:
            errors.append(f"resources[{index}] missing id")
        elif resource_id in seen:
            errors.append(f"duplicate resource id: {resource_id}")
        seen.add(resource_id)
        if not resource.get("type"):
            errors.append(f"resources[{index}] missing type")
    return {
        "kind": "desired-dataset-validation",
        "version": "v1",
        "ok": not errors,
        "resource_count": len(normalized["resources"]),
        "errors": errors,
    }


def _mapping_to_resources(data: dict[str, Any]) -> list[Any]:
    if all(isinstance(value, dict) for value in data.values()):
        return [dict(value, id=key) if "id" not in value else value for key, value in data.items()]
    return []


def _normalize_resource(resource: Any) -> dict[str, Any]:
    if not isinstance(resource, dict):
        raise UsageError(f"resource must be a mapping: {resource!r}")
    result = dict(resource)
    identifier = result.get("id") or result.get("name") or result.get("hostname")
    if not identifier:
        raise UsageError(f"resource missing id/name: {resource!r}")
    result["id"] = str(identifier)
    if "name" not in result:
        result["name"] = result["id"]
    if "type" not in result:
        result["type"] = str(result.get("kind") or "host")
    if "site" in result and result["site"] is not None:
        result["site"] = str(result["site"])
    return result
