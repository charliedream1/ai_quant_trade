"""Matured IC for recorded research strengths; allocation weights are never treated as predictions."""

import pandas as pd

from src.alpha_mining.factors import market_panel
from src.alpha_mining.research import factor_statistics

from .config import settings


def research_metrics(records: list[dict], history: dict, end_date: str) -> dict:
    cfg = settings()
    grouped: dict[tuple[str, int], list[dict]] = {}
    for row in records:
        grouped.setdefault((row["node"], row["horizon"]), []).append(row)
    result = {}
    for (node, horizon), rows in grouped.items():
        scores = pd.DataFrame([{**row, "value": float(row["score"])} for row in rows]).pivot_table(
            index="date", columns="symbol", values="value", aggfunc="last"
        )
        bars = {s: [row for row in values if row["date"] <= end_date] for s, values in history.items()}
        panel = market_panel(bars)
        scores = scores.reindex(index=panel["open"].index, columns=panel["open"].columns)
        days = [day for day in panel["open"].index if rows[0]["date"] <= day <= end_date]
        limits = cfg["limits"]
        policy = {
            "horizon": horizon,
            "min_assets": limits["min_ic_assets"],
            "min_coverage": limits["ic_min_coverage"],
            "min_test_dates": limits["min_ic_dates"],
            "block_sessions": max(horizon, limits["ic_block_sessions"]),
            "bootstrap_samples": limits["ic_bootstrap_samples"],
            "seed": cfg["defaults"]["seed"],
            "significance": limits["ic_significance"],
        }
        if days:
            result[node] = factor_statistics(scores, panel["open"], days, policy)
    return {
        "nodes": result,
        "scope": "recorded_relative_research_strength_next_open_labels_not_target_weights",
        "status": "evaluated"
        if any(row["inference"]["status"] == "evaluated" for row in result.values())
        else "insufficient_or_not_applicable",
    }
