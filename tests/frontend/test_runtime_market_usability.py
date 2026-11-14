"""Regression checks for honest rankings, validated inputs and shared work."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest
import yaml

from src.core.exceptions import BusinessError
from src.engine.market.quote_service import QuoteService
from src.frontend.service.economics import EconomicUIMixin


def test_both_sector_directions_are_requested_without_fabricated_decliners(client):
    values = yaml.safe_load(Path(__file__).with_name("runtime_market_fixtures.yaml").read_text(encoding="utf-8"))
    calls = []

    class Source:
        def sectors(self, board, limit, direction):
            calls.append(direction)
            return sorted(values["sectors"], key=lambda row: row["change_pct"], reverse=direction == "desc")[:limit]

    service = QuoteService(data=Source())
    rows = service.sector_rankings(limit=4)
    assert set(calls) == {"asc", "desc"}
    assert {row["code"] for row in rows} == {"up", "mild", "down"}
    assert next(row for row in rows if row["code"] == "down")["ranking"] == "Decliner"
    values["sectors"] = [row for row in values["sectors"] if row["change_pct"] > 0]
    assert not service.sector_rankings(selection="decliners")


@pytest.mark.parametrize("symbol,period", [("", ""), ("   ", ""), ("600519", "bad"), ("600519", "2026-11-14")])
def test_financial_input_rejected_before_fetch(monkeypatch, symbol, period):
    from src.engine.economics.service import EconomicAnalysis

    monkeypatch.setattr(
        EconomicAnalysis, "fundamentals", lambda *args, **kwargs: pytest.fail("No source request expected")
    )
    with pytest.raises(BusinessError):
        EconomicUIMixin().economic_load("fundamentals", [], symbol, period, "", False)


def test_concurrent_ui_cache_misses_share_one_loader(client):
    from src.frontend.service.foundation import _daily_cached

    entered, release, started = Event(), Event(), Event()
    calls = []

    def load():
        calls.append(1)
        entered.set()
        assert release.wait(5)
        return {"value": 7}

    def follower():
        started.set()
        return _daily_cached(("singleflight-acceptance",), load)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(_daily_cached, ("singleflight-acceptance",), load)
        assert entered.wait(5)
        second = executor.submit(follower)
        assert started.wait(5)
        release.set()
        assert first.result()[0] == second.result()[0] == {"value": 7}
    assert len(calls) == 1


def test_successful_callback_is_debug_even_when_slow(monkeypatch):
    from src.frontend.common import callbacks

    levels = []
    clock = iter([0.0, 10.0])
    monkeypatch.setattr(callbacks, "perf_counter", lambda: next(clock))
    monkeypatch.setattr(callbacks.CALLBACK_LOG, "log", lambda level, *args: levels.append(level))
    with callbacks._callback_run("acceptance", "test"):
        pass
    assert levels == ["DEBUG"]
