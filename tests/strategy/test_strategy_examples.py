"""Import and run every bundled strategy example through the real backtest runner."""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path

import pytest

from src.engine.backtest import BacktestRunner
from src.strategy import StrategyLoader, StrategyStore, StrategyValidator

EXAMPLES = sorted(Path("egs/examples/strategy_examples").glob("*_strategy.py"))


def test_all_strategy_examples_validate_and_dry_run():
    validator = StrategyValidator()
    loader = StrategyLoader()
    assert len(EXAMPLES) >= 8
    for path in EXAMPLES:
        validation = validator.validate_source(path.read_text(encoding="utf-8"))
        report = loader.dry_run(path, symbols=["600519", "300750"])
        assert validation["valid"] is True, path
        assert report["valid"] is True, path
        assert report["adapter_type"] in {"strategy_base_class", "class_port", "function_port"}


@pytest.mark.parametrize("path", EXAMPLES)
def test_all_strategy_examples_complete_mock_backtest(client, path):
    store = StrategyStore()
    runner = BacktestRunner()
    dependencies = {
        "lightgbm_rank_strategy": "lightgbm",
        "xgboost_rank_strategy": "xgboost",
        "mlp_ensemble_strategy": "torch",
    }
    dependency = dependencies.get(path.stem)
    if dependency and find_spec(dependency) is None:
        pytest.skip(f"optional model backend unavailable: {dependency}")
    item = store.import_example(path.as_posix(), {"name": f"validation_{path.stem}"})
    task = runner.create(
        {
            "strategy_id": item["strategy_id"],
            "symbols": ["600519", "300750", "000001"],
            "start_date": "2026-01-05",
            "end_date": "2026-04-30",
            "initial_capital": 1_000_000,
            "params": item.get("default_params") or {},
            "order_type": "open" if dependency else "market",
            "price_adjustment": "qfq",
            "max_position_count": 3,
            "max_position_weight": 0.35,
            "lot_size": 100,
            "slippage_rate": 0.001,
        }
    )
    assert task["status"] == "finished", path
    curve = runner.equity_curve(int(task["task_id"]))
    assert curve["dates"]
    assert all("2026-01-05" <= str(value)[:10] <= "2026-04-30" for value in curve["dates"]), path
    metrics = runner.performance(int(task["task_id"]))
    assert metrics["engine_mode"] == "event_kline", path
    assert metrics["data_source"] == "mock-local", path
