"""Actual HTTP and real ledger checks; LLM-only portions are explicit test doubles."""

from threading import Event
from time import monotonic

import pandas as pd


def data(client, kind, payload):
    response = client.post("/api/v1/alpha/datasets", json={"name": "隔离测试", "kind": kind, "payload": payload}).json()
    assert response["code"] == 0, response
    return response["data"]["id"]


def create(client, dataset_id, policy, **overrides):
    response = client.post(
        "/api/v1/alpha/studies",
        json={
            "name": "隔离研究",
            "dataset_id": dataset_id,
            "batch_size": 1,
            "models": {"default": {"model_id": 1}},
            "policy": policy,
            **overrides,
        },
    ).json()
    assert response["code"] == 0, response
    return response["data"]["id"]


def wait(client, study_id):
    deadline = monotonic() + 40
    while True:
        response = client.get(f"/api/v1/alpha/studies/{study_id}").json()
        assert response["code"] == 0, response
        result = response["data"]
        if result["status"] not in {"discovering", "validating", "testing"}:
            return result
        assert monotonic() < deadline, result
        Event().wait(0.02)


def test_three_roles_actual_ledger_and_immutable_validation(client, fixture_llm, market_payload, workflow_fixture):
    dataset = data(client, "market", market_payload)
    study = create(client, dataset, workflow_fixture["policy"])
    assert client.post(f"/api/v1/alpha/studies/{study}/actions", json={"action": "discover"}).json()["code"] == 0
    discovered = wait(client, study)
    assert discovered["status"] == "discovered", discovered
    assert len(discovered["candidates"]) == 1 and discovered["candidates"][0]["status"] == "implemented"
    assert client.post(f"/api/v1/alpha/studies/{study}/seal").json()["code"] == 0
    response = client.post(
        f"/api/v1/alpha/studies/{study}/candidates",
        json={"hypothesis": workflow_fixture["idea"]["ideas"][0], "implementation": workflow_fixture["implement"]},
    ).json()
    assert response["code"] != 0
    assert client.post(f"/api/v1/alpha/studies/{study}/actions", json={"action": "validate"}).json()["code"] == 0
    finished = wait(client, study)
    assert finished["status"] == "validated", finished
    summary = finished["result"]["validation"][0]
    assert "error" not in summary, summary
    assert summary["technical"]["passed"] and "trade_count" in summary["metrics"]
    assert summary["evaluator"]["verdict"] == "approve"
    assert summary["passed"] == all(summary["gates"].values())
    assert finished["event_chain_valid"] and finished["result"]["family_tests"] == 2
    assert client.post(f"/api/v1/alpha/studies/{study}/actions", json={"action": "validate"}).json()["code"] != 0
    assert client.post(f"/api/v1/alpha/studies/{study}/export", json={}).json()["code"] != 0
    report = client.get(f"/api/v1/alpha/studies/{study}/files/report.html")
    assert report.status_code == 200 and "调整后p值" in report.text
    stream = client.get(f"/api/v1/alpha/studies/{study}/stream")
    assert '"type": "result"' in stream.text
    assert {row["role"] for row in fixture_llm.calls} == {"idea", "implement", "evaluate"}
    raw = client.get(f"/api/v1/alpha/studies/{study}/files/{summary['artifact']}").json()
    for key in ("strategy", "baseline"):
        metrics = raw["backtest"][key]["metrics"]
        assert metrics["execution_costs"]["sha256"] == finished["config"]["execution_costs"]["sha256"]


def test_theme_quotes_and_date_filtering(client, fixture_llm, workflow_fixture):
    dataset = data(client, "documents", {"documents": workflow_fixture["documents"], "is_mock": True})
    study = create(
        client, dataset, workflow_fixture["policy"], mode="theme", theme="云计算", cutoff="2019-05-01T00:00:00+00:00"
    )
    assert client.post(f"/api/v1/alpha/studies/{study}/actions", json={"action": "run"}).json()["code"] == 0
    result = wait(client, study)
    assert result["status"] == "completed", result
    assert result["result"]["frozen_symbols"] == ["AAA"]
    assert not result["result"]["export_ready"] and not result["result"]["direct_trading_signal"]
    assert result["result"]["comparisons"]["llm_refined"]["scores"]["AAA"] == 1


