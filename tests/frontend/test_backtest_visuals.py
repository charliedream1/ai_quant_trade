"""Backtest report visual and explanation contracts."""

from datetime import date, timedelta

from src.frontend.service.visuals import (
    backtest_explanation,
    backtest_exposure_figure,
    backtest_monthly_figure,
    backtest_rolling_figure,
    backtest_trade_figure,
    equity_figure,
    metrics_frame,
)


def _curve() -> dict[str, list[float] | list[str]]:
    dates = [(date(2026, 1, 1) + timedelta(days=index)).isoformat() for index in range(45)]
    equity = [1000000.0 + index * 1200.0 - (index % 7) * 3000.0 for index in range(45)]
    return {
        "dates": dates,
        "equity": equity,
        "benchmark": [1000000.0 + index * 800.0 for index in range(45)],
        "drawdown": [0.0 if index % 5 else -0.01 for index in range(45)],
        "exposure": [0.2 + (index % 4) * 0.1 for index in range(45)],
        "position_count": [index % 4 for index in range(45)],
    }


def test_backtest_visuals_cover_monthly_rolling_trade_and_exposure_views() -> None:
    curve = _curve()
    monthly = backtest_monthly_figure(curve)
    rolling = backtest_rolling_figure(curve)
    trades = backtest_trade_figure(
        [
            {"close_time": "2026-01-08", "pnl": 120.0},
            {"close_time": "2026-01-12", "pnl": -40.0},
        ]
    )
    exposure = backtest_exposure_figure(curve)

    assert monthly.data and monthly.data[0].type == "heatmap"
    assert len(rolling.data) == 2
    assert len(trades.data) == 2
    assert len(exposure.data) == 2


def test_metrics_frame_groups_metrics_and_explains_units() -> None:
    frame = metrics_frame(
        {
            "total_return": 0.12,
            "max_drawdown": -0.08,
            "annual_volatility": 0.2,
            "profit_factor": 1.4,
            "trade_count": 6,
            "data_source": "mock-local",
        }
    )

    assert list(frame.columns) == ["类别", "指标", "数值", "解释"]
    assert len(frame) == 6
    assert any("最大回撤" in str(value) for value in frame["指标"])
    assert any("历史峰值" in str(value) for value in frame["解释"])


def test_backtest_explanation_marks_mock_and_small_samples() -> None:
    text = backtest_explanation(
        {"data_source": "mock-local", "trade_count": 2, "result_scope": "完整事件回测结果"},
        {"equity": [100.0, 101.0]},
    )

    assert "mock" in text
    assert "交易样本较少" in text


def test_equity_chart_preserves_small_nav_variations():
    figure = equity_figure(_curve())
    assert figure.data[0].fill == "none", "filling to zero flattens small NAV variations"
