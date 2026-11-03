"""Real dated OHLCV with zero-cost and explicit stock cost experiments."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from loguru import logger

from src.core.file_storage import FileStorage
from src.data import DataSourceManager
from src.engine.backtest import BacktestRunner
from src.strategy import StrategyStore
from src.strategy.composition.config import template
from src.strategy.composition.store import PipelineStore


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    logger.add(output / "real.log", encoding="utf-8", colorize=False)
    assert not DataSourceManager().is_mock
    FileStorage().ensure_dirs()
    ordinary = StrategyStore().import_example("egs/strategy_examples/dual_ma_strategy.py")
    plan = template("rule_trend")
    plan.update(nodes=[], output="universe", name="真实成本组合")
    plan["universe"]["symbols"] = ["000001", "600036"]
    plan["execution"]["initial_capital"] = 10000
    store = PipelineStore()
    draft = store.save_draft(plan)
    version = store.publish(draft["id"])
    runner, results = BacktestRunner(), []
    for name, strategy_id in (("simple", ordinary["id"]), ("composition", version["strategy_id"])):
        for profile in ("zero", "cn_a"):
            started = perf_counter()
            payload = {
                "strategy_id": strategy_id,
                "symbols": ["000001", "600036"],
                "engine": "auto",
                "start_date": "2026-01-01",
                "end_date": "2026-06-30",
                "initial_capital": 10000,
                "price_adjustment": "none",
                "max_position_weight": 0.5,
                "execution_costs": {"profile": profile},
            }
            task = runner.create(payload)
            metrics, curve = runner.performance(task["id"]), runner.equity_curve(task["id"])
            assert task["status"] == "finished" and not metrics["data_source"].startswith("mock")
            assert curve["dates"][0][:10] == "2026-01-05" and curve["dates"][-1][:10] == "2026-06-30"
            assert len(curve["dates"]) == 116
            assert metrics["execution_orders"] and any(row.get("quantity", 0) for row in metrics["execution_orders"])
            assert metrics["total_execution_cost"] == 0 if profile == "zero" else metrics["total_execution_cost"] > 0
            assert abs(metrics["net_pnl"] + metrics["total_execution_cost"] - metrics["gross_pnl_before_costs"]) < 1e-6
            result = {
                "engine": name,
                "profile": profile,
                "seconds": round(perf_counter() - started, 3),
                "task": task,
                "metrics": metrics,
                "curve": curve,
                "trades": runner.trades(task["id"], page_size=100000),
            }
            results.append(result)
            (output / "real-cost-results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info(
                "Real cost acceptance {} {}: fees={} return={} seconds={}",
                name,
                profile,
                metrics["total_execution_cost"],
                metrics["net_return"],
                result["seconds"],
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
