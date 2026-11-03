"""Date-bounded OHLCV archives; real data never falls back to synthetic bars."""

import hashlib
import json
from datetime import date, timedelta
from time import time
from typing import Any

from src.core.config import get_settings
from src.core.exceptions import BusinessError, ErrorCode
from src.core.logger import get_logger
from src.engine.backtest.config import backtest_config

LOG = get_logger("backtest.history")


def load_history(data: Any, symbol: str, start: str, end: str, adjustment: str, warmup: bool = False) -> dict[str, Any]:
    """Return bars plus coverage evidence, checking the actual exchange index calendar."""
    cfg = backtest_config()["history"]
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last or (last - first).days > cfg["max_calendar_days"] or last > date.today():
        raise BusinessError(ErrorCode.INVALID_PARAM, "回测日期无效、超过历史跨度限制或包含未来日期")
    provider = getattr(data, "provider", data)
    if not callable(getattr(provider, "_load_kline_tencent", None)):
        fetch = getattr(provider, "strategy_snapshot", None) or provider.stock_detail
        return fetch(symbol, kline_count=cfg["mock_bars"], kline_period="daily", price_adjustment=adjustment)
    begin = (first - timedelta(days=cfg["warmup_calendar_days"])).isoformat() if warmup else start
    rows = _volume_in_shares(_archive(provider, symbol, begin, end, adjustment, cfg), cfg)
    calendar = _archive(provider, cfg["calendar_symbol"], start, end, "none", cfg)
    expected = {row["date"] for row in calendar if start <= row["date"] <= end}
    actual = {row["date"] for row in rows if start <= row["date"] <= end}
    missing = sorted(expected - actual)
    if not expected or missing:
        sample = ", ".join(missing[:8]) or f"{start} 至 {end}无交易日历"
        raise BusinessError(
            ErrorCode.DATA_SOURCE_ERROR, f"{symbol} 历史覆盖不足：{sample}；请补齐行情或调整日期，未生成部分回测"
        )
    return {
        "kline": rows,
        "coverage": {
            "requested_start": start,
            "requested_end": end,
            "actual_start": min(actual),
            "actual_end": max(actual),
            "calendar_source": cfg["calendar_symbol"],
            "expected_sessions": len(expected),
            "missing_sessions": missing,
            "warmup_start": rows[0]["date"] if rows else None,
        },
    }


def _volume_in_shares(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize fresh and cached source rows without changing the raw archive."""
    result = []
    for row in rows:
        source = str(row.get("data_source", ""))
        factor = next((value for prefix, value in cfg["volume_multipliers"].items() if source.startswith(prefix)), 1)
        if row.get("volume_unit") == "shares":
            factor = 1
        result.append({**row, "volume": float(row["volume"]) * factor, "volume_unit": "shares"})
    return result


def _archive(
    provider: Any, symbol: str, start: str, end: str, adjustment: str, cfg: dict[str, Any]
) -> list[dict[str, Any]]:
    key = hashlib.sha256(json.dumps([provider.source_name, symbol, start, end, adjustment]).encode()).hexdigest()
    root = get_settings().data_dir / "backtest_history"
    path = root / f"{key[:24]}.json"
    if path.is_file() and time() - path.stat().st_mtime < cfg["cache_seconds"]:
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached.get("key") == key:
            return cached["rows"]
    rows = []
    current = date.fromisoformat(start)
    last = date.fromisoformat(end)
    while current <= last:
        boundary = min(current + timedelta(days=cfg["batch_calendar_days"] - 1), last)
        rows.extend(_download(provider, symbol, current.isoformat(), boundary.isoformat(), adjustment, cfg))
        current = boundary + timedelta(days=1)
    provider._validate_kline(rows, "dated archive")
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"key": key, "rows": rows}, ensure_ascii=False), encoding="utf-8")
    return rows


def _download(provider, symbol, start, end, adjustment, cfg):
    errors = []
    for source in ("tencent", "eastmoney", "baostock"):
        try:
            method = getattr(provider, f"_load_kline_{source}")
            rows = method(symbol, "daily", cfg["max_bars"], adjustment, start_date=start, end_date=end)
            rows = [row for row in rows if start <= row["date"] <= end]
            if not rows:
                raise ValueError("请求区间无行情")
            provider._validate_kline(rows, source)
            LOG.info("dated history | {} {}..{} source={} bars={}", symbol, start, end, source, len(rows))
            return rows
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    raise BusinessError(ErrorCode.DATA_SOURCE_ERROR, f"{symbol} 按日期取数失败：" + "; ".join(errors))
