"""Cash, chronology, graph and independent analytical reference cases."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.engine.backtest.engines import _buy_quantity
from src.engine.composition.book import PortfolioBook
from src.engine.composition.execution import execute_targets
from src.portfolio.allocation import allocate
from src.risk.policies import RiskManager
from src.strategy import StrategySignal
from src.strategy.components.ensemble import combine
from src.strategy.components.rules import evaluate
from src.strategy.composition.config import config, templates
from src.strategy.composition.contracts import Frame, Observation
from src.strategy.composition.validation import compile_plan, settings

DATA = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("core.yaml").read_text(encoding="utf-8"))


def frame(day=None):
    return Frame.create(
        day or DATA["rows"][-1]["date"],
        {
            "AAA": DATA["rows"],
            "BBB": [
                {**r, "close": r["close"] / 2, "open": r["open"] / 2, "high": r["high"] / 2, "low": r["low"] / 2}
                for r in DATA["rows"]
            ],
        },
    )


def test_templates_and_graph_contracts():
    assert {"factor_equal", "factor_icir", "factor_model_groups"} <= {row["id"] for row in templates()}
    for row in templates():
        assert compile_plan(row["definition"])["name"]
    base = templates()[-1]["definition"]
    with pytest.raises(ValueError):
        compile_plan(
            {
                **base,
                "nodes": [
                    {"id": "A", "component": "trend", "inputs": ["B"]},
                    {"id": "B", "component": "trend", "inputs": ["A"]},
                ],
                "output": "A",
            }
        )
    with pytest.raises(ValueError):
        compile_plan(base, {"risk": {"max_weight": float("nan")}})


def test_cash_fees_and_settlement():
    book = PortfolioBook(DATA["capital"], DATA["budgets"])
    book.advance(DATA["rows"][1]["date"])
    book.prices.update(DATA["prices"])
    policy = settings("execution", DATA["execution"])
    targets = {"trend": {"AAA": 0.4}, "reversion": {"BBB": 0.3}}
    opens = {"AAA": {"open": 100}, "BBB": {"open": 50}}
    result = execute_targets(book, targets, DATA["budgets"], opens, frame(DATA["rows"][0]["date"]), policy)
    assert book.positions() == {"AAA": 400, "BBB": 600}
    assert book.cash() == pytest.approx(29930)
    assert book.nav() == pytest.approx(DATA["capital"] - result["fees"])
    closing = execute_targets(book, {"trend": {}, "reversion": {}}, DATA["budgets"], opens, frame(), policy)
    assert not closing["trades"] and book.positions() == {"AAA": 400, "BBB": 600}
    book.advance(DATA["rows"][2]["date"])
    closing = execute_targets(book, {"trend": {}, "reversion": {}}, DATA["budgets"], opens, frame(), policy)
    assert not book.positions()
    assert book.cash() == pytest.approx(99860)
    assert sum(row["pnl"] for row in closing["trades"]) == pytest.approx(-140)


def test_internal_crossing_is_not_double_broker_turnover():
    book = PortfolioBook(DATA["capital"], {"one": 0.5, "two": 0.5})
    book.prices["AAA"] = 100
    book.advance(DATA["rows"][0]["date"])
    book.sleeves["one"].fill("AAA", 100, 100, 0, book.session, 0, book.last_day, "market")
    before = book.nav()
    policy = settings("execution", {**DATA["execution"], "commission_rate": 0})
    result = execute_targets(
        book, {"one": {}, "two": {"AAA": 0.1}}, {"one": 0.5, "two": 0.5}, {"AAA": {"open": 100}}, frame(), policy
    )
    assert book.positions() == {"AAA": 100}
    assert book.nav() == before
    assert result["turnover"] == 0 and len(result["internal_transfers"]) == 1
    assert book.sleeves["two"].quantity("AAA") == 100


def test_missing_bar_never_uses_another_date_to_fill():
    book = PortfolioBook(DATA["capital"], {"main": 1})
    book.prices["AAA"] = 100
    book.advance(DATA["rows"][0]["date"])
    result = execute_targets(
        book, {"main": {"AAA": 0.5}}, {"main": 1}, {}, frame(), settings("execution", DATA["execution"])
    )
    assert not book.positions() and result["orders"][0]["status"] == "deferred"


def test_no_future_rows_and_no_current_bar_donchian_threshold():
    first = frame(DATA["rows"][3]["date"])
    assert len(first.history["AAA"]) == 4
    mutable = frame().mutable_history()
    mutable["AAA"][-1]["close"] *= 100
    altered = Frame.create(first.as_of, mutable)
    params = {"window": 2, "threshold": 0.0}
    a = evaluate("donchian", ["AAA"], first, params)["AAA"]
    b = evaluate("donchian", ["AAA"], altered, params)["AAA"]
    assert a == b
    assert a.evidence["prior_high"] == 103


def test_ensemble_abstention_semantics_and_stable_ranking():
    rows = {s: Observation(s, v) for s, v in {"AAA": 1, "BBB": 2}.items()}
    config_params = config()["components"]["rank"]["defaults"]
    result = combine("rank", [rows, {}], {**config_params, "minimum": 2})
    assert all(row.status != "pass" for row in result.values())
    with pytest.raises(ValueError):
        combine("rank", [rows, {s: replace(row, horizon=5) for s, row in rows.items()}], config_params)
    ordered = combine("rank", [rows, dict(reversed(list(rows.items())))], config_params)
    assert ordered["BBB"].value == 1 and ordered["AAA"].value == 0


def test_equal_portfolio_caps_leave_cash_and_zero_vol_is_explicit():
    rows = {s: Observation(s, 1) for s in ("AAA", "BBB")}
    params = settings("portfolio", {"max_weight": 0.2})
    weights, detail = allocate("equal", rows, frame(), params)
    assert weights == {"AAA": 0.2, "BBB": 0.2} and detail["cash"] == pytest.approx(0.6)
    with pytest.raises(ValueError):
        allocate("inverse_volatility", rows, frame(), params)


def test_erc_reference_for_uncorrelated_two_asset_case(monkeypatch):
    import pandas as pd

    import src.portfolio.allocation as module

    values = np.asarray([[1, 2], [-1, 2], [1, -2], [-1, -2]], dtype=float) / 100
    panel = pd.DataFrame(values, columns=["AAA", "BBB"])
    monkeypatch.setattr(module, "returns_panel", lambda *args: panel)
    weights, detail = allocate(
        "erc",
        {s: Observation(s, 1) for s in panel.columns},
        frame(),
        settings("portfolio", {"max_weight": 1, "exposure": 1, "shrinkage": 0.0}),
    )
    assert weights["AAA"] == pytest.approx(2 / 3, abs=0.001)
    assert weights["BBB"] == pytest.approx(1 / 3, abs=0.001)
    assert detail["solver"]["success"]


def test_risk_clipping_does_not_renormalize_and_freeze_survives_restart():
    book = PortfolioBook(DATA["capital"], {"main": 1})
    book.prices.update(DATA["prices"])
    book.advance(DATA["rows"][0]["date"])
    params = settings("risk", {"max_weight": 0.1, "max_exposure": 0.5, "min_covariance_observations": 2})
    risk = RiskManager(params)
    target, detail = risk.evaluate({"AAA": 0.8, "BBB": 0.2}, frame(), book)
    assert sum(target.values()) <= 0.2 and detail["cash_target"] >= 0.8
    risk.state["drawdown_latched"] = True
    restored = RiskManager(params, risk.state)
    target, detail = restored.evaluate({"AAA": 0.5}, frame(), book)
    assert detail["frozen"] and not any(target.values())


@pytest.mark.parametrize("rule", ["stop_loss", "trailing_stop", "time_exit"])
def test_existing_holding_exits_even_when_research_candidate_is_empty(rule):
    book = PortfolioBook(DATA["capital"], {"main": 1})
    book.advance(DATA["rows"][0]["date"])
    book.prices["AAA"] = 100
    book.sleeves["main"].fill("AAA", 800, 100, 0, book.session, 0, book.last_day, "market")
    params = settings(
        "risk",
        {
            "max_drawdown": 0,
            "daily_loss": 0,
            "atr_multiple": 0,
            "stop_loss": 0.1 if rule == "stop_loss" else 0,
            "trailing_stop": 0.1 if rule == "trailing_stop" else 0,
            "max_holding_sessions": 1 if rule == "time_exit" else 0,
        },
    )
    risk = RiskManager(params)
    risk.evaluate({}, frame(), book)
    book.advance(DATA["rows"][1]["date"])
    book.prices["AAA"] = 80
    targets, evidence = risk.evaluate({}, frame(), book)
    assert targets["AAA"] == 0 and "AAA" in evidence["emergency"]
    exits = [event for event in evidence["events"] if event["rule"] == "exit"]
    assert exits and exits[0]["checks"][rule]


def test_sector_and_asset_class_caps_leave_cash():
    book = PortfolioBook(DATA["capital"], {"main": 1})
    book.prices.update(DATA["prices"])
    book.advance(DATA["rows"][0]["date"])
    current = frame()
    meta = {s: {"sector": "same", "asset_class": "stock", "available_at": current.as_of} for s in ("AAA", "BBB")}
    current = Frame.create(current.as_of, current.mutable_history(), meta)
    params = settings(
        "risk",
        {
            "max_weight": 1,
            "max_exposure": 1,
            "max_sector_weight": 0.3,
            "max_asset_class_weight": 0.25,
            "target_volatility": 0,
            "min_covariance_observations": 2,
        },
    )
    targets, detail = RiskManager(params).evaluate({"AAA": 0.5, "BBB": 0.5}, current, book)
    assert sum(targets.values()) == pytest.approx(0.25)
    assert {row["rule"] for row in detail["events"]} >= {"sector_limit", "asset_class_limit"}


def test_daily_loss_baseline_does_not_reset_on_same_day_monitoring():
    book = PortfolioBook(DATA["capital"], {"main": 1})
    book.advance(DATA["rows"][0]["date"])
    book.prices["AAA"] = 100
    book.sleeves["main"].fill("AAA", 800, 100, 0, book.session, 0, book.last_day, "market")
    risk = RiskManager(settings("risk", {"max_drawdown": 0, "daily_loss": 0.05}))
    risk.evaluate({}, frame(), book)
    book.advance(DATA["rows"][1]["date"])
    book.prices["AAA"] = 80
    _, first = risk.evaluate({"AAA": 0.8}, frame(), book)
    _, second = risk.evaluate({"AAA": 0.8}, frame(), book)
    assert first["frozen"] and second["frozen"]
    assert first["daily_return"] == second["daily_return"] == pytest.approx(-0.16)


def test_explicit_legacy_quantity_cannot_bypass_weight_cap():
    signal = StrategySignal(symbol="AAA", side="buy", quantity=10000)
    quantity = _buy_quantity(
        DATA["capital"], signal, 100, 0, {"initial_capital": DATA["capital"], "max_position_weight": 0.1, "lot_size": 1}
    )
    assert quantity == 100
