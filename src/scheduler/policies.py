"""Scheduler execution policies for calendar filtering and retries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from src.core.config import get_settings

CHINA_MARKET_UTC_OFFSET_HOURS = 8
DEFAULT_RETRY_TIMES = 0
DEFAULT_RETRY_INTERVAL_SECONDS = 0.0
DEFAULT_RETRY_BACKOFF = 2.0
MAX_RETRY_TIMES = 5
MAX_RETRY_INTERVAL_SECONDS = 3600.0
MAX_RETRY_BACKOFF = 10.0
DEFAULT_TIMEOUT_SECONDS = 0.0
MAX_TIMEOUT_SECONDS = 24 * 60 * 60.0
THREAD_TIMEOUT_MODE = "thread"
PROCESS_TIMEOUT_MODE = "process"


@dataclass(frozen=True)
class RetryPolicy:
    retry_times: int
    interval_seconds: float
    backoff: float

    @property
    def max_attempts(self) -> int:
        return self.retry_times + 1

    def delay_seconds(self, attempt: int) -> float:
        """Return delay before a 1-based retry attempt."""

        if attempt <= 1 or self.interval_seconds <= 0:
            return 0.0
        delay = self.interval_seconds * (self.backoff ** max(attempt - 2, 0))
        return min(delay, MAX_RETRY_INTERVAL_SECONDS)


def retry_policy_from_params(params: dict[str, Any]) -> RetryPolicy:
    retry_times = _bounded_int(
        params.get("retry_times", params.get("retry_count", params.get("retries", DEFAULT_RETRY_TIMES))),
        DEFAULT_RETRY_TIMES,
        0,
        MAX_RETRY_TIMES,
    )
    interval_seconds = _bounded_float(
        params.get("retry_interval_seconds", params.get("retry_interval", DEFAULT_RETRY_INTERVAL_SECONDS)),
        DEFAULT_RETRY_INTERVAL_SECONDS,
        0.0,
        MAX_RETRY_INTERVAL_SECONDS,
    )
    backoff = _bounded_float(
        params.get("retry_backoff", DEFAULT_RETRY_BACKOFF),
        DEFAULT_RETRY_BACKOFF,
        1.0,
        MAX_RETRY_BACKOFF,
    )
    return RetryPolicy(retry_times=retry_times, interval_seconds=interval_seconds, backoff=backoff)


def timeout_seconds_from_params(params: dict[str, Any]) -> float | None:
    raw = params.get("timeout_seconds")
    if raw in (None, "") and params.get("timeout_minutes") not in (None, ""):
        raw = float(params["timeout_minutes"]) * 60.0
    timeout = _bounded_float(raw, DEFAULT_TIMEOUT_SECONDS, 0.0, MAX_TIMEOUT_SECONDS)
    return timeout if timeout > 0 else None


def timeout_mode_from_params(params: dict[str, Any]) -> str:
    raw = str(params.get("timeout_mode") or params.get("timeout_execution") or "").strip().lower()
    if raw in {PROCESS_TIMEOUT_MODE, "hard", "kill", "subprocess"}:
        return PROCESS_TIMEOUT_MODE
    if _truthy(params.get("hard_timeout", False)) or _truthy(params.get("process_timeout", False)):
        return PROCESS_TIMEOUT_MODE
    return THREAD_TIMEOUT_MODE if raw in {THREAD_TIMEOUT_MODE, "soft"} else PROCESS_TIMEOUT_MODE


def mutex_group_from_params(params: dict[str, Any]) -> str | None:
    raw = params.get("mutex_group", params.get("mutex"))
    if raw in (None, ""):
        return None
    group = str(raw).strip()
    return group or None


def trading_day_skip_summary(params: dict[str, Any], now: datetime | None = None) -> str | None:
    if not _truthy(params.get("trading_day_only", params.get("only_trading_day", False))):
        return None
    calendar = _calendar_params(params)
    current_date = market_date(now)
    if is_trading_day(current_date, calendar):
        return None
    return f"非交易日 {current_date.isoformat()}，按交易日过滤跳过。"


def market_date(now: datetime | None = None) -> date:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return (current.astimezone(UTC) + timedelta(hours=CHINA_MARKET_UTC_OFFSET_HOURS)).date()


def is_trading_day(value: date, calendar: dict[str, Any] | None = None) -> bool:
    calendar = calendar or {}
    text = value.isoformat()
    if text in _date_set(calendar, "extra_trading_days", "trading_days"):
        return True
    if text in _date_set(calendar, "extra_holidays", "holidays"):
        return False
    return value.weekday() < 5


def _calendar_params(params: dict[str, Any]) -> dict[str, Any]:
    calendar = _calendar_file_params(params)
    inline_calendar = params.get("trading_calendar") or params.get("calendar") or {}
    if isinstance(inline_calendar, dict):
        calendar = _merge_calendar(calendar, inline_calendar)
    return calendar


def _calendar_file_params(params: dict[str, Any]) -> dict[str, Any]:
    path = _calendar_path(params)
    if path is None or not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        return {}
    market = str(params.get("calendar_market") or params.get("market") or "cn_stock").strip() or "cn_stock"
    market_payload = loaded.get("markets", {})
    if isinstance(market_payload, dict):
        loaded = market_payload.get(market) or market_payload.get("cn_stock") or {}
    return loaded if isinstance(loaded, dict) else {}


def _calendar_path(params: dict[str, Any]) -> Path | None:
    settings = get_settings()
    raw = params.get("trading_calendar_path") or params.get("calendar_path") or settings.trading_calendar_path or None
    if raw in (None, ""):
        return None
    path = Path(str(raw))
    return path if path.is_absolute() else (settings.project_root / path).resolve()


def _merge_calendar(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in {"holidays", "extra_holidays", "trading_days", "extra_trading_days"}:
            merged[key] = sorted(_date_set(merged, key) | _date_set({key: value}, key))
        elif key in {"market", "source", "timezone"}:
            merged[key] = value
        else:
            merged[key] = value
    return merged


def _date_set(params: dict[str, Any], *keys: str) -> set[str]:
    values: set[str] = set()
    for key in keys:
        raw = params.get(key)
        if raw in (None, ""):
            continue
        if isinstance(raw, str):
            items = [item.strip() for item in raw.split(",")]
        elif isinstance(raw, list | tuple | set):
            items = [str(item).strip() for item in raw]
        else:
            items = [str(raw).strip()]
        values.update(item for item in items if item)
    return values


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "是", "开启"}
    return bool(value)


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    if value in (None, ""):
        return default
    return min(max(int(value), minimum), maximum)


def _bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    if value in (None, ""):
        return default
    return min(max(float(value), minimum), maximum)
