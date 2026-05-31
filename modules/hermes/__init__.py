"""Hermes infrastructure operation gateway."""

from __future__ import annotations

from pathlib import Path


def version() -> str:
    release_root = Path(__file__).resolve().parents[2]
    version_file = release_root / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


__all__ = ["version"]
