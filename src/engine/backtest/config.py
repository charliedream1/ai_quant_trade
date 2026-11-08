"""Shared backtest configuration, independent of frontend and providers."""

from functools import lru_cache
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def backtest_config() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/strategies/backtest.yaml").read_text(encoding="utf-8"))
