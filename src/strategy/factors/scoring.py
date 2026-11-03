"""Explicit factor weights and rank scores, distinct from capital allocation."""

from typing import Any

import numpy as np

from src.strategy.composition.contracts import Observation

from .config import factor_config, factor_error
from .panel import FactorPanel


def capped_weights(raw: dict[str, float], cap: float) -> dict[str, float]:
    if not raw:
        return {}
    if cap * len(raw) < 1 - factor_config()["limits"]["numerical_floor"]:
        raise factor_error("invalid", "max_factor_weight is infeasible for selected factors")
    remaining = dict(raw)
    result = {}
    budget = 1.0
    while remaining:
        total = sum(remaining.values())
        proposal = {
            key: budget * value / total if total > 0 else budget / len(remaining) for key, value in remaining.items()
        }
        limited = [key for key, weight in proposal.items() if weight > cap]
        if not limited:
            result.update(proposal)
            break
        for key in limited:
            result[key] = cap
            budget -= cap
            remaining.pop(key)
    return result


def score(panel: FactorPanel, symbols: list[str], as_of: str, params: dict[str, Any]) -> dict[str, Observation]:
    research = panel.metadata.get("research", {})
    columns = list(panel.values.columns)
    metrics = research.get("metrics", {})
    if params["weighting"] == "icir" and not research:
        raise factor_error("invalid", "ICIR requires a research selection node")
    raw = dict.fromkeys(columns, 1.0)
    if params["weighting"] == "icir" and columns:
        floor = factor_config()["limits"]["numerical_floor"]
        icir = {key: max(0.0, metrics[key].get("icir") or 0) for key in columns}
        total = sum(icir.values())
        if total <= floor:
            raw = {}  # Degenerate ICIR cannot be advertised as a dynamic estimate.
        else:
            raw = {
                key: (1 - params["shrinkage"]) * value / total + params["shrinkage"] / len(columns)
                for key, value in icir.items()
            }
    weights = capped_weights(raw, params["max_factor_weight"])
    current = (
        panel.values.loc[as_of]
        if as_of in panel.values.index.get_level_values("date")
        else panel.values.iloc[:0].droplevel("date")
    )
    ranks = current.rank(method="average", pct=False)
    for key in columns:
        count = int(current[key].count())
        ranks[key] = (ranks[key] - 1) / (count - 1) if count > 1 else ranks[key] * 0 + 0.5
    output = {}
    warming = bool(research) and any(row["samples"] < research["params"]["min_dates"] for row in metrics.values())
    for symbol in sorted(symbols):
        values = {
            key: float(current.loc[symbol, key])
            for key in columns
            if symbol in current.index and np.isfinite(current.loc[symbol, key])
        }
        available = {key: weights[key] for key in values if key in weights}
        coverage = len(available) / len(columns) if columns else 0.0
        effective = {}
        status, reason, value = "unknown", "factor_missing", None
        if not columns or not weights:
            status, reason = ("unknown", "factor_warming") if warming else ("reject", "factor_rejected")
        elif (
            len(available) >= params["minimum_factors"]
            and coverage >= params["min_coverage"]
            and sum(available.values()) > 0
            and len(available) * params["max_factor_weight"] >= 1 - factor_config()["limits"]["numerical_floor"]
        ):
            effective = capped_weights(available, params["max_factor_weight"])
            value = sum(weight * float(ranks.loc[symbol, key]) for key, weight in effective.items())
            status, reason = "pass", "factor_pass"
        output[symbol] = Observation(
            symbol,
            value,
            status,
            reason,
            {
                "factors": values,
                "factor_weights": weights,
                "effective_weights": effective,
                "coverage": coverage,
                "factor_set": panel.metadata["set"],
                "definition_digest": panel.metadata["definition_digest"],
                "weighting": params["weighting"],
                "research_label_end": research.get("label_end", ""),
            },
            horizon=research.get("params", {}).get("horizon", 1),
            family="factor",
        )
    return output
