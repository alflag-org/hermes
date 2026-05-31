#!/usr/bin/env python3
"""Atlas command entrypoint for Hermes."""

from __future__ import annotations

import sys
from pathlib import Path


RELEASE_ROOT = Path(__file__).resolve().parents[1]
MODULES = RELEASE_ROOT / "modules"
MODULES_PATH = str(MODULES)
sys.path = [path for path in sys.path if path != MODULES_PATH]
sys.path.insert(0, MODULES_PATH)

from hermes.cli import main


if __name__ == "__main__":
    main()
