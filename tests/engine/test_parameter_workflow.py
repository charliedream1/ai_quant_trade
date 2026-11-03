"""Exercise YAML selection, API/UI execution and immutable experiment evidence."""

from __future__ import annotations

import json

import pytest

from src.engine.backtest import BacktestRunner
from src.frontend.services import FrontendService
from src.strategy import StrategyStore


@pytest.fixture
def strategy(client):
    return StrategyStore().import_example(
        "egs/strategy_examples/standard_port_strategy.py",
        {"name": "parameter_workflow", "default_params": {"min_change_pct": 0, "quantity": 200}},
    )


def _payload(strategy_id):
    return {
        "strategy_id": strategy_id,
        "symbols": ["600519", "300750"],
        "start_date": "2026-01-05",
        "end_date": "2026-01-16",
        "initial_capital": 1000000,
        "commission_rate": 0,
        "lot_size": 100,
    }


@pytest.mark.parametrize("overrides", [None, {}])
def test_api_runs_saved_defaults_in_constructor_and_event_context(client, strategy, overrides):
    payload = _payload(strategy["id"])
    if overrides is not None:
        payload["params"] = overrides
    response = client.post("/api/v1/backtests", json=payload).json()
    assert response["code"] == 0, response
    task = response["data"]
    snapshot = task["parameter_snapshot"]
    assert task["params"]["quantity"] == 200
    assert snapshot["resolved_params"] == {"min_change_pct": 0, "quantity": 200}
    assert snapshot["run"]["commission_rate"] == task["commission_rate"] == 0
    trades = BacktestRunner().trades(task["id"])["items"]
    assert trades and all(trade["quantity"] == 200 and trade["commission"] == 0 for trade in trades)
    assert len(snapshot["data"]["fingerprint"]) == 64
    assert snapshot["data"]["equity_points"] == 10
    assert snapshot["data"]["bars_by_symbol"] == {"600519": 10, "300750": 10}
    assert snapshot["data"]["source"] == "mock-local"
    assert "_experiment" not in task["params"]


def test_scheme_preview_matches_api_run_and_persisted_snapshot(client, strategy):
    profile = "standard_momentum.yaml:strict"
    options = client.get(f"/api/v1/strategies/{strategy['id']}/parameter-profiles").json()["data"]
    assert profile in [item["id"] for item in options]
    settings = {"params": {"quantity": 300, "min_change_pct": 0}, "parameter_profile": profile}
    preview = client.post(f"/api/v1/strategies/{strategy['id']}/resolve-params", json=settings).json()
    assert preview["code"] == 0, preview
    assert "source" not in preview["data"]
    result = client.post("/api/v1/backtests", json={**_payload(strategy["id"]), **settings}).json()
    assert result["code"] == 0, result
    task = result["data"]
    saved = task["parameter_snapshot"]
    assert saved["resolved_params"] == preview["data"]["resolved_params"]
    assert saved["profile"]["id"] == profile
    assert saved["layers"]["profile_params"] == {"min_change_pct": 0.02}
    store = StrategyStore()
    store.repo.update("strategies", strategy["id"], {"name": "changed_name", "param_schema": {"quantity": 900}})
    assert BacktestRunner().detail(task["id"])["parameter_snapshot"] == saved
    snapshot_text = FrontendService().backtest_param_snapshot(task["id"])
    assert "parameter_workflow" in snapshot_text and "changed_name" not in snapshot_text
    listed = BacktestRunner().list()["items"][0]
    assert listed["parameter_snapshot"] == saved
    assert "_experiment" not in listed["params"]


def test_frontend_regular_and_quick_paths_share_resolution(client, strategy):
    ui = FrontendService()
    preview, _ = ui.preview_strategy_parameters(strategy["id"], "{}")
    normal = ui.create_backtest(strategy["id"], "600519,300750", "2026-01-05", "2026-01-16", 1000000, "{}")
    quick = ui.strategy_quick_backtest(strategy["id"], "600519,300750", "2026-01-05", "2026-01-16", 1000000, "{}")
    assert json.loads(ui.backtest_resolved_parameters(normal[1])[0]) == json.loads(preview)
    assert "parameter_snapshot" not in normal[2].columns
    assert json.loads(ui.backtest_resolved_parameters(quick[1])[0]) == json.loads(preview)
    assert (
        BacktestRunner().detail(normal[1])["parameter_snapshot"]["data"]["fingerprint"]
        == BacktestRunner().detail(quick[1])["parameter_snapshot"]["data"]["fingerprint"]
    )


def test_invalid_input_is_business_error_and_does_not_create_task(client, strategy):
    for extra in ({"params": []}, {"params": {"_backtest": {}}}, {"parameter_profile": "rsi.yaml:strict"}):
        result = client.post("/api/v1/backtests", json={**_payload(strategy["id"]), **extra}).json()
        assert result["code"] == 1002, result
    assert BacktestRunner().list()["total"] == 0


def test_old_tasks_are_readable_without_claiming_full_snapshot(client, strategy):
    runner = BacktestRunner()
    task = runner.create(_payload(strategy["id"]))
    runner.repo.update(
        "backtest_tasks", task["id"], {"params": {"quantity": 100, "_backtest": {"order_type": "market"}}}
    )
    assert runner.detail(task["id"])["parameter_snapshot"] is None
    params, note = FrontendService().backtest_resolved_parameters(task["id"])
    assert json.loads(params) == {"quantity": 100}
    assert "未保存完整" in note


def test_saved_execution_settings_match_engine_normalization(client, strategy):
    task = BacktestRunner().create(
        {**_payload(strategy["id"]), "order_type": "OPEN", "price_adjustment": "forward", "max_position_weight": 2}
    )
    execution = task["parameter_snapshot"]["run"]
    metrics = BacktestRunner().performance(task["id"])
    assert execution["order_type"] == metrics["order_type"] == "open"
    assert execution["price_adjustment"] == metrics["price_adjustment"] == "qfq"
    assert execution["max_position_weight"] == metrics["max_position_weight"] == 1
