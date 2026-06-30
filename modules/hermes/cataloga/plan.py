from __future__ import annotations

from typing import Any

from hermes.cataloga.diff import diff_cataloga_projection
from hermes.cataloga.project import render_cataloga_dataset
from hermes.manifest.load import HostManifest


def cataloga_plan(manifests: list[HostManifest], catalog_data: Any) -> dict[str, Any]:
    dataset = render_cataloga_dataset(manifests)
    diff = diff_cataloga_projection(manifests, catalog_data)
    return {
        "kind": "cataloga-import-plan",
        "version": "v1",
        "review_required": True,
        "summary": {
            "expected_resources": len(dataset["resources"]),
            "mismatches": len(diff["mismatches"]),
            "warnings": len(diff["warnings"]),
        },
        "diff": {
            "ok": diff["ok"],
            "mismatches": diff["mismatches"],
            "warnings": diff["warnings"],
        },
        "import_dataset": dataset,
        "manual_review": [
            "Review resource ids before import.",
            "Review tags and lifecycle before passing this artifact to Cataloga tooling.",
            "Hermes did not call the Cataloga API or write to the Cataloga database.",
        ],
    }
