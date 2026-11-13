"""Published HKEX session dates; unsupported years never masquerade as verified calendars."""

from datetime import date, timedelta
from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def calendar_config():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/data/hong_kong_calendar.yaml").read_text(encoding="utf-8"))


def sessions(start, end):
    current, last = date.fromisoformat(start), date.fromisoformat(end)
    config = calendar_config()
    if any(str(year) not in config["years"] for year in range(current.year, last.year + 1)):
        return None
    result = []
    while current <= last:
        if current.weekday() < 5 and current.isoformat() not in config["years"][str(current.year)]["holidays"]:
            result.append(current.isoformat())
        current += timedelta(days=1)
    return result
