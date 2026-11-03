"""Run real domain implementations over the existing explicit mock data source."""

from copy import deepcopy

import pytest

from src.engine.composition.simulation import CompositionSimulation
from src.engine.market.resource_pool import ResourcePoolService
from src.strategy.composition.config import template
from src.strategy.composition.service import PipelineService
from src.strategy.composition.validation import compile_plan

from .market_fixture import snapshot


def test_rule_run_persists_actual_events_report_and_registered_strategy(client):
    service = PipelineService()
    started = service.start(
        {
            "template": "rule_trend",
            "mode": "backtest",
            "start_date": "2026-05-04",
            "end_date": "2026-10-20",
            "agent_mode": "off",
        }
    )
    result = list(service.follow(started["id"]))[-1]["run"]
    assert result["status"] == "finished", result["result"]
    assert result["result"]["is_mock"]
    assert len(result["result"]["curve"]["dates"]) > 20
    assert service.store.artifact(started["id"], "report.html").is_file()
    assert any(row["kind"] == "stage" for row in service.store.events(started["id"]))
    version = service.store.version(result["version_id"])
    assert version["strategy_id"]


def test_http_version_preview_and_existing_backtest_bridge(client):
    definition = deepcopy(template("rule_trend"))
    preview = client.post("/api/v1/strategy-pipelines/preview", json={"definition": definition}).json()
    assert preview["code"] == 0 and not preview["data"]["training_started"]
    draft = client.post("/api/v1/strategy-pipelines", json={"definition": definition}).json()["data"]
    version = client.post(f"/api/v1/strategy-pipelines/{draft['id']}/publish").json()["data"]
    response = client.post(
        "/api/v1/backtests",
        json={
            "strategy_id": version["strategy_id"],
            "engine": "composition",
            "symbols": definition["universe"]["symbols"],
            "start_date": "2026-05-04",
            "end_date": "2026-10-20",
            "initial_capital": 1000000,
        },
    )
    value = response.json()
    assert value["code"] == 0, value
    metrics = client.get(f"/api/v1/backtests/{value['data']['task_id']}/performance").json()["data"]
    assert metrics["engine_mode"] == "composition_batch" and metrics["pipeline_version"] == version["id"]


def test_resource_pool_scope_is_applied_even_to_a_larger_frozen_snapshot(client):
    pool = ResourcePoolService().create_pool("empty composition validation")
    service = PipelineService()
    with pytest.raises(ValueError, match="empty"):
        service.start(
            {"template": "rule_trend", "resource_pool_id": pool["id"], "mode": "targets", "agent_mode": "off"}
        )
    data = snapshot()
    day = max(row["date"] for rows in data["history"].values() for row in rows)
    symbols = ["000001", "600036"]
    plan = compile_plan(template("rule_trend"))
    simulation = CompositionSimulation(
        plan,
        data,
        {"mode": "targets", "agent_mode": "off", "end_date": day, "symbols": symbols, "resource_pool_id": pool["id"]},
        None,
        lambda *args: None,
    )
    result = simulation.run()
    assert all(row["input_count"] <= len(symbols) for row in result["diagnostics"]["stages"])
    assert set(result["targets"]) <= set(symbols)
    # ETF children have no intersection with this stock-only resource pool.
    plan = compile_plan(template("multi_sleeve"))
    simulation = CompositionSimulation(
        plan,
        data,
        {"mode": "targets", "agent_mode": "off", "end_date": day, "symbols": symbols, "resource_pool_id": pool["id"]},
        None,
        lambda *args: None,
    )
    assert set(simulation.run()["targets"]) <= set(symbols)
