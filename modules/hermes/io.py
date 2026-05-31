from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from hermes.errors import UsageError


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def load_data(path: str | Path) -> Any:
    target = Path(path)
    if not target.exists():
        raise UsageError(f"file not found: {target}")
    text = target.read_text(encoding="utf-8")
    if target.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text) or {}


def dump_data(data: Any, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if fmt == "yaml":
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    raise UsageError(f"unsupported machine format: {fmt}")


def write_data(path: str | Path, data: Any, fmt: str | None = None) -> None:
    target = Path(path)
    selected = fmt or ("json" if target.suffix.lower() == ".json" else "yaml")
    write_text(target, dump_data(data, selected))
