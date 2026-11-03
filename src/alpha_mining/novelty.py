"""Descriptive reference-factor overlap, distinct from a significance or novelty claim."""

import numpy as np
import pandas as pd

from src.strategy.factors.panel import build_panel
from src.strategy.factors.statistics import correlation


def reference_overlap(
    history: dict, scores: pd.DataFrame, days: list[str], definitions: dict, minimum_assets: int
) -> dict:
    # Only calculate evaluation dates; build_panel still reads each date's causal warm-up window.
    starts = {
        symbol: next((index for index, row in enumerate(rows) if row["date"] >= days[0]), len(rows))
        for symbol, rows in history.items()
    }
    reference = build_panel(history, "frozen_alpha_reference", starts=starts, definitions=definitions)
    groups = list(
        reference.values.loc[reference.values.index.get_level_values("date").isin(days)].groupby(level="date")
    )
    aligned = scores.reindex(index=days)
    result = {}
    for name in definitions:
        values = []
        for day, group in groups:
            assets = group.index.get_level_values("symbol")
            left = aligned.loc[day].reindex(assets)
            right = group[name].to_numpy()
            valid = np.isfinite(left.to_numpy()) & np.isfinite(right)
            if valid.sum() < minimum_assets:
                continue
            value = correlation(left.to_numpy()[valid].tolist(), right[valid].tolist(), ranked=True)
            if value is not None:
                values.append(value)
        result[name] = {"mean_daily_rank_correlation": float(np.mean(values)) if values else None, "dates": len(values)}
    return {
        "registered_factors": result,
        "scope": "frozen_registered_price_volume_reference_not_entire_strategy_library",
        "interpretation": "descriptive_overlap_not_proof_of_incremental_alpha",
    }
