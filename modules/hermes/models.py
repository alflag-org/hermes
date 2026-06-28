from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class WarningItem:
    code: str
    message: str
    severity: str = "warning"
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def warning(code: str, message: str, *, severity: str = "warning", source: str | None = None) -> dict[str, Any]:
    return WarningItem(code=code, message=message, severity=severity, source=source).to_dict()
