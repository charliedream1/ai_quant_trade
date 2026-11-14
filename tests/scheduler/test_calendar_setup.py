"""Official schedule initialization never promotes an empty or stale file."""

from datetime import date
from pathlib import Path

import pytest
import yaml

from src.core.config import Settings
from src.scheduler import calendar_setup
from src.scheduler.calendar_updater import trading_calendar_status
from src.scheduler.policies import is_trading_day


def test_seed_preserves_exchange_weekends_and_user_file(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path / "data")
    monkeypatch.setattr(calendar_setup, "get_settings", lambda: settings)
    result = calendar_setup.initialize_calendar()
    assert result["created"]
    path = Path(result["path"])
    record = yaml.safe_load(path.read_text(encoding="utf-8"))["markets"]["cn_stock"]
    assert not is_trading_day(date(2026, 2, 28), record)
    assert not is_trading_day(date(2026, 10, 1), record)
    assert is_trading_day(date(2026, 10, 8), record)
    before = path.read_bytes()
    assert not calendar_setup.initialize_calendar()["created"]
    assert path.read_bytes() == before


def test_explicit_missing_calendar_is_preserved(tmp_path, monkeypatch):
    selected = tmp_path / "custom.yaml"
    monkeypatch.setattr(
        calendar_setup, "get_settings", lambda: Settings(data_dir=tmp_path, trading_calendar_path=selected)
    )
    with pytest.raises(ValueError, match="Configured"):
        calendar_setup.initialize_calendar()
    assert not selected.exists()


def test_empty_calendar_and_outside_coverage_are_not_healthy(tmp_path):
    target = tmp_path / "calendar.yaml"
    target.write_text("markets:\n  cn_stock:\n    holidays: []\n", encoding="utf-8")
    assert trading_calendar_status({"calendar_path": str(target)})["status"] == "invalid"
    target.write_text(
        "markets:\n  cn_stock:\n    range_start: '2025-01-01'\n    range_end: '2025-12-31'\n", encoding="utf-8"
    )
    assert trading_calendar_status({"calendar_path": str(target)})["status"] == "out_of_range"
