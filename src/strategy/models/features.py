"""Point-in-time price/volume features and matured forward-return labels."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.strategy.factors.features import feature_panel
from src.strategy.factors.panel import PanelBuilder

from .contracts import FeatureRow


def build_panel(
    history: dict[str, list[dict[str, Any]]], config: dict[str, Any], builder: PanelBuilder | None = None
) -> list[FeatureRow]:
    if config.get("feature_set"):
        return feature_panel(history, config, builder)
    rows: list[FeatureRow] = []
    for symbol, bars in history.items():
        rows.extend(_symbol_features(symbol, bars, config))
    if config["demean_target"]:
        groups: dict[str, list[FeatureRow]] = {}
        for row in rows:
            if row.target is not None:
                groups.setdefault(row.date, []).append(row)
        for group in groups.values():
            mean = sum(float(row.target) for row in group if row.target is not None) / len(group)
            for row in group:
                if row.target is not None:
                    row.target -= mean
    return sorted(rows, key=lambda item: (item.date, item.symbol))


def _symbol_features(symbol: str, bars: list[dict[str, Any]], config: dict[str, Any]) -> list[FeatureRow]:
    lags = [int(value) for value in config["lag_windows"]]
    short = int(config["short_window"])
    long = int(config["long_window"])
    vol = int(config["volatility_window"])
    volume_window = int(config["volume_window"])
    horizon = int(config["horizon"])
    warmup = max(*lags, short, long, vol, volume_window)
    closes = np.asarray([float(bar["close"]) for bar in bars])
    volumes = np.asarray([float(bar.get("volume") or 0) for bar in bars])
    rows = []
    for index in range(warmup, len(bars)):
        close = closes[index]
        if close <= 0 or np.any(closes[index - warmup : index + 1] <= 0):
            continue
        bar = bars[index]
        daily = np.diff(closes[index - vol : index + 1]) / closes[index - vol : index]
        mean_volume = float(volumes[index - volume_window + 1 : index + 1].mean())
        values = [float(close / closes[index - lag] - 1) for lag in lags]
        values.extend(
            [
                float(np.std(daily)),
                float(close / closes[index - short + 1 : index + 1].mean() - 1),
                float(close / closes[index - long + 1 : index + 1].mean() - 1),
                (float(bar["high"]) - float(bar["low"])) / close,
                close / float(bar["open"]) - 1 if float(bar["open"]) > 0 else 0.0,
                float(volumes[index] / mean_volume - 1) if mean_volume > 0 else 0.0,
            ]
        )
        if not np.isfinite(values).all():
            continue
        future_index = index + horizon
        matured = future_index < len(bars)
        rows.append(
            FeatureRow(
                symbol=symbol,
                date=str(bar["timestamp"])[:10],
                values=values,
                target=float(closes[future_index] / close - 1) if matured else None,
                target_date=str(bars[future_index]["timestamp"])[:10] if matured else "",
            )
        )
    return rows


def time_split(rows: list[FeatureRow], config: dict[str, Any]) -> tuple[list[FeatureRow], list[FeatureRow]]:
    matured = [row for row in rows if row.target is not None]
    dates = sorted({row.date for row in matured})[-int(config["train_window"]) :]
    if len(dates) < int(config["min_train_dates"]):
        return [], []
    validation_size = max(1, int(len(dates) * float(config["validation_fraction"])))
    validation_start = dates[-validation_size]
    train = [row for row in matured if row.date in dates and row.target_date < validation_start]
    validation = [row for row in matured if row.date >= validation_start]
    if len(train) < int(config["min_train_samples"]):
        return [], []
    return train, validation
