"""Cron helpers with APScheduler support and a small fallback parser."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.timeutil import utc_now

try:
    from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-not-found]
except ModuleNotFoundError:
    CronTrigger = None  # type: ignore[assignment,misc]

APSCHEDULER_AVAILABLE = CronTrigger is not None
FIELD_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))
MAX_LOOKAHEAD_MINUTES = 366 * 24 * 60


def normalize_cron(value: Any) -> str:
    cron_expr = str(value or "").strip()
    if not cron_expr:
        raise BusinessError(ErrorCode.INVALID_PARAM, "Cron 表达式不能为空")
    _parse_cron(cron_expr)
    return cron_expr


def next_run_iso(cron_expr: str, base: datetime | None = None) -> str:
    normalized = normalize_cron(cron_expr)
    if CronTrigger is not None:
        trigger = CronTrigger.from_crontab(normalized, timezone=timezone.utc)
        next_run = trigger.get_next_fire_time(None, base or utc_now())
        if next_run is None:
            raise BusinessError(ErrorCode.INVALID_PARAM, f"Cron 表达式无法计算下次执行时间：{cron_expr}")
        return _iso(next_run)
    return _fallback_next_run(normalized, base or utc_now())


def build_cron_trigger(cron_expr: str) -> Any:
    normalized = normalize_cron(cron_expr)
    if CronTrigger is None:
        return None
    return CronTrigger.from_crontab(normalized, timezone=timezone.utc)


def _fallback_next_run(cron_expr: str, base: datetime) -> str:
    minute_set, hour_set, day_set, month_set, weekday_set = _parse_cron(cron_expr)
    cursor = base.astimezone(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(MAX_LOOKAHEAD_MINUTES):
        if (
            cursor.minute in minute_set
            and cursor.hour in hour_set
            and cursor.day in day_set
            and cursor.month in month_set
            and _cron_weekday(cursor) in weekday_set
        ):
            return _iso(cursor)
        cursor += timedelta(minutes=1)
    raise BusinessError(ErrorCode.INVALID_PARAM, f"Cron 表达式未来一年内无触发时间：{cron_expr}")


def _parse_cron(cron_expr: str) -> tuple[set[int], set[int], set[int], set[int], set[int]]:
    fields = cron_expr.split()
    if len(fields) != 5:
        raise BusinessError(ErrorCode.INVALID_PARAM, f"Cron 表达式必须是 5 段：{cron_expr}")
    try:
        parsed = tuple(_parse_field(field, *FIELD_RANGES[index]) for index, field in enumerate(fields))
    except ValueError as exc:
        raise BusinessError(ErrorCode.INVALID_PARAM, f"Cron 表达式非法：{cron_expr}") from exc
    return parsed  # type: ignore[return-value]


def _parse_field(field: str, min_value: int, max_value: int) -> set[int]:
    values: set[int] = set()
    for part in field.split(","):
        token = part.strip()
        if not token:
            raise ValueError("empty cron token")
        if "/" in token:
            base, step_text = token.split("/", 1)
            step = int(step_text)
            if step <= 0:
                raise ValueError("invalid cron step")
        else:
            base = token
            step = 1
        if base == "*":
            start, end = min_value, max_value
        elif "-" in base:
            start_text, end_text = base.split("-", 1)
            start, end = int(start_text), int(end_text)
        else:
            start = end = int(base)
        if start < min_value or end > max_value or start > end:
            raise ValueError("cron value out of range")
        values.update(range(start, end + 1, step))
    if max_value == 7 and 7 in values:
        values.add(0)
        values.discard(7)
    return values


def _cron_weekday(value: datetime) -> int:
    weekday = value.isoweekday()
    return 0 if weekday == 7 else weekday


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
