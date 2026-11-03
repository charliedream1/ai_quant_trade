"""Fit real model backends and verify strategy causality through the API."""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml

from src.engine.backtest import BacktestRunner
from src.strategy import StrategyStore
from src.strategy.models.config import model_config
from src.strategy.models.features import build_panel, time_split
from src.strategy.models.runtime import ModelStrategy

PROFILE_FILES = [
    ("lightgbm_rank", "lightgbm", "lightgbm_rank_strategy.py"),
    ("xgboost_rank", "xgboost", "xgboost_rank_strategy.py"),
    ("mlp_ensemble", "torch", "mlp_ensemble_strategy.py"),
]


@pytest.fixture
def bars() -> dict[str, list[dict[str, Any]]]:
    config = yaml.safe_load(Path("tests/strategy/fixtures/model_scenarios.yaml").read_text(encoding="utf-8"))
    dates = pd.bdate_range(config["start"], periods=config["periods"])
    result = {}
    for offset, symbol in enumerate(config["symbols"]):
        prices = []
        price = float(config["price"])
        for index, timestamp in enumerate(dates):
            wave = np.sin(index * config["frequency"] + offset * config["phase_step"])
            price *= 1 + config["drift"] + config["amplitude"] * wave
            prices.append(
                {
                    "symbol": symbol,
                    "timestamp": timestamp.date().isoformat(),
                    "open": price * (1 - config["open_gap"]),
                    "high": price * (1 + config["range"]),
                    "low": price * (1 - config["range"]),
                    "close": price,
                    "volume": config["volume"] * (1 + config["volume_amplitude"] * wave),
                }
            )
        result[symbol] = prices
    return result


def test_panel_time_split_has_matured_labels_and_validation_gap(bars):
    config = model_config("xgboost_rank")
    train, validation = time_split(build_panel(bars, config), config)
    assert train and validation
    assert max(row.target_date for row in train) < min(row.date for row in validation)
    assert all(row.date < row.target_date for row in train + validation)


def _drive(history, count, profile="xgboost_rank"):
    runtime = ModelStrategy(profile)
    context = {"mode": "backtest", "symbols": list(history), "metadata": {"order_type": "open"}}
    runtime.on_start(context)
    for index in range(count):
        for values in history.values():
            runtime.on_bar(values[index], context)
    return runtime


@pytest.mark.parametrize("profile,dependency,filename", PROFILE_FILES)
def test_future_changes_cannot_change_past_predictions(bars, profile, dependency, filename):
    if find_spec(dependency) is None:
        pytest.skip(f"optional backend unavailable: {dependency}")
    prefix = len(next(iter(bars.values()))) - 15
    total = len(next(iter(bars.values())))
    first = _drive(bars, total, profile)
    changed = {symbol: [dict(row) for row in rows] for symbol, rows in bars.items()}
    for rows in changed.values():
        for row in rows[prefix:]:
            row["close"] *= 3
    second = _drive(changed, total, profile)
    assert first.fits
    cutoff = next(iter(bars.values()))[prefix]["timestamp"]
    assert [row for row in first.predictions if row["date"] < cutoff] == [
        row for row in second.predictions if row["date"] < cutoff
    ]
    assert all(fit["validation_end"] <= fit["as_of"] for fit in first.fits)


def test_neural_standardization_uses_only_training_rows(bars):
    if find_spec("torch") is None:
        pytest.skip("optional torch unavailable")
    runtime = _drive(bars, 85, "mlp_ensemble")
    as_of = runtime.fits[-1]["as_of"]
    snapshot = {symbol: [row for row in rows if row["timestamp"] <= as_of] for symbol, rows in bars.items()}
    train, validation = time_split(build_panel(snapshot, runtime.config), runtime.config)
    train_mean = np.asarray([row.values for row in train]).mean(axis=0)
    all_mean = np.asarray([row.values for row in train + validation]).mean(axis=0)
    assert np.allclose(runtime.model.mean, train_mean)
    assert not np.allclose(runtime.model.mean, all_mean)


@pytest.mark.parametrize("profile,dependency,filename", PROFILE_FILES)
def test_model_strategy_import_fit_predict_and_backtest(client, monkeypatch, bars, profile, dependency, filename):
    if find_spec(dependency) is None:
        pytest.skip(f"optional backend unavailable: {dependency}")

    class PanelData:
        source_name = "synthetic-contract-test"

        def stock_detail(self, symbol, **kwargs):
            return {"kline": bars[symbol]}

    monkeypatch.setattr("src.engine.backtest.runner.DataSourceManager", PanelData)
    item = StrategyStore().import_example(f"egs/strategy_examples/{filename}", {"name": profile})
    enabled = client.post(f"/api/v1/strategies/{item['strategy_id']}/enable").json()
    assert enabled["code"] == 0
    all_dates = [row["timestamp"] for row in next(iter(bars.values()))]
    created = client.post(
        "/api/v1/backtests",
        json={
            "strategy_id": item["strategy_id"],
            "parameter_profile": (
                f"{profile}.yaml:compact" if profile == "mlp_ensemble" else f"{profile}.yaml:slower_fit"
            ),
            "params": {"quantity": 200},
            "symbols": list(bars),
            "start_date": all_dates[0],
            "end_date": all_dates[-1],
            "order_type": "open",
            "initial_capital": 1000000,
            "lot_size": 100,
            "max_position_count": 3,
        },
    ).json()
    assert created["code"] == 0, created
    task_id = created["data"]["task_id"]
    runner = BacktestRunner()
    snapshot = runner.detail(task_id)["parameter_snapshot"]
    assert snapshot["resolved_params"]["quantity"] == 200
    assert snapshot["profile"]["id"].startswith(f"{profile}.yaml:")
    assert len(snapshot["data"]["fingerprint"]) == 64
    assert snapshot["resolved_params"]["model_params"]
    metrics = runner.performance(task_id)
    report = metrics["model_diagnostics"]
    assert report["status"] == "fitted"
    assert metrics["benchmark_label"] == "标的池等权买入持有"
    assert runner.detail(task_id)["benchmark"] == metrics["benchmark_label"]
    assert report["fit_count"] > 0
    assert report["prediction_count"] > 0
    assert report["evaluated_prediction_count"] > 0
    assert np.isfinite(report["oos_mse"])
    assert report["fit_duration_ms"] > 0
    assert len(runner.equity_curve(task_id)["dates"]) == len(all_dates)
    assert all(fit["label_end"] < fit["validation_start"] <= fit["as_of"] for fit in report["fit_history"])
    trades = runner.trades(task_id, page_size=1000)["items"]
    assert trades, "scenario should exercise model-driven transactions"
    assert all(trade["order_type"] == "open" and trade["commission"] > 0 for trade in trades)


def test_model_rejects_same_day_open_assumptions():
    runtime = ModelStrategy("xgboost_rank")
    with pytest.raises(ValueError, match="open"):
        runtime.on_start({"mode": "backtest", "metadata": {"order_type": "market"}})


def test_short_sample_fails_instead_of_pretending_to_train(bars):
    runtime = _drive(bars, 10)
    with pytest.raises(Exception, match="训练样本不足"):
        runtime.on_stop({"mode": "backtest", "metadata": {}})
