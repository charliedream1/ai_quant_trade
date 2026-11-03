"""Named factor feature sets, using the same causal panels as graph research."""

from typing import Any

import numpy as np

from src.strategy.models.contracts import FeatureRow

from .config import factor_config
from .panel import PanelBuilder, build_panel, preprocess
from .research import forward_labels


def feature_panel(
    history: dict[str, list[dict[str, Any]]], params: dict[str, Any], builder: PanelBuilder | None = None
) -> list[FeatureRow]:
    panel = builder.build(history, params["feature_set"]) if builder else build_panel(history, params["feature_set"])
    settings = {**factor_config()["preprocess"], "method": params["feature_preprocess"]}
    if builder and builder.contract:
        settings = {**builder.contract["preprocess"], "method": params["feature_preprocess"]}
    processed = preprocess(panel, settings)
    dates = processed.values.index.get_level_values("date")
    as_of = max(dates, default="")
    labels = forward_labels(history, params["horizon"], as_of)
    data = processed.values.join(labels, how="left")
    if params["demean_target"]:
        data["target"] -= data.groupby(level="date")["target"].transform("mean")
    output = []
    for (day, symbol), row in data.iterrows():
        values = [float(row[key]) for key in processed.values.columns]
        if not np.isfinite(values).all():
            continue
        target = float(row["target"]) if np.isfinite(row["target"]) else None
        output.append(
            FeatureRow(str(symbol), str(day), values, target, str(row["label_end"]) if target is not None else "")
        )
    return output
