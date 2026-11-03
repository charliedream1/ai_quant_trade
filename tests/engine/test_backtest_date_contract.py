"""Regression tests for strict backtest date boundaries."""

from src.engine.backtest.engines import _filter_events, _mock_events_in_range


def test_out_of_range_rows_are_not_reused():
    rows = [{"date": "2026-10-12", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 100}]
    assert _filter_events("600519", rows, "2026-01-05", "2026-01-16") == []


def test_mock_rows_receive_weekday_dates_inside_requested_range():
    rows = [{"open": 1, "high": 2, "low": 1, "close": 2, "volume": 100} for _ in range(4)]
    events = _mock_events_in_range("600519", rows, "2026-01-05", "2026-01-09")
    assert [event.timestamp for event in events] == [
        "2026-01-05T00:00:00",
        "2026-01-06T00:00:00",
        "2026-01-07T00:00:00",
        "2026-01-08T00:00:00",
    ]
