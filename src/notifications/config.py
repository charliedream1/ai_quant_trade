"""Shared immutable defaults and trusted platform navigation."""

from copy import deepcopy
from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def _config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/ui/notifications.yaml").read_text(encoding="utf-8"))


def config() -> dict:
    return deepcopy(_config())


def target(source: str, identifier=None) -> dict:
    value = dict(config()["source_targets"][source])
    if source == "backtest" and identifier is not None:
        value["task_id"] = str(int(identifier))
    return value
