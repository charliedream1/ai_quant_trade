"""Offline first-run calendar setup preserves explicit and legacy user files."""

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import yaml
from filelock import FileLock

from src.core.config import get_settings
from src.core.diagnostics_config import diagnostics_config
from src.core.timeutil import utc_now_iso


def exchange_today():
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def active_calendar_path():
    settings = get_settings()
    if settings.trading_calendar_path:
        path = Path(settings.trading_calendar_path)
        return (path if path.is_absolute() else settings.project_root / path).resolve()
    legacy = settings.project_root / "egs/config/data/trading_calendar.yaml"
    if legacy.is_file():
        return legacy.resolve()
    policy = diagnostics_config()["calendar"]
    return (settings.data_dir / policy["directory"] / policy["filename"]).resolve()


def initialize_calendar():
    settings = get_settings()
    target = active_calendar_path()
    if target.exists():
        return {"path": str(target), "created": False}
    managed = (
        settings.data_dir / diagnostics_config()["calendar"]["directory"] / diagnostics_config()["calendar"]["filename"]
    ).resolve()
    if settings.trading_calendar_path and target != managed:
        raise ValueError("Configured calendar is missing; restore it or select the managed default")
    base = settings.data_dir.resolve()
    if not target.is_relative_to(base):
        raise ValueError("Managed calendar escapes the private data directory")
    policy = diagnostics_config()["calendar"]
    payload = yaml.safe_load((settings.project_root / policy["seed"]).read_text(encoding="utf-8"))
    calendar = payload["markets"]["cn_stock"]
    if not calendar["range_start"] <= exchange_today().isoformat() <= calendar["range_end"]:
        raise ValueError("No verified bundled exchange calendar covers the current date")
    target.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(target) + ".lock", timeout=policy["lock_seconds"]):
        if target.exists():
            return {"path": str(target), "created": False}
        calendar["updated_at"] = utc_now_iso()
        pending = target.with_name(uuid4().hex + ".pending")
        pending.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        os.replace(pending, target)
    return {"path": str(target), "created": True, "source": calendar["source"]}
