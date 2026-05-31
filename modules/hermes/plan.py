from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sync_plan(site: str | None, domain: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "kind": "sync-plan",
        "version": "v1",
        "site": site,
        "domain": domain,
        "created_at": now_iso(),
        "actions": actions,
    }


def apply_result(ok: bool, applied: int, failed: int = 0, *, dry_run: bool = False, details=None):
    return {
        "kind": "apply-result",
        "version": "v1",
        "ok": ok,
        "applied": applied,
        "failed": failed,
        "dry_run": dry_run,
        "details": details or [],
    }
