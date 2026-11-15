"""Small table, clock and snapshot primitives shared without domain-service imports."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Sequence
from concurrent.futures import Future
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any

import pandas as pd
import yaml

from src.core.config import PROJECT_ROOT, get_settings
from src.core.diagnostics_config import diagnostics_config
from src.core.logger import get_logger
from src.data import current_market

SHANGHAI_TZ = timezone(timedelta(hours=8))
LOG = get_logger("frontend.services")
_DAILY_UI_CACHE: dict[str, tuple[str, str, Any]] = {}
_DAILY_UI_CACHE_LOCK = RLock()
_DAILY_UI_LOADING: dict[str, Future] = {}
INDEX_COLUMNS = ["code", "name", "price", "change", "change_pct", "volume", "amount", "data_source", "updated_at"]

WATCHLIST_COLUMNS = [
    "symbol",
    "name",
    "latest_price",
    "change_pct",
    "volume",
    "turnover_rate",
    "data_source",
    "updated_at",
    "group_id",
    "remark",
]

HOLDING_COLUMNS = [
    "symbol",
    "name",
    "quantity",
    "available_qty",
    "latest_price",
    "change_pct",
    "market_value",
    "float_pnl",
    "float_pnl_pct",
    "data_source",
]

ACCOUNT_MODE_CHOICES = [
    (str(row["label"]), str(row["id"]))
    for row in yaml.safe_load(
        (PROJECT_ROOT / "egs/config/platform/ai_workbench_presets.yaml").read_text(encoding="utf-8")
    )["account_modes"]
]


def _local_now() -> datetime:
    return datetime.now(SHANGHAI_TZ).replace(microsecond=0)


def _display_now() -> str:
    return _local_now().strftime("%Y-%m-%d %H:%M:%S")


def _today_key() -> str:
    return _local_now().date().isoformat()


def _cache_key(parts: Sequence[Any]) -> str:
    settings = get_settings()
    namespace = [str(settings.db_path), str(settings.data_dir), str(settings.data_mode), current_market()]
    return json.dumps([*namespace, *(str(part) for part in parts)], ensure_ascii=False, sort_keys=True)


def _daily_cached(
    key_parts: Sequence[Any], loader: Callable[[], Any], force_refresh: bool = False
) -> tuple[Any, bool, str]:
    """Cache low-frequency UI payloads for the current local trading day."""
    cache_key = _cache_key(key_parts)
    today = _today_key()
    with _DAILY_UI_CACHE_LOCK:
        cached = _DAILY_UI_CACHE.get(cache_key)
        if cached and cached[0] == today and not force_refresh:
            return copy.deepcopy(cached[2]), True, cached[1]
        pending = _DAILY_UI_LOADING.get(cache_key)
        owner = pending is None
        if owner:
            pending = Future()
            _DAILY_UI_LOADING[cache_key] = pending
    assert pending is not None
    if not owner:
        value, refreshed_at = pending.result(timeout=diagnostics_config()["cache"]["wait_seconds"])
        return copy.deepcopy(value), True, refreshed_at
    try:
        LOG.debug("UI snapshot load | key={} refresh={}", cache_key, force_refresh)
        value = loader()
        refreshed_at = _display_now()
        with _DAILY_UI_CACHE_LOCK:
            _DAILY_UI_CACHE[cache_key] = (today, refreshed_at, copy.deepcopy(value))
        pending.set_result((value, refreshed_at))
        return copy.deepcopy(value), False, refreshed_at
    except BaseException as exc:
        pending.set_exception(exc)
        raise
    finally:
        with _DAILY_UI_CACHE_LOCK:
            _DAILY_UI_LOADING.pop(cache_key, None)


def _normalize_account_mode(value: Any) -> str:
    allowed = {choice_value for _, choice_value in ACCOUNT_MODE_CHOICES}
    selected = str(value or "paper").strip()
    return selected if selected in allowed else "paper"


def to_frame(value: Any, columns: Sequence[str] | None = None) -> pd.DataFrame:
    """Convert service payloads to stable, readable Gradio tables."""
    if value is None:
        return pd.DataFrame(columns=list(columns or []))
    if isinstance(value, dict) and "items" in value:
        value = value.get("items") or []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        value = [value]
    if not value:
        if columns:
            return pd.DataFrame(columns=list(columns))
        return pd.DataFrame([{"状态": "暂无数据"}])
    rows: list[dict[str, Any]] = []
    for item in value:
        row = dict(item) if isinstance(item, dict) else {"value": item}
        for key, cell in list(row.items()):
            if isinstance(cell, dict | list | tuple):
                row[key] = json.dumps(cell, ensure_ascii=False)
        rows.append(row)
    frame = pd.DataFrame(rows)
    if columns:
        for column in columns:
            if column not in frame:
                frame[column] = None
        frame = frame[list(columns)]
    return frame
