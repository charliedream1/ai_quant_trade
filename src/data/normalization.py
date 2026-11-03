"""Shared numeric normalization without importing the full data provider."""

import math
from typing import Any


def _number(value: Any, default: float = 0.0) -> float:
    if value in (None, "", "-"):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(result) or math.isinf(result) else result


def _empty_rows() -> list[dict[str, Any]]:
    return []


def _empty_boards() -> dict[str, Any]:
    return {"industry": None, "concepts": [], "indices": []}
