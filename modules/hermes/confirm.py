from __future__ import annotations

from hermes.errors import UsageError


def require_apply(apply: bool, operation: str) -> None:
    if not apply:
        raise UsageError(f"{operation} is dry-run by default; pass --apply to mutate state")
