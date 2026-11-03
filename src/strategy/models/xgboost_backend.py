"""CPU XGBoost regression backend."""

from __future__ import annotations

from typing import Any

from xgboost import XGBRegressor


def build_model(params: dict[str, Any]) -> Any:
    return XGBRegressor(**params)
