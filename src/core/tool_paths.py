"""Resolve project tools without forcing a checkout-local installation."""

from __future__ import annotations

import os
from pathlib import Path

from .config import PROJECT_ROOT

TOOLS_ROOT_ENV = "ALL_IN_ONE_TOOLS_DIR"


def tools_root() -> Path:
    """Return the runtime tools directory selected by the process environment."""
    configured = os.environ.get(TOOLS_ROOT_ENV, "").strip()
    root = Path(configured).expanduser() if configured else PROJECT_ROOT / ".tools"
    return root.resolve()


def runtime_path(value: str | Path) -> Path:
    """Resolve a configured path, redirecting ``.tools`` to the selected tools root."""
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    parts = path.parts
    if parts and parts[0] == ".tools":
        return (tools_root() / Path(*parts[1:])).resolve()
    return (PROJECT_ROOT / path).resolve()
