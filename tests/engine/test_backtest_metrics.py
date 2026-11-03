"""Backtest performance metric contracts."""

from src.engine.backtest.engines import _metrics


def test_metrics_include_risk_trade_and_execution_breakdown() -> None:
    trades = [
        {
            "pnl": 120.0,
            "commission": 2.0,
            "open_value": 1000.0,
            "close_value": 1120.0,
            "holding_days": 4,
        },
        {
            "pnl": -60.0,
            "commission": 1.5,
            "open_value": 800.0,
            "close_value": 740.0,
            "holding_days": 2,
        },
    ]
    curve = {
        "dates": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        "exposure": [0.0, 0.5, 0.8, 0.0],
    }
    metrics = _metrics(
        initial_cash=10000.0,
        equity=[10000.0, 10100.0, 9950.0, 10060.0],
        benchmark=[10000.0, 10030.0, 10020.0, 10040.0],
        drawdown=[0.0, 0.0, -0.0149, 0.0],
        trades=trades,
        data_source="mock-local",
        payload={"order_type": "market", "price_adjustment": "qfq"},
        curve=curve,
    )

    assert metrics["trade_count"] == 2
    assert metrics["win_count"] == 1
    assert metrics["loss_count"] == 1
    assert metrics["annual_volatility"] > 0
    assert metrics["profit_factor"] == 2.0
    assert metrics["commission_paid"] == 3.5
    assert metrics["turnover_ratio"] == 0.366
    assert metrics["average_exposure"] == 0.325
    assert metrics["max_drawdown_duration_days"] == 0
    assert metrics["data_source"] == "mock-local"