def test_anonymous_regime_independent_configurations(client, fixture_llm, workflow_fixture):
    dataset = data(client, "macro", {"observations": workflow_fixture["macro"], "is_mock": True})
    study = create(
        client,
        dataset,
        workflow_fixture["policy"],
        mode="regime",
        cutoff="2019-05-01T00:00:00+00:00",
        configurations=[{"model_id": 1}, {"model_id": 2}],
        asset_mapping={"equity": "AAA", "bond": "BBB"},
    )
    assert client.post(f"/api/v1/alpha/studies/{study}/actions", json={"action": "run"}).json()["code"] == 0
    result = wait(client, study)
    assert result["status"] == "completed", result
    assert result["result"]["configured_count"] == 2 and not result["result"]["failures"]
    decisions = result["result"]["decisions"]
    assert all(row["regime"] == "Goldilocks" and row["weights"] == {"AAA": 0.7, "BBB": 0.3} for row in decisions)
    assert all(row["validation_mode"] == "historical_replay" for row in decisions)
    for call in fixture_llm.calls:
        assert (
            "2019" not in call["prompt"] and "vintage_at" not in call["prompt"] and "available_at" not in call["prompt"]
        )


def test_eight_configuration_capacity_without_paid_calls(client, fixture_llm, workflow_fixture):
    dataset = data(client, "macro", {"observations": workflow_fixture["macro"], "is_mock": True})
    study = create(
        client,
        dataset,
        workflow_fixture["policy"],
        mode="regime",
        cutoff="2019-05-01T00:00:00+00:00",
        configurations=[{"model_id": index} for index in range(1, 9)],
        asset_mapping={"equity": "AAA", "bond": "BBB"},
    )
    response = client.post(f"/api/v1/alpha/studies/{study}/actions", json={"action": "run"}).json()
    assert response["code"] == 0, response
    result = wait(client, study)
    assert result["status"] == "completed" and result["result"]["configured_count"] == 8
    assert len(result["result"]["decisions"]) == 8 and not result["result"]["failures"]
    assert len(fixture_llm.calls) == 16


def test_import_validation_and_cross_origin_protection(client):
    response = client.post(
        "/api/v1/alpha/datasets/upload?kind=market",
        files={"file": ("empty.csv", b"symbol,date,open,high,low,close,volume\n")},
    ).json()
    assert response["code"] != 0
    assert client.get("/api/v1/alpha/templates/macro").status_code == 200
    response = client.post("/api/v1/alpha/studies", headers={"Origin": "https://untrusted.example"}, json={}).json()
    assert response["code"] != 0


def test_regime_configurations_use_actual_paired_books(client, fixture_llm, market_payload, workflow_fixture):
    macro_id = data(client, "macro", {"observations": workflow_fixture["macro"], "is_mock": True})
    for rows in market_payload["history"].values():
        base = rows[0]["open"]
        for index, (day, row) in enumerate(
            zip(
                pd.bdate_range(workflow_fixture["regime_market_start"], periods=len(rows)).strftime("%Y-%m-%d"),
                rows,
                strict=True,
            )
        ):
            row["date"] = day
            price = (
                base
                + index * workflow_fixture["regime_price_step"]
                + (index % workflow_fixture["regime_wave_period"]) * workflow_fixture["regime_price_wave"]
            )
            row.update(open=price, close=price, high=price + 1, low=price - 1)
    market_id = data(client, "market", market_payload)
    study = create(
        client,
        macro_id,
        workflow_fixture["policy"],
        mode="regime",
        market_dataset_id=market_id,
        cutoff=workflow_fixture["regime_cutoff"],
        decision_dates=workflow_fixture["regime_decisions"],
        configurations=[{"model_id": 1}],
        asset_mapping={"equity": "AAA", "bond": "BBB"},
    )
    response = client.post(f"/api/v1/alpha/studies/{study}/actions", json={"action": "run"}).json()
    assert response["code"] == 0, response
    result = wait(client, study)
    assert result["status"] == "completed", result
    comparison = result["result"]["comparisons"]
    assert "configurations" in comparison, comparison
    paired = comparison["configurations"]["1"]
    assert paired["strategy"]["curve"]["dates"] == paired["baseline"]["curve"]["dates"]
    assert paired["strategy"]["metrics"]["trade_count"] > 0
    assert (
        paired["strategy"]["metrics"]["execution_costs"]["sha256"]
        == paired["baseline"]["metrics"]["execution_costs"]["sha256"]
    )
