"""Chronological split contracts and next-open matured factor labels."""

from typing import Any

import numpy as np
import pandas as pd

from src.strategy.factors.statistics import correlation

from .config import invalid
from .statistics import block_test


def split_dates(days: list[str], policy: dict[str, Any]) -> dict[str, list[str]]:
    ordered = sorted(set(days))
    train = int(len(ordered) * policy["train_fraction"])
    validation = int(len(ordered) * (policy["train_fraction"] + policy["validation_fraction"]))
    gap = policy["embargo_sessions"]
    splits = {
        "train": ordered[:train],
        "validation": ordered[train + gap : validation],
        "holdout": ordered[validation + gap :],
    }
    if len(splits["train"]) < policy["min_train_dates"] or any(
        len(splits[key]) < policy["min_test_dates"] + policy["horizon"] + 1 for key in ("validation", "holdout")
    ):
        raise invalid("真实日期不足以进行训练、隔离、验证和留出切分；请导入更长历史，不会降低门槛")
    return splits


def label_panel(opens: pd.DataFrame, horizon: int, days: list[str]) -> pd.DataFrame:
    entry, exit_ = opens.shift(-1), opens.shift(-(horizon + 1))
    labels = exit_ / entry - 1
    end_positions = pd.Series(opens.index, index=opens.index).shift(-(horizon + 1))
    allowed = end_positions.notna() & end_positions.le(days[-1])
    return labels.loc[labels.index.isin(days) & allowed].replace([np.inf, -np.inf], np.nan)


def factor_statistics(scores: pd.DataFrame, opens: pd.DataFrame, days: list[str], policy: dict) -> dict:
    labels = label_panel(opens, policy["horizon"], days)
    daily = []
    for day, targets in labels.iterrows():
        values = scores.loc[day]
        selected = values.notna() & targets.notna()
        count = int(selected.sum())
        coverage = count / len(scores.columns)
        if count < policy["min_assets"] or coverage < policy["min_coverage"]:
            continue
        ic = correlation(values[selected].tolist(), targets[selected].tolist())
        rank_ic = correlation(values[selected].tolist(), targets[selected].tolist(), ranked=True)
        if rank_ic is not None:
            daily.append({"date": day, "ic": ic, "rank_ic": rank_ic, "coverage": coverage, "assets": count})
    inference = block_test([row["rank_ic"] for row in daily], policy)
    return {
        "daily": daily,
        "inference": inference,
        "mean_ic": float(np.mean([row["ic"] for row in daily])) if daily else None,
        "mean_rank_ic": inference["mean"],
        "mean_coverage": float(np.mean([row["coverage"] for row in daily])) if daily else 0.0,
        "label": "next_open_to_horizon_next_open",
        "horizon": policy["horizon"],
    }
