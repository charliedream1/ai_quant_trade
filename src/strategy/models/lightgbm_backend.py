"""Optional CPU LightGBM regression backend."""

from __future__ import annotations

from typing import Any

import pandas as pd
from lightgbm import LGBMRegressor


class LightGBMModel:
    def __init__(self, params: dict[str, Any]) -> None:
        self.model = LGBMRegressor(**params)

    def fit(self, features: Any, targets: Any) -> LightGBMModel:
        self.model.fit(pd.DataFrame(features), targets)
        return self

    def predict(self, features: Any) -> Any:
        return self.model.predict(pd.DataFrame(features))


def build_model(params: dict[str, Any]) -> LightGBMModel:
    return LightGBMModel(params)
