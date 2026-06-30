from __future__ import annotations

from typing import Any

from hermes.atlas.project import render_atlas_host
from hermes.manifest.load import HostManifest
from hermes.models import warning


def diff_atlas_host(manifest: HostManifest, actual_host: Any) -> dict[str, Any]:
    expected = render_atlas_host(manifest)
    actual = actual_host if isinstance(actual_host, dict) else {}
    mismatches: list[dict[str, Any]] = []

    for field in ("name", "site", "zone", "role", "runtime_kind"):
        if expected.get(field) != actual.get(field):
            mismatches.append(
                _mismatch(
                    f"wrong-{field.replace('_', '-')}",
                    f"{field} expected {expected.get(field)!r} got {actual.get(field)!r}",
                    str(manifest.name),
                )
            )

    expected_tags = set(str(tag) for tag in expected.get("tags", []))
    actual_tags = (
        {str(tag) for tag in actual.get("tags", []) if tag is not None}
        if isinstance(actual.get("tags"), list)
        else set()
    )
    for tag in sorted(expected_tags - actual_tags):
        mismatches.append(_mismatch("missing-tag", f"missing tag: {tag}", str(manifest.name)))
    for tag in sorted(actual_tags - expected_tags):
        mismatches.append(_mismatch("extra-tag", f"extra tag: {tag}", str(manifest.name)))

    ok = not mismatches
    return {
        "kind": "atlas-host-diff",
        "version": "v1",
        "ok": ok,
        "expected": expected,
        "actual": actual,
        "mismatches": mismatches,
        "warnings": [],
        "_exit_code": 0 if ok else 2,
    }


def _mismatch(code: str, message: str, source: str) -> dict[str, Any]:
    return warning(code, message, severity="error", source=source)
