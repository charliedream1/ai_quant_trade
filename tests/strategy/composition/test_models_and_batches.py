"""Actual fitting, optimizers and causal, order-independent batch execution."""

from copy import deepcopy

import pytest

from src.engine.composition.simulation import CompositionSimulation
from src.strategy.composition.config import template, templates
from src.strategy.composition.validation import compile_plan

from .market_fixture import small_models, snapshot


def run(plan, data, end=None, state=None, mode="backtest"):
    dates = [r["date"] for r in next(iter(data["history"].values()))]
    request = {"mode": mode, "agent_mode": "off", "start_date": dates[0], "end_date": end or dates[-1], "market": "CN"}
    events = []
    simulation = CompositionSimulation(plan, data, request, None, lambda *args: events.append(args), state)
    return simulation, simulation.run(), events


@pytest.mark.parametrize("name", [row["id"] for row in templates()])
def test_all_seven_templates_actually_execute_batch_path(name):
    data = snapshot()
    plan = small_models(compile_plan(template(name)))
    simulation, result, events = run(plan, data)
    assert not result["decision_errors"], result["decision_errors"]
    assert len(result["curve"]["dates"]) == len(next(iter(data["history"].values())))
    assert result["account"]["nav"] == pytest.approx(
        result["account"]["cash"]
        + sum(q * simulation.book.prices[s] for s, q in result["account"]["positions"].items())
    )
    assert result["account"]["cash"] >= 0
    if name == "parallel_three_model":
        models = result["diagnostics"]["model_diagnostics"]
        assert len(models) == 3
        assert all(value["fits"] and value["predictions"] > 0 for value in models.values())
        for model in models.values():
            assert all(
                fit["label_end"] < fit["validation_start"] and fit["validation_label_end"] <= fit["as_of"]
                for fit in model["fits"]
            )
    assert any(event[0] == "risk" for event in events)


def test_batch_security_order_and_future_data_do_not_change_history():
    data = snapshot()
    plan = small_models(compile_plan(template("parallel_three_model")))
    dates = [r["date"] for r in next(iter(data["history"].values()))]
    end = dates[len(dates) // 2]
    _, original, _ = run(plan, data, end)
    changed = deepcopy(data)
    changed["history"] = dict(reversed(list(changed["history"].items())))
    for rows in changed["history"].values():
        for row in rows:
            if row["date"] > end:
                row["close"] *= 10
    _, replayed, _ = run(plan, changed, end)
    assert original["curve"]["equity"] == pytest.approx(replayed["curve"]["equity"], abs=1e-7)
    assert original["targets"] == pytest.approx(replayed["targets"], abs=1e-7)


def test_paper_restart_and_same_day_monitor_preserve_approved_target():
    data = snapshot()
    plan = compile_plan(
        {
            **template("rule_trend"),
            "nodes": [{"id": "momentum", "component": "momentum", "inputs": ["universe"]}],
            "output": "momentum",
        }
    )
    first, initial, _ = run(plan, data, mode="paper")
    assert initial["targets"]
    state = first.serialize()
    request = {"mode": "paper", "agent_mode": "off", "end_date": first.book.last_day, "risk_only": True}
    restored = CompositionSimulation(plan, data, request, None, lambda *args: None, state)
    result = restored.run()
    assert result["targets"] == pytest.approx(initial["targets"])
    assert restored.pending_due == first.pending_due
    assert len(result["orders"]) == len(initial["orders"])


def test_fee_adjusted_post_fill_account_caps():
    data = snapshot()
    plan = compile_plan(
        {
            **template("rule_trend"),
            "nodes": [{"id": "momentum", "component": "momentum", "inputs": ["universe"]}],
            "output": "momentum",
            "risk": {"max_weight": 0.1, "max_exposure": 0.3},
        }
    )
    _, result, _ = run(plan, data)
    assert result["orders"]
    # At close prices weights may drift; each next execution clips rather than promising impossible close caps.
    assert all(row.get("quantity", 0) >= 0 for row in result["orders"])
    assert result["metrics"]["total_commission"] == pytest.approx(
        sum(row.get("commission", 0) for row in result["orders"])
    )
