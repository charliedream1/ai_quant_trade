"""Real runner/API/CLI cost snapshots checked against an independent cash ledger."""

import json

import pytest

from src.engine.backtest import BacktestRunner
from src.strategy import StrategyStore

CODE = """class CostFixtureStrategy:
    def on_bar(self, bar, context):
        if bar["timestamp"].startswith("2026-01-05"):
            return {"side": "buy", "symbol": bar["symbol"], "quantity": 100}
        return {"side": "sell", "symbol": bar["symbol"], "quantity": 100}
"""


class DatedData:
    source_name = "fixture-dated-cost-ledger"

    def stock_detail(self, symbol, **kwargs):
        return {
            "kline": [
                {"date": day, "open": price, "high": price, "low": price, "close": price, "volume": 10000}
                for day, price in [("2026-01-05", 10), ("2026-01-06", 11)]
            ]
        }


def payload(strategy_id, profile="cn_a"):
    return {
        "strategy_id": strategy_id,
        "symbols": ["600519"],
        "engine": "auto",
        "start_date": "2026-01-05",
        "end_date": "2026-01-06",
        "initial_capital": 2000,
        "max_position_weight": 1,
        "execution_costs": {
            "profile": profile,
            "slippage_mode": "none",
            "max_participation": 1,
            "settlement_sessions": 1,
        },
    }


def test_api_cash_fees_tax_transfer_and_frozen_snapshot(client, monkeypatch):
    monkeypatch.setattr("src.engine.backtest.runner.DataSourceManager", DatedData)
    strategy = StrategyStore().create({"name": "cost_ledger_fixture", "code": CODE})
    StrategyStore().review(strategy["id"], strategy["source_sha256"], "explicit-cost-test-review")
    response = client.post("/api/v1/backtests", json=payload(strategy["id"])).json()
    assert response["code"] == 0, response
    task = response["data"]
    runner = BacktestRunner()
    metrics, curve = runner.performance(task["id"]), runner.equity_curve(task["id"])
    # 2000 - 1000 - 5 - .01 + 1100 - 5 - .55 - .01 = 2089.43
    assert curve["equity"][-1] == pytest.approx(2089.43)
    assert metrics["commission_paid"] == 10
    assert metrics["tax_paid"] == 0.55
    assert metrics["transfer_fee_paid"] == 0.02
    assert metrics["total_execution_cost"] == pytest.approx(10.57)
    assert metrics["gross_pnl_before_costs"] == pytest.approx(100)
    snapshot = task["parameter_snapshot"]["run"]["execution_costs"]
    assert snapshot == metrics["execution_costs"] and len(snapshot["sha256"]) == 64
    assert len(metrics["execution_orders"]) == 2
    zero = runner.create(payload(strategy["id"], "zero"))
    assert runner.equity_curve(zero["id"])["equity"][-1] == 2100
    assert runner.performance(zero["id"])["total_execution_cost"] == 0
    assert runner.performance(task["id"])["total_execution_cost"] == pytest.approx(10.57)


def test_strict_failure_is_durable_and_never_claims_real_trading_support(client, monkeypatch):
    monkeypatch.setattr("src.engine.backtest.runner.DataSourceManager", DatedData)
    strategy = StrategyStore().create({"name": "strict_cost_fixture", "code": CODE})
    StrategyStore().review(strategy["id"], strategy["source_sha256"], "explicit-cost-test-review")
    request = payload(strategy["id"])
    request["execution_costs"]["validation_mode"] = "strict"
    result = client.post("/api/v1/backtests", json=request).json()
    assert result["code"] != 0 and "严格" in result["message"]
    assert BacktestRunner().detail(result["data"]["task_id"])["status"] == "failed"


def test_cli_uses_the_same_cost_contract(cli_command, monkeypatch):
    monkeypatch.setattr("src.engine.backtest.runner.DataSourceManager", DatedData)
    strategy = StrategyStore().create({"name": "cli_cost_fixture", "code": CODE})
    StrategyStore().review(strategy["id"], strategy["source_sha256"], "explicit-cost-test-review")
    request = payload(strategy["id"])
    result = cli_command(
        "backtest",
        "run",
        "--strategy-id",
        strategy["id"],
        "--symbols",
        '["600519"]',
        "--start-date",
        request["start_date"],
        "--end-date",
        request["end_date"],
        "--initial-capital",
        2000,
        "--max-position-weight",
        1,
        "--execution-costs",
        json.dumps(request["execution_costs"]),
    )
    task = result["data"]
    assert BacktestRunner().equity_curve(task["task_id"])["equity"][-1] == pytest.approx(2089.43)


def test_partial_position_closes_allocate_open_fees_once(client, monkeypatch):
    class ThreeDays(DatedData):
        def stock_detail(self, symbol, **kwargs):
            value = super().stock_detail(symbol, **kwargs)
            value["kline"].append(
                {"date": "2026-01-07", "open": 12, "high": 12, "low": 12, "close": 12, "volume": 10000}
            )
            return value

    monkeypatch.setattr("src.engine.backtest.runner.DataSourceManager", ThreeDays)
    source = CODE.replace('"quantity": 100}', '"quantity": 200}', 1)
    strategy = StrategyStore().create({"name": "partial_cost_fixture", "code": source})
    StrategyStore().review(strategy["id"], strategy["source_sha256"], "explicit-cost-test-review")
    request = payload(strategy["id"])
    request.update(end_date="2026-01-07", initial_capital=5000)
    task = BacktestRunner().create(request)
    trades = BacktestRunner().trades(task["id"])["items"]
    assert [row["commission"] for row in trades] == [7.5, 7.5]
    assert BacktestRunner().equity_curve(task["id"])["equity"][-1] == pytest.approx(5283.81)
    assert BacktestRunner().performance(task["id"])["total_execution_cost"] == pytest.approx(16.19)
