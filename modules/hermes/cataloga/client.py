from __future__ import annotations

from typing import Any

from hermes.cataloga.dataset import normalize_dataset, validate_dataset
from hermes.errors import UsageError
from hermes.io import load_data


def load_dataset_from_config(config: dict[str, Any]) -> dict[str, Any]:
    cataloga = config.get("cataloga") or {}
    if cataloga.get("mode", "file") != "file":
        raise UsageError("only file-based Cataloga mode is implemented")
    dataset = cataloga.get("dataset")
    if not dataset:
        raise UsageError("cataloga.dataset is required for file-based export")
    return normalize_dataset(load_data(dataset))


def import_plan(path: str) -> dict[str, Any]:
    data = normalize_dataset(load_data(path))
    validation = validate_dataset(data)
    return {
        "kind": "cataloga-import-plan",
        "version": "v1",
        "ok": validation["ok"],
        "resource_count": len(data["resources"]),
        "actions": [
            {"action": "upsert-resource", "id": resource["id"], "type": resource.get("type")}
            for resource in data["resources"]
        ],
        "errors": validation["errors"],
    }
