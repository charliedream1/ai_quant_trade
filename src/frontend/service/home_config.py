"""Typed access to homepage presentation configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache(maxsize=1)
def home_config() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "egs" / "config" / "ui" / "home_dashboard.yaml"
    return dict(yaml.safe_load(path.read_text(encoding="utf-8")))


def limit(name: str) -> int:
    return int(home_config()["limits"][name])


def color(name: str) -> str:
    return str(home_config()["colors"][name])


def label(name: str) -> str:
    return str(home_config()["labels"][name])
