"""Bounded parallel OHLCV reads and causal normalization."""

from __future__ import annotations

import math
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd

from src.core.timeutil import today_date
from src.data import DataSourceManager


def load_history(
    data: DataSourceManager,
    universe: dict[str, Any],
    config: dict[str, Any],
    progress: Callable[[str], None] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], list[dict[str, str]]]:
    history, quotes, failures = {}, {}, []
    symbols = universe["symbols"]
    with ThreadPoolExecutor(max_workers=config["load_workers"], thread_name_prefix="factor-prices") as executor:
        futures = {executor.submit(_load, data, symbol, universe["as_of"], config): symbol for symbol in symbols}
        for count, future in enumerate(as_completed(futures), 1):
            symbol = futures[future]
            try:
                bars, quote = future.result()
                if not bars:
                    raise ValueError("观察日期内没有有效日线")
                history[symbol], quotes[symbol] = bars, quote
            except Exception as exc:
                failures.append({"symbol": symbol, "error": str(exc)})
            if progress:
                progress(f"读取行情 {count}/{len(symbols)}，成功{len(history)}，失败{len(failures)}")
    return history, quotes, failures


def _load(
    data: DataSourceManager, symbol: str, as_of: str, config: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    provider = getattr(data, "provider", data)
    light = getattr(provider, "strategy_snapshot", None)
    method = light if callable(light) else data.stock_detail
    detail = method(
        symbol=symbol,
        kline_count=config["history_bars"],
        kline_period="daily",
        price_adjustment=config["price_adjustment"],
    )
    unique = {}
    raw = detail.get("kline") or []
    if raw and all(str(row.get("date") or "").startswith("D-") for row in raw) and getattr(data, "is_mock", False):
        days = pd.bdate_range(end=today_date(), periods=len(raw)).strftime("%Y-%m-%d")
        raw = [{**row, "date": str(day)} for row, day in zip(raw, days, strict=True)]
    for row in raw:
        day = str(row.get("date") or row.get("trade_date") or row.get("timestamp") or "")[:10]
        close = float(row.get("close") or 0)
        if not day or day > as_of or not math.isfinite(close) or close <= 0:
            continue
        unique[day] = {**row, "date": day, "close": close, "data_source": data.source_name}
    return [unique[day] for day in sorted(unique)], detail.get("quote") or {}
