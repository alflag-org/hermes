from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from hermes.context import get_paths
from hermes.errors import ConfigError


SENSITIVE_KEY = re.compile(r"(password|secret|token|credential|api[_-]?key)", re.IGNORECASE)


def load_config(path: str | None = None) -> dict[str, Any]:
    selected = str(resolve_config_path(path))
    target = Path(selected)
    if not target.exists():
        return {}
    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Hermes config must be a mapping: {target}")
    _reject_inline_secrets(data, ())
    return data


def resolve_config_path(path: str | None = None) -> Path:
    selected = path or os.environ.get("HERMES_CONFIG")
    if selected is None:
        selected = str(Path(get_paths().etc) / "hermes.yml")
    return Path(selected)


def get_default_site(config: dict[str, Any], explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    defaults = config.get("defaults") or {}
    return config.get("site") or defaults.get("site")


def get_default_format(config: dict[str, Any], explicit: str | None = None) -> str:
    if explicit:
        return explicit
    defaults = config.get("defaults") or {}
    return str(defaults.get("format") or "text")


def _reject_inline_secrets(value: Any, path: tuple[str, ...]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if SENSITIVE_KEY.search(key_text) and not key_text.endswith("_env"):
                if child not in (None, ""):
                    joined = ".".join((*path, key_text))
                    raise ConfigError(
                        f"inline secret-like value is not allowed in config: {joined}"
                    )
            _reject_inline_secrets(child, (*path, key_text))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_inline_secrets(child, (*path, str(index)))
