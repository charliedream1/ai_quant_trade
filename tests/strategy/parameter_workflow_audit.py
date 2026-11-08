"""Replay archived real bars through parameter previews and model backtests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import patch

import yaml
from loguru import logger

import src.core.config as config_module
from src.core.database import Database
from src.engine.backtest import BacktestRunner
from src.strategy import StrategyStore
from src.strategy.parameters import StrategyParameters

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "egs/config/strategies/parameter_validation.yaml"


def run_audit(config: dict) -> dict:
    evidence = json.loads((PROJECT_ROOT / config["evidence_path"]).read_text(encoding="utf-8"))
    bars = evidence["rows"]
    dates = sorted({row["date"] for rows in bars.values() for row in rows})

    class ArchivedRealData:
        source_name = "archived-real-tencent-fqkline-qfq"

        def stock_detail(self, symbol, **kwargs):
            return {"kline": bars[symbol]}

    resolver = StrategyParameters()
    runner = BacktestRunner()
    store = StrategyStore()
    results = []
    for strategy_config in config["strategies"]:
        filename = strategy_config["file"]
        name = f"parameter_audit_{Path(filename).stem}"
        strategy = next((row for row in store.list(keyword=name)["items"] if row["name"] == name), None)
        if strategy is None:
            strategy = store.import_example(f"egs/examples/strategy_examples/{filename}", {"name": name})
        for scheme in strategy_config["schemes"]:
            times = []
            for _ in range(config["preview_repeats"]):
                started = perf_counter()
                preview = resolver.resolve(strategy["id"], config["overrides"], scheme)
                times.append((perf_counter() - started) * 1000)
            started = perf_counter()
            with patch("src.engine.backtest.runner.DataSourceManager", ArchivedRealData):
                task = runner.create(
                    {
                        **config["backtest"],
                        "strategy_id": strategy["id"],
                        "parameter_profile": scheme,
                        "params": config["overrides"],
                        "symbols": list(bars),
                        "start_date": dates[0],
                        "end_date": dates[-1],
                    }
                )
            duration_ms = (perf_counter() - started) * 1000
            metrics = runner.performance(task["id"])
            curve = runner.equity_curve(task["id"])
            trades = runner.trades(task["id"], page_size=10000)["items"]
            snapshot = task["parameter_snapshot"]
            model = metrics["model_diagnostics"]
            assert snapshot["resolved_params"] == preview["resolved_params"]
            assert snapshot["profile"]["id"] == scheme
            assert snapshot["data"]["equity_points"] == len(dates)
            assert model["fit_count"] > 0 and model["evaluated_prediction_count"] > 0
            assert trades and len(snapshot["data"]["fingerprint"]) == 64
            assert all(row["order_type"] == "open" and row["commission"] > 0 for row in trades)
            assert abs(sum(row["pnl"] for row in trades) - (curve["equity"][-1] - task["initial_cash"])) < 1
            assert all(fit["label_end"] < fit["validation_start"] <= fit["as_of"] for fit in model["fit_history"])
            results.append(
                {
                    "scheme": scheme,
                    "status": "passed",
                    "task_id": task["id"],
                    "duration_ms": round(duration_ms, 2),
                    "preview_median_ms": round(median(times), 2),
                    "preview_max_ms": round(max(times), 2),
                    "fit_count": model["fit_count"],
                    "prediction_count": model["evaluated_prediction_count"],
                    "trade_count": len(trades),
                    "snapshot": snapshot,
                    "metrics": metrics,
                }
            )
            logger.info(
                "parameter audit passed | scheme={} fits={} trades={} preview_median_ms={:.2f}",
                scheme,
                model["fit_count"],
                len(trades),
                median(times),
            )
    return {
        "kind": "archived_real_market_parameter_comparison",
        "evidence_path": config["evidence_path"],
        "start_date": dates[0],
        "end_date": dates[-1],
        "symbols": list(bars),
        "points": len(dates),
        "results": results,
    }


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    runtime = PROJECT_ROOT / config["runtime_dir"]
    runtime.mkdir(parents=True, exist_ok=True)
    os.environ["ALL_IN_ONE_DB_PATH"] = str(runtime / "validation.db")
    os.environ["ALL_IN_ONE_DATA_DIR"] = str(runtime / "data")
    os.environ["ALL_IN_ONE_DATA_MODE"] = "real"
    os.environ["ALL_IN_ONE_HELP_DOCS_AUTO_BUILD"] = "false"
    config_module._SETTINGS = None
    Database.reset_instance()
    try:
        report = run_audit(config)
        target = PROJECT_ROOT / config["report_path"]
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        logger.info("parameter audit report saved | path={} runs={}", target, len(report["results"]))
    finally:
        Database.reset_instance()
        config_module._SETTINGS = None


if __name__ == "__main__":
    main()
