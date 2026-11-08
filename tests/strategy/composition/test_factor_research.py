"""Analytical references, time isolation and end-to-end factor composition."""

import sqlite3
from contextlib import closing
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from src.core.config import PROJECT_ROOT
from src.engine.composition.simulation import CompositionSimulation
from src.engine.research.factor_monitor import _icir, _pearson, _spearman
from src.frontend.service.graph_evidence import evidence
from src.strategy.composition.config import template
from src.strategy.composition.contracts import Frame
from src.strategy.composition.runtime import PipelineRuntime
from src.strategy.composition.service import PipelineService
from src.strategy.composition.store import source_manifest
from src.strategy.composition.validation import compile_plan, digest
from src.strategy.factors.cache import FactorCache
from src.strategy.factors.config import factor_config, factor_set
from src.strategy.factors.panel import FactorPanel, PanelBuilder, build_panel, factor_value, preprocess
from src.strategy.factors.research import analyze, forward_labels, select
from src.strategy.factors.scoring import capped_weights, score
from src.strategy.models.config import model_config
from src.strategy.models.features import build_panel as model_panel
from src.strategy.models.features import time_split

from .market_fixture import small_models, snapshot


def current(data, index=-1):
    day = next(iter(data["history"].values()))[index]["date"]
    return Frame.create(day, data["history"], data.get("metadata"))


def test_factor_values_match_independent_price_and_volume_reference():
    data = snapshot()
    rows = data["history"]["000001"][-21:]
    definitions = factor_set("balanced")
    close = np.asarray([row["close"] for row in rows])
    assert factor_value(rows, definitions["momentum_20d"]) == pytest.approx(close[-1] / close[0] - 1)
    assert factor_value(rows, definitions["reversal_5d"]) == pytest.approx(1 - close[-1] / close[-6])
    assert factor_value(rows, definitions["low_vol_20d"]) == pytest.approx(-np.std(np.diff(close) / close[:-1]))
    assert factor_value(rows, definitions["volume_trend"]) == 0
    assert factor_value(rows[:3], definitions["momentum_20d"]) is None
    broken = deepcopy(rows)
    broken[-1]["volume"] = None
    assert factor_value(broken, definitions["volume_trend"]) is None


def test_preprocess_is_cross_sectional_and_preserves_missing_and_ties():
    index = pd.MultiIndex.from_product([["2026-01-01", "2026-01-02"], ["A", "B", "C", "D"]], names=["date", "symbol"])
    values = pd.DataFrame({"x": [1, 2, 2, 1000, 10, 20, 20, 10000], "missing": [1, None, None, None] * 2}, index=index)
    panel = FactorPanel(values, {}, {})
    params = {"method": "rank", "min_assets": 3, "winsor_quantile": 0}
    result = preprocess(panel, params).values
    assert result.loc["2026-01-01", "x"].tolist() == pytest.approx([0, 0.5, 0.5, 1])
    assert result["missing"].isna().all()
    assert result.loc["2026-01-01", "x"].tolist() == result.loc["2026-01-02", "x"].tolist()
    constant = FactorPanel(pd.DataFrame({"x": [5] * 8}, index=index), {}, {})
    assert (preprocess(constant, {**params, "method": "zscore"}).values["x"] == 0).all()


def test_labels_require_exact_shared_dates_and_matured_end():
    data = snapshot()
    frame = current(data, 45)
    labels = forward_labels(dict(frame.history), 5, frame.as_of)
    assert max(labels["label_end"]) <= frame.as_of
    first = frame.history["000001"][0]
    expected = frame.history["000001"][5]["close"] / first["close"] - 1
    assert labels.loc[(first["date"], "000001"), "target"] == pytest.approx(expected)
    missing = frame.mutable_history()
    missing["000001"].pop(5)
    assert (first["date"], "000001") not in forward_labels(missing, 5, frame.as_of).index


@pytest.mark.parametrize("name", ["factor_equal", "factor_icir", "factor_model_groups"])
def test_new_templates_compile_and_actually_backtest(name):
    data = snapshot()
    plan = small_models(compile_plan(template(name)))
    dates = [row["date"] for row in next(iter(data["history"].values()))]
    request = {"mode": "backtest", "agent_mode": "off", "start_date": dates[0], "end_date": dates[-1], "market": "CN"}
    simulation = CompositionSimulation(plan, data, request, None, lambda *args: None)
    result = simulation.run()
    assert not result["decision_errors"], result["decision_errors"]
    assert result["trades"]
    assert result["account"]["cash"] >= 0
    assert result["account"]["nav"] == pytest.approx(
        result["account"]["cash"]
        + sum(quantity * simulation.book.prices[symbol] for symbol, quantity in result["account"]["positions"].items())
    )
    diagnostics = result["diagnostics"]
    if name == "factor_model_groups":
        models = diagnostics["model_diagnostics"]
        assert len(models) == 3
        assert all(model["fits"] and model["predictions"] for model in models.values())
        assert {model["fits"][-1]["feature_set"] for model in models.values()} == {"trend", "defensive", "balanced"}
    else:
        assert diagnostics["factor_diagnostics"]["factors"]["computed"] > 0


