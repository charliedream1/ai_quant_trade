"""Matured-label cross sections, coverage and historical factor selection."""

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from .panel import FactorPanel
from .statistics import correlation, information_ratio


def forward_labels(history: Mapping[str, Sequence], horizon: int, as_of: str) -> pd.DataFrame:
    # A shared market calendar prevents suspension gaps from changing a horizon's meaning.
    dates = sorted({str(row.get("date") or row.get("timestamp"))[:10] for bars in history.values() for row in bars})
    positions = {day: index for index, day in enumerate(dates)}
    records = []
    for symbol, bars in sorted(history.items()):
        mapping = {str(row.get("date") or row.get("timestamp"))[:10]: row for row in bars}
        for day, row in mapping.items():
            end = positions[day] + horizon
            if end >= len(dates) or dates[end] > as_of or dates[end] not in mapping:
                continue
            close, future = float(row["close"]), float(mapping[dates[end]]["close"])
            if close > 0 and future > 0 and np.isfinite([close, future]).all():
                records.append({"date": day, "symbol": symbol, "target": future / close - 1, "label_end": dates[end]})
    return pd.DataFrame(records, columns=["date", "symbol", "target", "label_end"]).set_index(["date", "symbol"])


def _daily_metric(
    day: str, values: np.ndarray, targets: np.ndarray, ends: np.ndarray, population: int, params: dict[str, Any]
) -> dict[str, Any] | None:
    valid = np.isfinite(values) & np.isfinite(targets)
    count = int(valid.sum())
    if count < params["min_assets"]:
        return None
    coverage = count / population
    x, y = values[valid], targets[valid]
    ic = correlation(x.tolist(), y.tolist())
    rank_ic = correlation(x.tolist(), y.tolist(), ranked=True)
    if rank_ic is None or coverage < params["min_coverage"]:
        return None
    ordered = y[np.argsort(x, kind="stable")]
    group_count = min(params["groups"], max(count // params.get("min_group_assets", 1), 1))
    groups = np.array_split(ordered, group_count)
    returns = [float(group.mean()) for group in groups] if group_count >= 2 else []
    return {
        "date": day,
        "label_end": str(max(ends[valid])),
        "ic": ic,
        "rank_ic": rank_ic,
        "coverage": coverage,
        "asset_count": count,
        "group_returns": returns,
        "group_sizes": [len(group) for group in groups] if returns else [],
        "long_short_return": returns[-1] - returns[0] if returns else None,
    }


def analyze(panel: FactorPanel, history: dict[str, list | tuple], as_of: str, params: dict[str, Any]) -> dict[str, Any]:
    labels = forward_labels(history, params["horizon"], as_of)
    joined = panel.values.join(labels, how="inner")
    dates = sorted(set(joined.index.get_level_values("date")))[-params["lookback"] :]
    joined = joined.loc[joined.index.get_level_values("date").isin(dates)]
    columns = list(panel.values.columns)
    populations = panel.values.groupby(level="date").size().to_dict()
    sections = [
        (
            day,
            group[columns].to_numpy(dtype=float),
            group["target"].to_numpy(dtype=float),
            group["label_end"].to_numpy(),
        )
        for day, group in joined.groupby(level="date", sort=True)
    ]
    metrics, histories = {}, {}
    for position, key in enumerate(columns):
        daily = []
        for day, matrix, targets, ends in sections:
            metric = _daily_metric(day, matrix[:, position], targets, ends, populations[day], params)
            if metric is not None:
                daily.append(metric)
        rank_values = [row["rank_ic"] for row in daily]
        metrics[key] = {
            "samples": len(daily),
            "rank_ic_mean": float(np.mean(rank_values)) if rank_values else None,
            "ic_mean": float(np.mean([row["ic"] for row in daily])) if daily else None,
            "icir": information_ratio(rank_values),
            "coverage": float(np.mean([row["coverage"] for row in daily])) if daily else None,
            "long_short_return": float(
                np.mean([row["long_short_return"] for row in daily if row["long_short_return"] is not None])
            )
            if any(row["long_short_return"] is not None for row in daily)
            else None,
            "label_end": max((row["label_end"] for row in daily), default=""),
        }
        histories[key] = daily
    return {
        "as_of": as_of,
        "params": dict(params),
        "metrics": metrics,
        "history": histories,
        "label_end": max((str(row["label_end"]) for row in metrics.values()), default=""),
    }


def select(panel: FactorPanel, history: dict[str, list | tuple], as_of: str, params: dict[str, Any]) -> FactorPanel:
    report = analyze(panel, history, as_of, params)
    metrics = report["metrics"]
    ordered = sorted(metrics, key=lambda k: (-(metrics[k]["rank_ic_mean"] or 0), k))
    selected: list[str] = []
    excluded = {}
    correlations = []
    cutoff_dates = sorted(set(panel.values.index.get_level_values("date")))[-params["lookback"] :]
    recent = panel.values.loc[panel.values.index.get_level_values("date").isin(cutoff_dates)]
    columns = {key: position for position, key in enumerate(panel.values.columns)}
    sections = [group.to_numpy(dtype=float) for _, group in recent.groupby(level="date", sort=True)]
    for key in ordered:
        metric = metrics[key]
        if metric["samples"] < params["min_dates"]:
            excluded[key] = "insufficient_matured_dates"
            continue
        if metric["rank_ic_mean"] < params["min_rank_ic"]:
            excluded[key] = "rank_ic_below_threshold"
            continue
        duplicate = None
        for other in selected:
            daily = []
            for matrix in sections:
                left, right = matrix[:, columns[key]], matrix[:, columns[other]]
                valid = np.isfinite(left) & np.isfinite(right)
                value = correlation(left[valid].tolist(), right[valid].tolist(), ranked=True)
                if value is not None and int(valid.sum()) >= params["min_assets"]:
                    daily.append(value)
            value = float(np.mean(daily)) if daily else None
            correlations.append({"left": key, "right": other, "rank_correlation": value, "samples": len(daily)})
            if value is not None and abs(value) >= params["max_correlation"]:
                duplicate = other
                break
        if duplicate:
            excluded[key] = "correlated_with:" + duplicate
        else:
            selected.append(key)
    report.update(selected=selected, excluded=excluded, correlation=correlations)
    return FactorPanel(
        panel.values[selected].copy(),
        {k: panel.definitions[k] for k in selected},
        {**panel.metadata, "research": report, "selection": True},
    )
