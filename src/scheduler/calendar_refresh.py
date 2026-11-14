"""Refresh the managed annual schedule only after a complete original-source match."""

import hashlib
import os
from datetime import date
from time import monotonic
from uuid import uuid4

import yaml
from bs4 import BeautifulSoup
from filelock import FileLock

from src.core.config import get_settings
from src.core.diagnostics_config import diagnostics_config
from src.core.network_policy import network_session
from src.core.timeutil import utc_now_iso

from .calendar_setup import active_calendar_path, initialize_calendar
from .calendar_updater import _parse_announcement_calendar


def _official_text(url, policy):
    started = monotonic()
    with network_session(public_only=True) as session:
        with session.get(url, timeout=policy["timeout_seconds"], stream=True) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(policy["chunk_bytes"]):
                data.extend(chunk)
                if len(data) > policy["max_bytes"] or monotonic() - started > policy["timeout_seconds"]:
                    raise ValueError("Official calendar response exceeds its budget")
    return BeautifulSoup(bytes(data), "html.parser").get_text(" ", strip=True), hashlib.sha256(data).hexdigest()


def refresh_managed_calendar():
    settings, policy = get_settings(), diagnostics_config()["calendar"]
    target = active_calendar_path()
    managed = (settings.data_dir / policy["directory"] / policy["filename"]).resolve()
    if target != managed:
        raise ValueError("Custom calendars are preserved; refresh them with their registered calendar task")
    initialize_calendar()
    seed = yaml.safe_load((settings.project_root / policy["seed"]).read_text(encoding="utf-8"))
    expected = seed["markets"]["cn_stock"]
    verified = []
    failures = []
    for url in expected["metadata"]["sources"]:
        try:
            text, digest = _official_text(url, policy)
            holidays, trading = _parse_announcement_calendar(text, expected)
            weekdays = {
                day
                for day in holidays
                if date.fromisoformat(day).weekday() < 5 and expected["range_start"] <= day <= expected["range_end"]
            }
            if weekdays != set(expected["holidays"]) or any(date.fromisoformat(day).weekday() >= 5 for day in trading):
                raise ValueError("Official schedule differs or cannot be completely parsed; manual review required")
            verified.append({"url": url, "sha256": digest})
        except Exception as exc:
            failures.append(type(exc).__name__)
    if not verified:
        raise ValueError("No official source verified the complete schedule; prior calendar retained")
    with FileLock(str(target) + ".lock", timeout=policy["lock_seconds"]):
        payload = yaml.safe_load(target.read_text(encoding="utf-8"))
        current = payload["markets"]["cn_stock"]
        if current["holidays"] != expected["holidays"] or current["range_end"] != expected["range_end"]:
            raise ValueError("Existing calendar differs from the bundled schedule; preserved for manual review")
        current["updated_at"] = utc_now_iso()
        current["metadata"]["verified_originals"] = verified
        pending = target.with_name(uuid4().hex + ".pending")
        pending.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        os.replace(pending, target)
    return {"path": str(target), "verified_sources": len(verified), "source_failures": failures}
