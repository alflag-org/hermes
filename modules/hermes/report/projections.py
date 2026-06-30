from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes.atlas.diff import diff_atlas_host
from hermes.cataloga.diff import diff_cataloga_projection
from hermes.daedalus.diff import diff_daedalus_projection
from hermes.manifest.load import HostManifest
from hermes.manifest.validate import validate_host_manifests


def projection_report(
    manifests: list[HostManifest],
    *,
    inventory: str | Path | None = None,
    catalog_data: Any | None = None,
    atlas_manifest: HostManifest | None = None,
    atlas_host_data: Any | None = None,
) -> dict[str, Any]:
    manifest_status = validate_host_manifests(manifests)
    daedalus_status = diff_daedalus_projection(manifests, inventory) if inventory else None
    cataloga_status = (
        diff_cataloga_projection(manifests, catalog_data) if catalog_data is not None else None
    )
    atlas_status = (
        diff_atlas_host(atlas_manifest, atlas_host_data)
        if atlas_manifest and atlas_host_data is not None
        else None
    )

    statuses = [
        item
        for item in (manifest_status, daedalus_status, cataloga_status, atlas_status)
        if item is not None
    ]
    drift_count = sum(len(item.get("mismatches", item.get("errors", []))) for item in statuses)
    return {
        "kind": "projection-report",
        "version": "v1",
        "ok": all(item.get("ok", True) for item in statuses),
        "manifest_status": _status_summary(manifest_status, "errors"),
        "daedalus_projection_status": _status_summary(daedalus_status, "mismatches"),
        "cataloga_projection_status": _status_summary(cataloga_status, "mismatches"),
        "atlas_projection_status": _status_summary(atlas_status, "mismatches"),
        "drift_summary": {
            "mismatches": drift_count,
            "warnings": sum(len(item.get("warnings", [])) for item in statuses),
        },
        "recommended_next_review_actions": _recommended_actions(
            daedalus_status,
            cataloga_status,
            atlas_status,
        ),
    }


def _status_summary(status: dict[str, Any] | None, problem_key: str) -> dict[str, Any]:
    if status is None:
        return {"provided": False, "ok": None, "problems": 0, "warnings": 0}
    return {
        "provided": True,
        "ok": status.get("ok", False),
        "problems": len(status.get(problem_key, [])),
        "warnings": len(status.get("warnings", [])),
    }


def _recommended_actions(
    daedalus_status: dict[str, Any] | None,
    cataloga_status: dict[str, Any] | None,
    atlas_status: dict[str, Any] | None,
) -> list[str]:
    actions = ["Review manifest validation errors first; projections are derived from manifests."]
    if daedalus_status and not daedalus_status.get("ok"):
        actions.append("Review Daedalus inventory drift before running Ansible elsewhere.")
    if cataloga_status and not cataloga_status.get("ok"):
        actions.append("Generate a Cataloga plan and review it before import.")
    if atlas_status and not atlas_status.get("ok"):
        actions.append("Review Atlas host context drift on the target host.")
    if len(actions) == 1:
        actions.append("No projection drift was detected in the supplied files.")
    return actions
