"""Explicit real-market acceptance for the shared one-click runner; never collected by pytest."""

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


def main(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    logger.add(output / "real-execution.log", encoding="utf-8", colorize=False)
    FileStorage().ensure_dirs()
    assert not DataSourceManager().is_mock
    store, runner = StrategyStore(), BacktestRunner()
    strategies = {
        name: store.import_example(path)
        for name, path in {
            "dual_ma": "egs/strategy_examples/dual_ma_strategy.py",
            "mlp": "egs/strategy_examples/mlp_ensemble_strategy.py",
            "industry": "egs/strategy_examples/industry_rotation_strategy.py",
        }.items()
    }
    pipeline = PipelineStore()
    draft = pipeline.save_draft(template("rule_trend"))
    version = pipeline.publish(draft["id"])
    strategies["composition"] = {"id": version["strategy_id"]}
    scenarios = [
        ("dual_ma", "2026-01-05", "2026-01-16"),
        ("dual_ma", "2026-01-01", "2026-06-30"),
        ("dual_ma", "2026-09-01", "2026-09-30"),
        ("mlp", "2026-01-05", "2026-01-16"),
        ("industry", "2026-01-01", "2026-06-30"),
        ("composition", "2026-01-01", "2026-06-30"),
    ]
    results = []
    for name, start, end in scenarios:
        started = perf_counter()
        payload = {
            "strategy_id": strategies[name]["id"],
            "engine": "auto",
            "symbols": ["600519", "300750"],
            "start_date": start,
            "end_date": end,
            "initial_capital": 1000000,
            "price_adjustment": "qfq",
        }
        try:
            task = runner.create(payload)
            task_id = task["task_id"]
            curve, metrics, trades = (
                runner.equity_curve(task_id),
                runner.performance(task_id),
                runner.trades(task_id, page_size=100000),
            )
            assert task["status"] == "finished" and not str(metrics["data_source"]).startswith("mock")
            dates = [day[:10] for day in curve["dates"]]
            assert dates == sorted(set(dates)) and all(start <= day <= end for day in dates)
            assert dates[0] == ("2026-01-05" if start.startswith("2026-01") else start)
            assert dates[-1] == end
            assert abs(curve["equity"][-1] / payload["initial_capital"] - 1 - metrics["total_return"]) < 0.0001
            result = {
                "scenario": name,
                "requested_start": start,
                "requested_end": end,
                "seconds": round(perf_counter() - started, 3),
                "task": task,
                "metrics": metrics,
                "curve": curve,
                "trades": trades,
                "status": "passed",
            }
        except Exception as exc:
            logger.exception("Real scenario failed: {}", name)
            result = {
                "scenario": name,
                "requested_start": start,
                "requested_end": end,
                "seconds": round(perf_counter() - started, 3),
                "status": "failed",
                "error": str(exc),
            }
        results.append(result)
        (output / "real-backtests.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        logger.info("Real acceptance {} {}..{}: {} in {}s", name, start, end, result["status"], result["seconds"])
    assert all(row["status"] == "passed" for row in results), results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
