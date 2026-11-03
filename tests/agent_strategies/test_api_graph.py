"""HTTP, independent CLI and physical graph execution share actual domain services."""

from copy import deepcopy
from threading import Event
from time import monotonic

from src.agent_strategies.service import AgentStrategyService
from src.engine.composition.simulation import CompositionSimulation
from src.strategy.composition.config import template
from src.strategy.composition.store import PipelineStore
from src.strategy.composition.validation import compile_plan

from .conftest import FIXTURE, FixtureLLM


def wait(client, run_id):
    deadline = monotonic() + 20
    while True:
        response = client.get(f"/api/v1/agent-strategies/runs/{run_id}").json()
        assert response["code"] == 0, response
        run = response["data"]
        if run["status"] in {"completed", "partial", "failed", "cancelled"}:
            return run
        assert monotonic() < deadline, run
        Event().wait(0.01)


def test_actual_http_run_report_scores_sse_and_cross_origin(client, workflow_data, monkeypatch):
    monkeypatch.setattr("src.agent_strategies.session.LLMClient", FixtureLLM)
    response = client.post(
        "/api/v1/agent-strategies/runs",
        json={
            "recipe": "contest_event",
            "market_dataset_id": workflow_data["market_id"],
            "documents_dataset_id": workflow_data["documents_id"],
            "as_of": workflow_data["days"][-1],
            "validation_mode": "historical_research",
            "model_id": 1,
        },
    ).json()
    assert response["code"] == 0, response
    run = wait(client, response["data"]["id"])
    assert run["status"] == "completed", run
    assert run["result"]["cold_start"] and not run["result"]["targets"]
    assert client.get(f"/api/v1/agent-strategies/runs/{run['id']}/scores").json()["code"] == 0
    report = client.get(f"/api/v1/agent-strategies/runs/{run['id']}/files/report.html")
    assert report.status_code == 200 and "数据竞赛" in report.text and "研究预算" in report.text
    streamed = client.get(f"/api/v1/agent-strategies/runs/{run['id']}/stream")
    assert '"llm_response"' in streamed.text and '"type": "result"' in streamed.text
    store = AgentStrategyService().store
    for index in range(305):
        store.event(run["id"], "explicit-pagination-fixture", {"index": index})
    paged = client.get(f"/api/v1/agent-strategies/runs/{run['id']}/stream")
    assert '"index": 304' in paged.text
    assert paged.text.index('"index": 304') < paged.text.index('"type": "result"')
    rejected = client.post(
        "/api/v1/agent-strategies/runs", headers={"Origin": "https://untrusted.example"}, json={}
    ).json()
    assert rejected["code"] != 0


def test_independent_cli_catalog_and_run(cli_command, workflow_data, monkeypatch):
    monkeypatch.setattr("src.agent_strategies.session.LLMClient", FixtureLLM)
    catalog = cli_command("agent-strategy", "recipes")
    assert catalog["code"] == 0
    result = cli_command(
        "agent-strategy",
        "start",
        "--recipe",
        "cn_event",
        "--market-dataset-id",
        workflow_data["market_id"],
        "--documents-dataset-id",
        workflow_data["documents_id"],
        "--as-of",
        workflow_data["days"][-1],
        "--validation-mode",
        "historical_research",
        "--model-id",
        1,
    )
    assert result["code"] == 0, result
    run_id = result["data"]["id"]
    stream = cli_command("agent-strategy", "watch", run_id, stream=True)
    assert stream[-1]["data"]["data"]["status"] == "completed"
    file = cli_command("agent-strategy", "file", run_id, "result.json")
    assert file["code"] == 0 and file["data"]["download_url"]


def test_graph_debate_affects_real_fills_and_baseline_has_no_model_calls(client, workflow_data, monkeypatch):
    fake = FixtureLLM()
    monkeypatch.setattr("src.agent_strategies.session.LLMClient", lambda **kwargs: fake)
    plan = compile_plan(template("agent_cn_event"), {"universe": {"symbols": list(workflow_data["history"])}})
    snapshot = {
        "history": workflow_data["history"],
        "metadata": workflow_data["metadata"],
        "source": "explicit-test-fixture",
        "is_mock": True,
        "market": "CN",
    }
    request = {
        "mode": "backtest",
        "market": "CN",
        "agent_mode": "research",
        "model_id": 1,
        "backend": "api",
        "start_date": workflow_data["days"][40],
        "end_date": workflow_data["days"][48],
        "agent_documents_dataset_id": workflow_data["documents_id"],
        "execution_costs": {"profile": "cn_a"},
    }
    actual = CompositionSimulation(plan, snapshot, request, PipelineStore(), lambda *args: None).run()
    assert not actual["decision_errors"], actual["decision_errors"]
    assert actual["metrics"]["trade_count"] > 0
    assert set(actual["targets"]) <= {FIXTURE["model"]["selections"]["chair"]}
    calls = len(fake.calls)
    baseline = CompositionSimulation(
        plan, snapshot, {**request, "agent_mode": "off"}, PipelineStore(), lambda *args: None
    ).run()
    assert len(fake.calls) == calls and baseline["metrics"]["trade_count"] > 0
    assert actual["metrics"]["execution_costs"]["sha256"] == baseline["metrics"]["execution_costs"]["sha256"]
    assert not actual["metrics"]["execution_costs"]["minimum_commission"] < 0


def test_parallel_sleeves_compile_without_budget_to_score_edges():
    a = template("agent_cn_event")
    b = template("agent_contest_event")
    plan = {
        "name": "explicit-parallel-budget-test",
        "schema_version": 1,
        "sleeves": [
            {"id": "debate", "budget": 0.5, "definition": a},
            {"id": "contest", "budget": 0.5, "definition": b},
        ],
        "portfolio": {"component": "fixed_budget"},
        "variants": {"baseline": {}},
    }
    compiled = compile_plan(deepcopy(plan))
    assert len(compiled["sleeves"]) == 2


def test_historical_pipeline_call_cap_is_shared_across_dates(client, workflow_data, monkeypatch):
    fake = FixtureLLM()
    monkeypatch.setattr("src.agent_strategies.session.LLMClient", lambda **kwargs: fake)
    plan = compile_plan(template("agent_cn_event"), {"universe": {"symbols": list(workflow_data["history"])}})
    snapshot = {
        "history": workflow_data["history"],
        "metadata": workflow_data["metadata"],
        "source": "explicit-test-fixture",
        "is_mock": True,
        "market": "CN",
    }
    request = {
        "mode": "backtest",
        "market": "CN",
        "agent_mode": "research",
        "model_id": 1,
        "backend": "api",
        "start_date": workflow_data["days"][40],
        "end_date": workflow_data["days"][70],
        "agent_documents_dataset_id": workflow_data["documents_id"],
        "agent_strategy_options": {"calls": 12},
        "execution_costs": {"profile": "cn_a"},
    }
    result = CompositionSimulation(plan, snapshot, request, PipelineStore(), lambda *args: None).run()
    assert result["agent_model_budget"] == {"used": 12, "limit": 12}
    assert len(fake.calls) == 12 and result["decision_errors"]
