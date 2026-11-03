"""Provider fallback and cache reuse must not change the shares available for fills."""

import pytest

from src.data.backtest_history import _volume_in_shares, load_history
from src.engine.backtest.config import backtest_config
from src.engine.execution.config import resolve_costs
from src.engine.execution.policy import capacity


@pytest.mark.parametrize("source,volume", [("eastmoney-push2his-none", 2), ("tencent-fqkline-none", 200)])
def test_archived_provider_units_produce_equal_capacity_without_mutating_cache(monkeypatch, source, volume):
    class Provider:
        def _load_kline_tencent(self):
            raise AssertionError("Archive fixture should be reused")

    raw = [{"date": "2026-01-05", "volume": volume, "data_source": source}]
    monkeypatch.setattr("src.data.backtest_history._archive", lambda *args: raw)
    history = load_history(Provider(), "000001", "2026-01-05", "2026-01-05", "none")["kline"]
    policy = resolve_costs({"max_participation": 0.5, "lot_size": 100})
    assert history[0]["volume"] == 200 and history[0]["volume_unit"] == "shares"
    assert capacity(history, policy, 500) == 100
    assert raw[0]["volume"] == volume and "volume_unit" not in raw[0]
    assert _volume_in_shares(history, backtest_config()["history"]) == history
