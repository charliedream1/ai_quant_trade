"""Fetch real historical bars and validate all three model strategy workflows."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import yaml
from loguru import logger

import src.core.config as config_module
from src.core.database import Database
from src.data.eastmoney import EastmoneyDataSource
from src.engine.backtest import BacktestRunner
from src.strategy import StrategyStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "egs" / "model_validation.yaml"


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
    report = _validate(config)
    target = PROJECT_ROOT / config["report_path"]
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    logger.info(
        "model workflow validation saved | path={} results={}",
        target,
        [(row["profile"], row["status"], row.get("task_id")) for row in report["results"]],
    )
    if any(row["status"] != "passed" for row in report["results"]):
        raise SystemExit(1)


def _validate(config):
    source = EastmoneyDataSource(timeout_seconds=config["timeout_seconds"])
    started = perf_counter()
    saved_evidence = PROJECT_ROOT / config["evidence_path"]
    if config["reuse_evidence"] and saved_evidence.is_file():
        stored = json.loads(saved_evidence.read_text(encoding="utf-8"))
        if stored["cutoff"] != config["cutoff_date"]:
            raise ValueError("缓存行情截止日期与验收参数不一致")
        raw = stored["rows"]
    else:
        with ThreadPoolExecutor(max_workers=len(config["symbols"])) as pool:
            futures = {
                symbol: pool.submit(source._kline, symbol, "daily", config["history_bars"], "qfq")
                for symbol in config["symbols"]
            }
            raw = {
                symbol: [row for row in future.result() if row["date"] <= config["cutoff_date"]]
                for symbol, future in futures.items()
            }
    common = set.intersection(*({row["date"] for row in rows} for rows in raw.values()))
    if not common:
        raise ValueError("真实行情没有共同交易日")
    panel = {symbol: [row for row in rows if row["date"] in common] for symbol, rows in raw.items()}
    evidence = {
        "cutoff": config["cutoff_date"],
        "raw_count": {symbol: len(rows) for symbol, rows in raw.items()},
        "aligned_count": len(common),
        "rows": panel,
    }
    (PROJECT_ROOT / config["evidence_path"]).write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    class HistoricalPanel:
        source_name = "tencent-or-fallback-historical-real"

        def stock_detail(self, symbol, **kwargs):
            return {"kline": panel[symbol]}

    results = []
    for profile in config["profiles"]:
        model_started = perf_counter()
        try:
            store = StrategyStore()
            name = f"real_validation_{profile}"
            strategy = next((row for row in store.list(keyword=name)["items"] if row["name"] == name), None)
            if strategy is None:
                strategy = store.import_example(f"egs/strategy_examples/{profile}_strategy.py", {"name": name})
            StrategyStore().set_status(strategy["strategy_id"], "可用")
            runner = BacktestRunner()
            with patch("src.engine.backtest.runner.DataSourceManager", HistoricalPanel):
                task = runner.create(
                    {
                        **config["backtest"],
                        "strategy_id": strategy["strategy_id"],
                        "symbols": config["symbols"],
                        "start_date": min(common),
                        "end_date": max(common),
                    }
                )
            metrics = runner.performance(task["task_id"])
            curve = runner.equity_curve(task["task_id"])
            trades = runner.trades(task["task_id"], page_size=1000)["items"]
            model = metrics["model_diagnostics"]
            assert model["fit_count"] > 0 and model["evaluated_prediction_count"] > 0
            assert len(curve["dates"]) == len(common)
            assert min(curve["dates"]) >= min(common) and max(curve["dates"]) <= max(common)
            assert all(trade["commission"] >= 0 for trade in trades)
            assert (
                abs(
                    sum(float(trade["pnl"]) for trade in trades)
                    - (curve["equity"][-1] - config["backtest"]["initial_capital"])
                )
                < 1
            )
            assert all(fit["label_end"] < fit["validation_start"] <= fit["as_of"] for fit in model["fit_history"])
            results.append(
                {
                    "profile": profile,
                    "status": "passed",
                    "task_id": task["task_id"],
                    "duration_ms": round((perf_counter() - model_started) * 1000),
                    "metrics": metrics,
                    "curve_points": len(curve["dates"]),
                    "trades": trades,
                    "attribution": runner.attribution(task["task_id"]),
                }
            )
        except Exception as exc:
            logger.exception("real model validation failed | profile={}", profile)
            results.append({"profile": profile, "status": "failed", "error": str(exc)})
    return {
        "kind": "real_market_small_sample",
        "start_date": min(common),
        "end_date": max(common),
        "symbols": config["symbols"],
        "points": len(common),
        "data_sources": sorted({row.get("data_source", "unknown") for rows in panel.values() for row in rows}),
        "duration_ms": round((perf_counter() - started) * 1000),
        "results": results,
    }


if __name__ == "__main__":
    main()


def test_real_model_workflow():
    """Only collected when this audit file is explicitly passed to pytest."""
    main()
