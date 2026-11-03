"""Presentation diagnostics derived from the shared causal factor research engine."""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

import pandas as pd

from src.strategy.factors.cache import FactorCache
from src.strategy.factors.panel import FactorPanel, build_panel
from src.strategy.factors.research import analyze
from src.strategy.factors.statistics import correlation, information_ratio

from .qlib_signal import apply_qlib


def _active(universe: dict[str, Any], day: str, symbol: str) -> bool:
    rows = universe.get("memberships") or []
    return not rows or any(
        row["symbol"] == symbol and row["valid_from"] <= day <= (row.get("valid_to") or "9999-12-31") for row in rows
    )


def monitor_analysis(
    history: dict[str, Any],
    quotes: dict[str, Any],
    universe: dict[str, Any],
    config: dict[str, Any],
    backend: str,
    cache: FactorCache | None = None,
) -> dict[str, Any]:
    panel = build_panel(history, config["factor_set"], cache)
    dates = sorted(set(panel.values.index.get_level_values("date")))
    index = pd.MultiIndex.from_tuples(
        [(day, symbol) for day in dates for symbol in universe["symbols"] if _active(universe, day, symbol)],
        names=["date", "symbol"],
    )
    panel = FactorPanel(panel.values.reindex(index), panel.definitions, panel.metadata)
    latest = panel.values.xs(dates[-1], level="date") if dates else pd.DataFrame(columns=panel.definitions)
    result: dict[str, Any] = {
        key: []
        for key in (
            "metrics",
            "ic_history",
            "quantile_returns",
            "quantile_history",
            "ic_decay",
            "style_exposure",
            "snapshots",
            "rolling",
            "stability",
        )
    }
    horizons = sorted({config["default_horizon_days"], *config["diagnostic_horizons"]})
    reports = {}
    for horizon in horizons:
        params = {
            "horizon": horizon,
            "lookback": len(dates),
            "min_assets": config["min_assets"],
            "min_coverage": 0.0,
            "groups": config["groups"],
            "min_group_assets": config["min_group_assets"],
        }
        reports[horizon] = analyze(panel, history, universe["as_of"], params)
    if backend == "qlib":
        apply_qlib(panel.values, history, universe["as_of"], list(reports.values()), config)
    for horizon, report in reports.items():
        for key, stats in report["metrics"].items():
            result["ic_decay"].append(
                {
                    "factor_key": key,
                    "factor_name": panel.definitions[key]["label"],
                    "horizon_days": horizon,
                    "rank_ic": stats["rank_ic_mean"],
                    "rank_ic_mean": stats["rank_ic_mean"],
                    "sample_size": stats["samples"],
                }
            )
        if horizon == config["default_horizon_days"]:
            _primary(result, report, panel, latest, quotes, universe, config)
    result["correlation"] = {
        "factors": [row["label"] for row in panel.definitions.values()],
        "matrix": latest.corr(min_periods=config["min_assets"])
        .astype(object)
        .where(lambda frame: frame.notna(), None)
        .to_numpy()
        .tolist()
        if not latest.empty
        else [],
    }
    result["panel_metadata"] = panel.metadata
    result["backend"] = backend
    result["limitations"] = [
        "历史行业与市值未完整提供，当前未做行业/市值中性化；风格图为价量代理。",
        "分组收益未计交易费用，排序换手不是资金换手，未评估真实容量。",
        "交易日历来自输入行情日期并集；未到期标签不参与评估，重叠标签不视为独立样本。",
    ]
    return result


def _primary(output, report, panel, latest, quotes, universe, config) -> None:
    for key, definition in panel.definitions.items():
        base = {"factor_key": key, "factor_name": definition["label"]}
        daily = report["history"][key]
        valid = latest[key].dropna().sort_values(ascending=False) if not latest.empty else pd.Series(dtype=float)
        metric = _metric(base, daily, report["metrics"][key], panel, latest, valid, config)
        output["metrics"].append(metric)
        _history_rows(output, base, daily, report["params"]["horizon"])
        _snapshot_rows(output, base, valid, quotes, metric["snapshot_date"])
        _exposure_rows(output, base, panel, latest)
        _windows(output, base, daily, config)