def test_future_prices_and_future_cache_cannot_change_historical_results(tmp_path):
    data = snapshot()
    frame = current(data, 80)
    cache = FactorCache(tmp_path / "causal.sqlite")
    build_panel(data["history"], "balanced", cache)
    plan = compile_plan(template("factor_icir"))
    runtime = PipelineRuntime(plan, lambda *args: None)
    first = runtime.evaluate(frame)
    changed = deepcopy(data)
    for rows in changed["history"].values():
        for row in rows:
            if row["date"] > frame.as_of:
                row["close"] *= 100
                row["volume"] *= 100
    second = PipelineRuntime(plan, lambda *args: None).evaluate(current(changed, 80))
    assert first == second
    assert runtime.factors.diagnostics["research"]["research"]["label_end"] <= frame.as_of
    cold = build_panel(dict(frame.history), "balanced")
    warm = build_panel(dict(frame.history), "balanced", cache)
    pd.testing.assert_frame_equal(cold.values, warm.values)
    assert warm.metadata["computed"] == 0


def test_cache_reuses_append_and_invalidates_revised_input_window(tmp_path):
    data = snapshot()
    cache = FactorCache(tmp_path / "panel.sqlite")
    first = build_panel(dict(current(data, 40).history), "balanced", cache)
    repeated = build_panel(dict(current(data, 40).history), "balanced", cache)
    pd.testing.assert_frame_equal(first.values, repeated.values)
    assert repeated.metadata["computed"] == 0
    extended = build_panel(dict(current(data, 41).history), "balanced", cache)
    assert extended.metadata["computed"] == len(data["history"]) * len(factor_set("balanced"))
    altered = current(data, 41).mutable_history()
    altered["000001"][-1]["close"] *= 1.1
    revised = build_panel(altered, "balanced", cache)
    assert revised.metadata["computed"] == len(factor_set("balanced"))
    assert (
        revised.values.loc[(current(data, 41).as_of, "000001"), "momentum_20d"]
        != extended.values.loc[(current(data, 41).as_of, "000001"), "momentum_20d"]
    )


def test_typed_panel_connections_and_parameter_budgets_are_rejected():
    base = template("factor_icir")
    with pytest.raises(ValueError, match="Portfolio"):
        compile_plan({**base, "nodes": base["nodes"][:2], "output": "factors"})
    for node, params in [
        ("normalized", {"winsor_quantile": 0.5}),
        ("research", {"lookback": 201}),
        ("scores", {"weighting": "magic"}),
    ]:
        changed = deepcopy(base)
        next(row for row in changed["nodes"] if row["id"] == node)["params"].update(params)
        with pytest.raises(ValueError):
            compile_plan(changed)
    changed = deepcopy(base)
    changed["nodes"][-1]["inputs"] = ["eligible"]
    with pytest.raises(ValueError, match="panel"):
        compile_plan(changed)


def test_integer_and_float_ensemble_weights_have_identical_browser_digest():
    definition = template("factor_model_groups")
    integral = deepcopy(definition)
    integral["nodes"][-1]["params"]["weights"] = [1, 1, 1]
    assert digest(compile_plan(definition)) == digest(compile_plan(integral))


def test_factor_caps_and_missing_do_not_become_zero_scores():
    weights = capped_weights({"A": 99.0, "B": 1.0, "C": 0.0}, 0.4)
    assert sum(weights.values()) == pytest.approx(1)
    assert max(weights.values()) <= 0.4
    with pytest.raises(ValueError, match="infeasible"):
        capped_weights({"A": 1}, 0.4)
    data = snapshot()
    frame = current(data, 3)
    panel = build_panel(dict(frame.history), "balanced")
    result = score(panel, frame.active(), frame.as_of, factor_config()["score"])
    assert all(row.status == "unknown" and row.value is None for row in result.values())

    index = pd.MultiIndex.from_product([[frame.as_of], ["A", "B", "C"]], names=["date", "symbol"])
    missing = FactorPanel(
        pd.DataFrame({"x": [1, 2, 3], "y": [None, 1, 2], "z": [1, 3, 2]}, index=index),
        {},
        {"set": "test", "definition_digest": "test"},
    )
    result = score(
        missing,
        ["A", "B", "C"],
        frame.as_of,
        {**factor_config()["score"], "max_factor_weight": 0.4, "min_coverage": 0.5},
    )
    assert result["A"].status == "unknown"  # Two surviving factors cannot satisfy a 40% cap.
    assert max(result["B"].evidence["effective_weights"].values()) <= 0.4


