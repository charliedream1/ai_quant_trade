"""Shared factor-monitor and graph-research statistics with deterministic ties."""

from collections.abc import Sequence

import numpy as np
import pandas as pd


def correlation(left: Sequence[float], right: Sequence[float], ranked: bool = False) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    x, y = np.asarray(left, dtype=float), np.asarray(right, dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        return None
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    if ranked:
        x, y = pd.Series(x).rank().to_numpy(), pd.Series(y).rank().to_numpy()
    x, y = x - x.mean(), y - y.mean()
    denominator = float(np.linalg.norm(x) * np.linalg.norm(y))
    return float(np.clip(x @ y / denominator, -1, 1)) if denominator > 0 else None


def information_ratio(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    array = np.asarray(values, dtype=float)
    if not np.isfinite(array).all() or np.ptp(array) == 0:
        return None
    deviation = float(array.std(ddof=0))
    return float(array.mean() / deviation) if deviation > 0 else None
