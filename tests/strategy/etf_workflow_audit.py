"""Run the ETF strategies on a small, source-backed ETF panel."""

from __future__ import annotations

import json
import os
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import yaml
from loguru import logger

import src.core.config as config_module
from src.core.database import Database
from src.data import DataSourceManager
from src.engine.backtest import BacktestRunner
from src.strategy import StrategyStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "egs/etf_validation.yaml"


def run_validation(config: dict) -> dict:
    source = DataSourceManager()
    raw: dict[str, list[dict]] = {}
    source_rows = {}
    for symbol in config["symbols"]:
        detail = source.stock_detail(symbol, kline_count=int(config["history_bars"]), kline_period="daily")
        rows = detail.get("kline") or []
        raw[symbol] = rows
        source_rows[symbol] = {"count": len(rows), "data_source": (detail.get("quote") or {}).get("data_source")}
    common = set.intersection(
        *({str(row.get("date") or row.get("timestamp"))[:10] for row in rows} for rows in raw.values())
    )
    if len(common) < 80:
        raise RuntimeError(f"ETF共同历史样本不足：{len(common)}")
    panel = {
        symbol: [row for row in rows if str(row.get("date") or row.get("timestamp"))[:10] in common]
        for symbol, rows in raw.items()
    }
    evidence = {
        "symbols": config["symbols"],
        "start_date": min(common),
        "end_date": max(common),
        "points": len(common),
        "source_rows": source_rows,
        "rows": panel,
        "source_name": source.source_name,
    }
    target = PROJECT_ROOT / config["evidence_path"]
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    class HistoricalETFData:
        source_name = "archived-real-etf"

        def stock_detail(self, symbol, **kwargs):
            return {"kline": panel[symbol], "quote": {"data_source": "archived-real-etf"}}

    results = []
    for item in config["strategies"]:
        started = perf_counter()
        store = StrategyStore()
        strategy = store.import_example(
            f"egs/strategy_examples/{item['file']}", {"name": f"real_etf_{Path(item['file']).stem}"}
        )
        runner = BacktestRunner()
        with patch("src.engine.backtest.runner.DataSourceManager", HistoricalETFData):
            task = runner.create(
                {
                    **config["backtest"],
                    "strategy_id": strategy["strategy_id"],
                    "parameter_profile": item["profile"],
                    "params": {"universe": "cn_core"},
                    "symbols": config["symbols"],
                    "start_date": min(common),
                    "end_date": max(common),
                }
            )
        metrics = runner.performance(task["task_id"])
        curve = runner.equity_curve(task["task_id"])
        trades = runner.trades(task["task_id"], page_size=10000)["items"]
        assert metrics["asset_type"] == "etf"
        assert metrics["tracking_error"] >= 0
        assert len(curve["dates"]) == len(common)
        assert task["parameter_snapshot"]["resolved_params"]["universe"] == "cn_core"
        assert all(trade["order_type"] == "open" for trade in trades)
        results.append(
            {
                "strategy": item["file"],
                "profile": item["profile"],
                "status": "passed",
                "task_id": task["task_id"],
                "duration_ms": round((perf_counter() - started) * 1000),
                "curve_points": len(curve["dates"]),
                "trade_count": len(trades),
                "tracking_error": metrics["tracking_error"],
                "turnover_ratio": metrics["turnover_ratio"],
                "data_source": metrics["data_source"],
                "snapshot": task["parameter_snapshot"],
            }
        )
        logger.info(
            "ETF strategy validation passed | strategy={} trades={} tracking_error={} duration_ms={}",
            item["file"],
            len(trades),
            metrics["tracking_error"],
            round((perf_counter() - started) * 1000),
        )
    return {"kind": "real_etf_strategy_validation", "evidence": evidence, "results": results}


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
        report = run_validation(config)
        target = PROJECT_ROOT / config["report_path"]
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        logger.info("ETF validation report saved | path={} results={}", target, len(report["results"]))
    finally:
        Database.reset_instance()
        config_module._SETTINGS = None


if __name__ == "__main__":
    main()
