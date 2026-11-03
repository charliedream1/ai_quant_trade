"""Factor monitoring diagnostics regression tests."""

from __future__ import annotations


def test_factor_monitor_includes_diagnostic_outputs(client):
    from src.engine.research.factor_monitor import FactorMonitorService

    payload = FactorMonitorService().monitor("600519,300750,000001,688981,300124", persist=False)

    assert payload["metrics"]
    assert payload["ic_decay"]
    assert payload["quantile_history"]
    assert payload["style_exposure"]
    assert {1, 3, 5, 10} <= {int(row["horizon_days"]) for row in payload["ic_decay"]}
    assert {
        "rank_ic_mean",
        "rank_ic_std",
        "avg_turnover_rate",
        "capacity_hint",
    } <= set(payload["metrics"][0])
    assert {"date", "quantile", "forward_return"} <= set(payload["quantile_history"][0])
    assert {"style_factor", "exposure", "hint"} <= set(payload["style_exposure"][0])
    assert all(row["sample_size"] >= 2 for row in payload["quantile_history"])
