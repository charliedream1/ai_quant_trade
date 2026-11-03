"""Causal factor panels indexed by actual security dates and source windows."""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cache import FactorCache
from .config import factor_config, factor_set


@dataclass
class FactorPanel:
    values: pd.DataFrame
    definitions: dict[str, dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


@lru_cache(maxsize=1)
def implementation_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes() + Path(__file__).with_name("cache.py").read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()


def factor_value(rows: Sequence, definition: dict[str, Any]) -> float | None:
    window, operator = definition["window"], definition["operator"]
    if len(rows) < window + 1:
        return None
    try:
        close = np.asarray([float(row["close"]) for row in rows])
        if not np.isfinite(close).all() or (close <= 0).any():
            return None
        if operator == "momentum":
            value = close[-1] / close[-window - 1] - 1
        elif operator == "volatility":
            value = np.std(np.diff(close[-window - 1 :]) / close[-window - 1 : -1])
        elif operator == "volume_ratio":
            volume = np.asarray([float(row["volume"]) for row in rows[-window:]])
            if not np.isfinite(volume).all() or (volume < 0).any() or volume.mean() <= 0:
                return None
            value = volume[-definition["short"] :].mean() / volume.mean() - 1
        elif operator == "mean_distance":
            value = close[-1] / close[-window:].mean() - 1
        elif operator == "range_position":
            high = max(float(row["high"]) for row in rows[-window:])
            low = min(float(row["low"]) for row in rows[-window:])
            value = (close[-1] - low) / (high - low) if high > low else 0.5
        elif operator == "amount":
            amounts = [float(row.get("amount", float(row["close"]) * float(row["volume"]))) for row in rows[-window:]]
            if min(amounts) < 0:
                return None
            value = np.mean(amounts)
        elif operator == "intraday":
            opening = float(rows[-1]["open"])
            value = close[-1] / opening - 1 if opening > 0 else np.nan
        else:
            return None
        return float(value * definition["direction"]) if np.isfinite(value) else None
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def build_panel(
    history: Mapping[str, Sequence],
    name: str,
    cache: FactorCache | None = None,
    starts: dict[str, int] | None = None,
    definitions: dict[str, dict[str, Any]] | None = None,
) -> FactorPanel:
    definitions = definitions if definitions is not None else factor_set(name)
    pending = []
    for symbol, bars in sorted(history.items()):
        for index, bar in enumerate(bars):
            if index < (starts or {}).get(symbol, 0):
                continue
            day = str(bar.get("date") or bar.get("timestamp"))[:10]
            for key, definition in definitions.items():
                window = bars[max(0, index - definition["window"]) : index + 1]
                inputs = [
                    {
                        k: _input_value(row.get(k))
                        for k in ("close", "open", "high", "low", "volume", "amount", "data_source")
                    }
                    for row in window
                ]
                identity = _digest([implementation_digest(), definition, symbol, day, inputs])
                pending.append((day, symbol, key, identity, window, definition))
    cached = cache.get([row[3] for row in pending]) if cache else {}
    computed: dict[str, float | None] = {}
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for day, symbol, key, identity, window, definition in pending:
        if identity not in cached and identity not in computed:
            computed[identity] = factor_value(window, definition)
        value = cached[identity] if identity in cached else computed[identity]
        records.setdefault((day, symbol), {})[key] = value
    if cache:
        cache.put(computed)
    index = pd.MultiIndex.from_tuples(list(records), names=["date", "symbol"])
    values = pd.DataFrame(list(records.values()), index=index, columns=list(definitions), dtype=float).sort_index()
    return FactorPanel(
        values,
        definitions,
        {
            "set": name,
            "definition_digest": _digest(definitions),
            "implementation": implementation_digest(),
            "cache_hits": len(pending) - len(computed),
            "computed": len(computed),
            "persisted": bool(cache),
        },
    )


def _input_value(value: Any) -> Any:
    return str(value) if isinstance(value, (float, np.floating)) and not np.isfinite(value) else value


def preprocess(panel: FactorPanel, params: dict[str, Any]) -> FactorPanel:
    values = panel.values.astype(float).copy()
    floor = factor_config()["limits"]["numerical_floor"]
    grouped = values.groupby(level="date", sort=False)
    count = grouped.transform("count")
    lower = grouped.quantile(params["winsor_quantile"]).reindex(values.index, level="date")
    upper = grouped.quantile(1 - params["winsor_quantile"]).reindex(values.index, level="date")
    values = values.clip(lower=lower, upper=upper)
    grouped = values.groupby(level="date", sort=False)
    if params["method"] == "rank":
        values = (grouped.rank(method="average") - 1) / (count - 1)
    else:
        deviation = grouped.transform("std", ddof=0)
        centered = values - grouped.transform("mean")
        values = centered / deviation.where(deviation > floor, 1.0)
    values = values.where(count >= params["min_assets"])
    return FactorPanel(values, panel.definitions, {**panel.metadata, "preprocess": dict(params)})


class PanelBuilder:
    """Reuse causal raw values between batches; revisions rebuild the affected suffix."""

    def __init__(self, cache: FactorCache | None = None, contract: dict[str, Any] | None = None):
        self.cache = cache
        self.contract = contract or {}
        self.history: dict[str, list | tuple] = {}
        self.panel: FactorPanel | None = None
        self.name = ""

    def build(self, history: Mapping[str, Sequence], name: str) -> FactorPanel:
        if self.panel is None or self.name != name:
            panel = build_panel(history, name, self.cache, definitions=self.contract.get("definitions"))
        else:
            starts = {}
            for symbol, bars in history.items():
                old = self.history.get(symbol, ())
                starts[symbol] = next(
                    (i for i, (a, b) in enumerate(zip(old, bars, strict=False)) if a != b), min(len(old), len(bars))
                )
            addition = build_panel(history, name, self.cache, starts, self.contract.get("definitions"))
            retained = []
            for symbol, bars in history.items():
                prior_dates = {str(row.get("date") or row.get("timestamp"))[:10] for row in bars[: starts[symbol]]}
                index = self.panel.values.index
                retained.append(
                    self.panel.values.loc[
                        (index.get_level_values("symbol") == symbol) & index.get_level_values("date").isin(prior_dates)
                    ]
                )
            values = pd.concat([*retained, addition.values]).sort_index()
            panel = FactorPanel(
                values,
                addition.definitions,
                {**addition.metadata, "memory_hits": sum(len(item) for item in retained) * len(addition.definitions)},
            )
        self.history = {symbol: tuple(dict(row) for row in bars) for symbol, bars in history.items()}
        self.name, self.panel = name, panel
        return panel
