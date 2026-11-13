"""Opt-in actual HK quotes and dated bars with an independent external-order cash ledger."""

import json
import os
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from pathlib import Path
from time import perf_counter

import pytest
import yaml
from loguru import logger

from src.core.config import PROJECT_ROOT
from src.data import DataSourceManager
from src.data.hong_kong_calendar import sessions
from src.engine.backtest import BacktestRunner
from src.strategy import StrategyStore

pytestmark = pytest.mark.skipif(os.environ.get("HK_LIVE") != "1", reason="Explicit public-source acceptance only")


def reference_fee(amount):
    amount = Decimal(str(amount))
    cent = Decimal("0.01")
    commission = (amount * Decimal("0.0003")).quantize(cent, rounding=ROUND_HALF_UP)
    stamp = (amount * Decimal("0.001")).quantize(Decimal(1), rounding=ROUND_CEILING)
    sfc = (amount * Decimal("0.000027")).quantize(cent, rounding=ROUND_HALF_UP)
    afrc = (amount * Decimal("0.0000015")).quantize(cent, rounding=ROUND_HALF_UP)
    trading = (amount * Decimal("0.0000565")).quantize(cent, rounding=ROUND_HALF_UP)
    settlement = (amount * Decimal("0.000042")).quantize(cent, rounding=ROUND_HALF_UP)
    return commission + stamp + sfc + afrc + trading + settlement


def test_actual_hkd_backtest_cash_and_fees(client, monkeypatch):
    policy = yaml.safe_load((PROJECT_ROOT / "egs/examples/data/hong_kong_acceptance.yaml").read_text(encoding="utf-8"))
    output = Path(os.environ["HK_LIVE_OUTPUT"])
    output.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ALL_IN_ONE_DATA_MODE", "real")
    provider = DataSourceManager(mode="real", market="HK")
    snapshots = {}
    for symbol in policy["symbols"]:
        quote = provider.stock_quote(symbol)
        rows = provider.history(symbol, policy["start_date"], policy["end_date"], 100, adjustment="none")
        assert quote["currency"] == "HKD" and not provider.is_mock
        assert [row["date"] for row in rows] == sessions(policy["start_date"], policy["end_date"])
        snapshots[symbol] = {"quote": quote, "bars": rows}
    (output / "market-snapshot.json").write_text(json.dumps(snapshots, ensure_ascii=False, indent=2), encoding="utf-8")
    strategy = StrategyStore().import_example(policy["strategy"])
    request = {
        "strategy_id": strategy["id"],
        "market": "HK",
        "engine": "simple",
        "symbols": policy["symbols"],
        "start_date": policy["start_date"],
        "end_date": policy["end_date"],
        "initial_capital": policy["initial_capital"],
        "params": policy["params"],
        "price_adjustment": "none",
        "order_type": policy["order_type"],
        "max_position_weight": 1,
        "execution_costs": {"profile": "hk_cash", "instruments": policy["instruments"]},
    }
    runner = BacktestRunner()
    start = perf_counter()
    task = runner.create(request)
    assert task["status"] == "finished", task
    metrics, curve = runner.performance(task["id"]), runner.equity_curve(task["id"])
    actual_orders = [row for row in metrics["execution_orders"] if row.get("quantity", 0)]
    assert len(actual_orders) == 2 * len(policy["symbols"])
    cash = Decimal(str(policy["initial_capital"]))
    reference_orders = []
    positions = {}
    for order in actual_orders:
        bars = snapshots[order["symbol"]]["bars"]
        buy = order["side"] == "buy"
        expected_bar = bars[0] if buy else bars[-1]
        assert order["time"] == expected_bar["date"]
        expected_price = Decimal(str(expected_bar["close"]))
        assert Decimal(str(order["price"])) == expected_price
        assert order["quantity"] == policy["quantity"]
        turnover = expected_price * order["quantity"]
        fee = reference_fee(turnover)
        assert fee == Decimal(str(order["costs"]["total"]))
        cash += (-turnover - fee) if buy else turnover - fee
        positions[order["symbol"]] = positions.get(order["symbol"], 0) + (
            order["quantity"] if buy else -order["quantity"]
        )
        reference_orders.append(
            {
                "symbol": order["symbol"],
                "side": order["side"],
                "price": str(expected_price),
                "quantity": order["quantity"],
                "fee": str(fee),
                "cash": str(cash),
            }
        )
    assert not any(positions.values())
    assert abs(cash - Decimal(str(curve["equity"][-1]))) <= Decimal("0.01")
    daily_cash, daily_positions, reference_curve = Decimal(str(policy["initial_capital"])), {}, []
    for index, day in enumerate(curve["dates"]):
        for order in actual_orders:
            if order["time"] != day:
                continue
            amount = Decimal(str(order["price"])) * order["quantity"]
            fee = reference_fee(amount)
            buy = order["side"] == "buy"
            daily_cash += -amount - fee if buy else amount - fee
            daily_positions[order["symbol"]] = daily_positions.get(order["symbol"], 0) + (
                order["quantity"] if buy else -order["quantity"]
            )
        value = daily_cash + sum(
            Decimal(str(next(row["close"] for row in snapshots[symbol]["bars"] if row["date"] == day))) * quantity
            for symbol, quantity in daily_positions.items()
        )
        assert abs(value - Decimal(str(curve["equity"][index]))) <= Decimal("0.01")
        reference_curve.append(
            {"date": day, "cash": str(daily_cash), "equity": str(value), "positions": dict(daily_positions)}
        )
    assert metrics["currency"] == "HKD" and curve["currency"] == "HKD"
    result = {
        "reference_daily_curve": reference_curve,
        "request": request,
        "task": task,
        "metrics": metrics,
        "curve": curve,
        "reference_orders": reference_orders,
        "reference_final_cash": str(cash),
        "seconds": round(perf_counter() - start, 3),
    }
    (output / "backtest-reference.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "HK actual backtest validated | sessions={} fills={} final_cash={} seconds={}",
        len(curve["dates"]),
        len(actual_orders),
        cash,
        result["seconds"],
    )
