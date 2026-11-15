"""Local inbox days map to explicit UTC windows, including DST-aware configuration."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import config


def window(selected_date: str | None = None, history: bool = False) -> tuple[str, str, str]:
    cfg = config()
    zone = ZoneInfo(cfg["timezone"])
    today = datetime.now(zone).date()
    selected = date.fromisoformat(selected_date) if selected_date else today
    if selected > today:
        raise ValueError("Notification dates cannot be in the future")
    start = datetime.combine(selected, time.min, zone)
    end = datetime.combine(selected + timedelta(days=1), time.min, zone)
    if history:
        start = datetime.combine(today - timedelta(days=cfg["retention_days"]), time.min, zone)
        end = datetime.combine(today + timedelta(days=1), time.min, zone)
    return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat(), selected.isoformat()
