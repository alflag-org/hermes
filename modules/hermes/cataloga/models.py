from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DesiredResource:
    id: str
    type: str
    name: str
    site: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
