"""ETF strategy, universe metadata and ETF-specific backtest evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.data.etf import ETFUniverseService
from src.engine.backtest import BacktestRunner
from src.strategy import StrategyStore
from src.strategy.parameters import StrategyParameters

ETF_EXAMPLES = [
    ("etf_momentum_rotation_strategy.py", "etf_momentum.yaml:baseline"),
    ("etf_trend_allocation_strategy.py", "etf_trend.yaml:baseline"),
]


def test_configured_etf_universes_have_metadata_and_symbols():
    service = ETFUniverseService()
    universes = service.list_universes()
    assert {item["universe"] for item in universes} >= {"cn_core", "cn_sector"}
    detail = service.universe("cn_core")
    assert detail["asset_type"] == "etf"
    assert detail["symbols"]
    assert all(item["benchmark"] and item["category"] for item in detail["symbols"])


@pytest.mark.parametrize("filename,profile", ETF_EXAMPLES)
def test_etf_examples_use_parameter_profiles_and_complete_backtest(client, filename, profile):
    store = StrategyStore()
    item = store.import_example(f"egs/examples/strategy_examples/{filename}", {"name": f"etf_{Path(filename).stem}"})
    resolved = StrategyParameters().resolve(item["id"], {"universe": "cn_core"}, profile)
    assert resolved["resolved_params"]["universe"] == "cn_core"
    task = BacktestRunner().create(
        {
            "strategy_id": item["id"],
            "parameter_profile": profile,
            "params": {"universe": "cn_core"},
            "symbols": ["510300", "510500", "159915", "512100"],
            "start_date": "2026-01-05",
            "end_date": "2026-06-30",
            "initial_capital": 1000000,
            "order_type": "open",
            "price_adjustment": "qfq",
            "max_position_count": 2,
            "max_position_weight": 0.6,
            "lot_size": 100,
            "slippage_rate": 0.001,
        }
    )
    metrics = BacktestRunner().performance(task["id"])
    snapshot = BacktestRunner().detail(task["id"])["parameter_snapshot"]
    assert task["status"] == "finished"
    assert metrics["asset_type"] == "etf"
    assert metrics["tracking_error"] >= 0
    assert metrics["etf_universe"] == "cn_core"
    assert snapshot["resolved_params"]["universe"] == "cn_core"
    assert snapshot["profile"]["id"] == profile