def test_named_features_keep_label_purge_and_asof_cross_sections():
    data = snapshot()
    frame = current(data)
    params = model_config("lightgbm_rank", {"feature_set": "balanced"})
    rows = model_panel(frame.mutable_history(), params)
    train, validation = time_split(rows, params)
    assert train and validation
    assert max(row.target_date for row in train) < min(row.date for row in validation)
    assert max(row.target_date for row in validation) <= frame.as_of
    assert len(rows[-1].values) == len(factor_set("balanced"))
    for override in ({"feature_set": []}, {"feature_preprocess": {}}, {"feature_set": "unknown"}):
        with pytest.raises(ValueError):
            model_config("lightgbm_rank", override)


def test_research_reuses_monitor_metric_definitions():
    data = snapshot()
    frame = current(data)
    panel = preprocess(build_panel(dict(frame.history), "balanced"), factor_config()["preprocess"])
    report = analyze(panel, dict(frame.history), frame.as_of, factor_config()["research"])
    key = "momentum_20d"
    daily = report["history"][key]
    labels = forward_labels(dict(frame.history), 5, frame.as_of)
    joined = panel.values.join(labels, how="inner").loc[daily[-1]["date"]].dropna(subset=[key, "target"])
    assert daily[-1]["ic"] == _pearson(joined[key].tolist(), joined["target"].tolist())
    assert daily[-1]["rank_ic"] == _spearman(joined[key].tolist(), joined["target"].tolist())
    assert report["metrics"][key]["icir"] == _icir([row["rank_ic"] for row in daily])
    selected = select(panel, dict(frame.history), frame.as_of, factor_config()["research"])
    assert set(selected.values.columns) <= set(panel.values.columns)


def test_incremental_panel_handles_revisions_and_rewinds_without_future_values():
    data = snapshot()
    builder = PanelBuilder()
    builder.build(dict(current(data).history), "balanced")
    frame = current(data, 50)
    panel = builder.build(dict(frame.history), "balanced")
    pd.testing.assert_frame_equal(panel.values, build_panel(dict(frame.history), "balanced").values)
    revised = frame.mutable_history()
    revised["000001"][30]["close"] *= 1.1
    after = builder.build(revised, "balanced")
    pd.testing.assert_frame_equal(after.values, build_panel(revised, "balanced").values)


def test_compiled_factor_definitions_are_frozen_against_catalog_changes():
    plan = compile_plan(template("factor_equal"))
    contract = next(row for row in plan["nodes"] if row["component"] == "factor_set")["factor_contract"]
    changed = deepcopy(contract)
    changed["definitions"]["momentum_20d"]["direction"] *= -1
    data = snapshot()
    history = dict(current(data).history)
    original = PanelBuilder(contract=contract).build(history, "balanced")
    altered = PanelBuilder(contract=changed).build(history, "balanced")
    pd.testing.assert_series_equal(original.values["momentum_20d"], -altered.values["momentum_20d"])
    assert original.metadata["definition_digest"] != altered.metadata["definition_digest"]
    manifest = source_manifest()
    assert "src/strategy/factors/panel.py" in manifest
    assert "src/strategy/factors/scoring.py" in manifest
    assert "egs/config/strategies/factor_research.yaml:computation" in manifest


def test_cache_integrity_and_project_boundary(tmp_path):
    with pytest.raises(ValueError, match="缓存"):
        FactorCache(PROJECT_ROOT.parent / "outside-project.sqlite")
    cache = FactorCache(tmp_path / "integrity.sqlite")
    cache.put({"negative_zero": -0.0, "integer": 1, "missing": None})
    assert cache.get(["negative_zero", "integer", "missing"]) == {"negative_zero": 0.0, "integer": 1.0, "missing": None}
    cache.put({"key": 1.0})
    with closing(sqlite3.connect(cache.path)) as db, db:
        db.execute("UPDATE factor_values SET value = 2")
    with pytest.raises(ValueError, match="缓存"):
        cache.get(["key"])


def test_factor_http_cli_publish_run_report_and_graph_evidence(cli_command, client):
    icon = client.get("/favicon.ico")
    assert icon.status_code == 200 and icon.headers["content-type"].startswith("image/png")
    catalog = cli_command("pipeline", "components")["data"]
    assert {"factor_set", "factor_preprocess", "factor_select", "factor_score"} <= {row["id"] for row in catalog}
    started = cli_command(
        "pipeline",
        "run",
        "--template",
        "factor_equal",
        "--mode",
        "backtest",
        "--agent-mode",
        "off",
        "--start-date",
        "2026-05-04",
        "--end-date",
        "2026-10-20",
    )
    run_id = started["data"]["id"]
    service = PipelineService()
    row = service.detail(run_id)
    assert row["status"] == "finished", row
    assert row["result"]["trades"]
    assert row["result"]["diagnostics"]["factor_diagnostics"]
    native = service.store.artifact(run_id, "report.html").read_text(encoding="utf-8")
    assert "因子权重" in native
    graph = evidence(run_id)
    assert graph["nodes"]["main/factors"]["factor_research"]["persisted"]
    assert graph["nodes"]["main/scores"]["factor_research"]["weighting"] == "equal"
