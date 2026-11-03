"""Shared visual document policy is independent from the UI implementation."""

from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def graph_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/strategy_graph.yaml").read_text(encoding="utf-8"))
