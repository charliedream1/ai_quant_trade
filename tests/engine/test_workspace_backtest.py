"""Date coverage, engine binding and durable failures at real service boundaries."""

from threading import Event

import pytest

from src.core.exceptions import BusinessError
from src.core.repository import Repository
from src.data.backtest_history import load_history
from src.engine.backtest import BacktestRunner
from src.engine.backtest.capabilities import resolve_engine, strategy_capability
from src.engine.backtest.engines import SimpleBacktestEngine
from src.engine.backtest.jobs import ACTIVE, cancel, submit
from src.strategy import StrategyStore
from src.strategy.composition.config import template
from src.strategy.composition.store import PipelineStore


def request(strategy_id):
    return {
        "strategy_id": strategy_id,
        "engine": "auto",
        "symbols": ["600519", "300750"],
        "start_date": "2026-01-05",
        "end_date": "2026-01-16",
        "initial_capital": 1000000,
    }


def test_composition_auto_binding_and_explicit_incompatibility(client):
    store = PipelineStore()
    draft = store.save_draft(template("rule_trend"))
    version = store.publish(draft["id"])
    strategy_id = version["strategy_id"]
    row = StrategyStore().get(strategy_id)
    cap = strategy_capability(strategy_id, row["default_params"], Repository())
    assert resolve_engine("auto", cap) == "composition"
    with pytest.raises(BusinessError, match="需要composition"):
        BacktestRunner().create({**request(strategy_id), "engine": "simple"})
    assert BacktestRunner().list()["total"] == 0
    task = BacktestRunner().create(request(strategy_id))
    assert task["engine"] == "composition" and task["status"] == "finished"
    assert BacktestRunner().equity_curve(task["task_id"])["dates"][0] == "2026-01-05"


def test_failed_execution_has_task_and_no_success_result(client, monkeypatch):
    strategy = StrategyStore().import_example("egs/strategy_examples/standard_port_strategy.py")

    def fail(*args, **kwargs):
        raise RuntimeError("historical source unavailable")

    monkeypatch.setattr("src.engine.backtest.engines._load_events", fail)
    response = client.post("/api/v1/backtests", json=request(strategy["id"])).json()
    assert response["code"] != 0
    task_id = response["data"]["task_id"]
    assert BacktestRunner().detail(task_id)["status"] == "failed"
    assert Repository().db.scalar("SELECT COUNT(*) FROM backtest_results") == 0


def test_async_duplicate_and_cancellation_keep_durable_id(client, monkeypatch):
    strategy = StrategyStore().import_example("egs/strategy_examples/standard_port_strategy.py")
    entered, release, finished = Event(), Event(), Event()
    original = BacktestRunner.execute

    def paused(self, *args, **kwargs):
        entered.set()
        assert release.wait(10)
        try:
            return original(self, *args, **kwargs)
        finally:
            finished.set()

    monkeypatch.setattr(BacktestRunner, "execute", paused)
    task = submit(request(strategy["id"]))
    try:
        assert entered.wait(5)
        assert submit(request(strategy["id"]))["task_id"] == task["task_id"]
        assert "取消" in cancel(task["task_id"])
    finally:
        release.set()
        assert finished.wait(10)
    assert BacktestRunner().detail(task["task_id"])["status"] == "cancelled"
    assert BacktestRunner().list()["total"] == 1
    assert not ACTIVE


def test_date_loader_uses_requested_dates_and_detects_interior_missing(client):
    class Provider:
        source_name = "contract-real-provider"
        calls = []

        def _load_kline_tencent(self, symbol, period, count, adjust, start_date, end_date):
            self.calls.append((symbol, start_date, end_date))
            days = ["2026-01-05", "2026-01-06", "2026-01-07"] if symbol == "sh000001" else ["2026-01-05", "2026-01-07"]
            return [{"date": day, "open": 1, "high": 2, "low": 1, "close": 2, "volume": 100} for day in days]

        def _validate_kline(self, rows, source):
            assert rows

    provider = Provider()
    with pytest.raises(BusinessError, match="2026-01-06"):
        load_history(provider, "600519", "2026-01-05", "2026-01-07", "qfq")
    assert provider.calls == [("600519", "2026-01-05", "2026-01-07"), ("sh000001", "2026-01-05", "2026-01-07")]


def test_timeout_has_distinct_terminal_state(client):
    strategy = StrategyStore().import_example("egs/strategy_examples/standard_port_strategy.py")
    task = BacktestRunner().create(request(strategy["id"]), deferred=True)

    def timeout():
        raise TimeoutError("test deadline")

    with pytest.raises(BusinessError, match="deadline"):
        BacktestRunner().execute(task["task_id"], checkpoint=timeout)
    assert BacktestRunner().detail(task["task_id"])["status"] == "timeout"


def test_sparse_calendars_do_not_zip_different_dates_or_peek_at_future_benchmark():
    seen = []

    class Port:
        def on_start(self, context):
            pass

        def on_stop(self, context):
            pass

        def on_bar(self, event, context):
            seen.append((event.symbol, event.timestamp))
            return []

    class Data:
        source_name = "fixture-calendar"

        def stock_detail(self, symbol, **kwargs):
            values = (
                [("2026-01-05", 10), ("2026-01-07", 20)]
                if symbol == "A"
                else [("2026-01-06", 100), ("2026-01-07", 200)]
            )
            return {
                "kline": [
                    {"date": day, "open": price, "high": price, "low": price, "close": price} for day, price in values
                ]
            }

    _, curve, _ = SimpleBacktestEngine().run(
        {"start_date": "2026-01-05", "end_date": "2026-01-07"}, ["A", "B"], 1000, strategy=Port(), data=Data()
    )
    assert seen == [("A", "2026-01-05"), ("B", "2026-01-06"), ("A", "2026-01-07"), ("B", "2026-01-07")]
    assert curve["benchmark"] == [1000, 1000, 2000]
    assert curve["equity"] == [1000, 1000, 1000]