def _metric(base, daily, stats, panel, latest, valid, config) -> dict[str, Any]:
    values = [row["rank_ic"] for row in daily]
    last = daily[-1] if daily else {}
    spreads = [row["long_short_return"] for row in daily if row["long_short_return"] is not None]
    return {
        **base,
        "category": "price_volume",
        "ic": last.get("ic"),
        "rank_ic": last.get("rank_ic"),
        "rank_ic_mean": stats["rank_ic_mean"],
        "rank_ic_std": pstdev(values) if values else None,
        "icir": stats["icir"],
        "hit_rate": mean(value > 0 for value in spreads) if spreads else None,
        "long_short_return": last.get("long_short_return"),
        "coverage": len(valid) / max(len(latest), 1),
        "turnover": _rank_turnover(panel.values, base["factor_key"]),
        "avg_turnover_rate": None,
        "capacity_hint": "未评估真实容量",
        "quantile_monotonicity": _monotonic(last.get("group_returns", [])),
        "sample_size": len(daily),
        "asset_count": last.get("asset_count", 0),
        "factor_count": len(valid),
        "status": "可监控"
        if len(daily) >= config["min_ic_samples"] and len(valid) >= config["min_assets"]
        else "样本不足",
        "latest_date": last.get("date", ""),
        "label_end": last.get("label_end", ""),
        "snapshot_date": str(panel.values.index.get_level_values("date").max()) if not latest.empty else "",
    }


def _history_rows(output, base, daily, horizon) -> None:
    for row in daily:
        output["ic_history"].append({**base, **row})
        quantiles = [
            {
                **base,
                "date": row["date"],
                "label_end": row["label_end"],
                "horizon_days": horizon,
                "quantile": f"Q{index + 1}",
                "forward_return": value,
                "sample_size": row["group_sizes"][index],
            }
            for index, value in enumerate(row["group_returns"])
        ]
        output["quantile_history"].extend(quantiles)
        if row is daily[-1]:
            output["quantile_returns"].extend(quantiles)


def _snapshot_rows(output, base, valid, quotes, day) -> None:
    for rank, (symbol, value) in enumerate(valid.items(), 1):
        quote = quotes.get(symbol, {})
        output["snapshots"].append(
            {
                **base,
                "symbol": symbol,
                "name": quote.get("name") or symbol,
                "value": float(value),
                "rank": rank,
                "quantile": "待标签到期",
                "change_pct": quote.get("change_pct"),
                "turnover_rate": quote.get("turnover_rate"),
                "date": day,
            }
        )


def _exposure_rows(output, base, panel, latest) -> None:
    key = base["factor_key"]
    for other in panel.definitions:
        if other == key or latest.empty:
            continue
        pairs = latest[[key, other]].dropna()
        output["style_exposure"].append(
            {
                **base,
                "style_factor": panel.definitions[other]["label"],
                "exposure": correlation(pairs[key].tolist(), pairs[other].tolist(), ranked=True),
                "hint": "最新价量代理截面秩相关，非行业或市值中性暴露",
            }
        )


def _rank_turnover(panel: pd.DataFrame, key: str) -> float | None:
    dates = sorted(set(panel.index.get_level_values("date")))
    if len(dates) < 2:
        return None
    previous = panel.xs(dates[-2], level="date")[key].dropna().rank()
    current = panel.xs(dates[-1], level="date")[key].dropna().rank()
    common = previous.index.intersection(current.index)
    return (
        float((previous[common] - current[common]).abs().mean() / max(len(common) - 1, 1)) if len(common) > 1 else None
    )


def _monotonic(values: list[float]) -> float | None:
    return correlation(list(range(len(values))), values, ranked=True) if len(values) >= 2 else None


def _windows(output: dict[str, Any], base: dict[str, Any], daily: list[dict[str, Any]], config: dict[str, Any]) -> None:
    for window in config["rolling_windows"]:
        values = [row["rank_ic"] for row in daily[-window:]]
        output["rolling"].append(
            {
                **base,
                "window": window,
                "samples": len(values),
                "rank_ic_mean": mean(values) if len(values) >= window else None,
                "icir": information_ratio(values) if len(values) >= window else None,
            }
        )
    cutoff = max(len(daily) - config["holdout_dates"], 0)
    for name, rows in (("前段", daily[:cutoff]), ("后段", daily[cutoff:])):
        output["stability"].append(
            {
                **base,
                "segment": name,
                "samples": len(rows),
                "start": rows[0]["date"] if rows else "",
                "end": rows[-1]["date"] if rows else "",
                "rank_ic_mean": mean(row["rank_ic"] for row in rows) if rows else None,
                "note": "预先固定时间分段，不代表经过模型训练的样本外绩效",
            }
        )
