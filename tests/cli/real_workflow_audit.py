"""Explicit audit: real archived OHLCV through subprocess CLI → HTTP → engine."""

import hashlib
import json
from pathlib import Path
from time import perf_counter

import yaml

from src.core.config import get_settings

ROOT = Path(__file__).resolve().parents[2]


def test_cli_real_model_and_etf_workflows(cli_command, monkeypatch, tmp_path):
    config = yaml.safe_load((ROOT / "egs/cli/validation.yaml").read_text(encoding="utf-8"))
    panels = {}
    evidence = {}
    for name, filename in config["panels"].items():
        content = (ROOT / filename).read_bytes()
        stored = json.loads(content)
        panel = {
            symbol: [row for row in rows if row["date"] <= config["cutoff"]] for symbol, rows in stored["rows"].items()
        }
        dates = set.intersection(*({row["date"] for row in rows} for rows in panel.values()))
        panels[name] = {symbol: [row for row in rows if row["date"] in dates] for symbol, rows in panel.items()}
        evidence[name] = {
            "file": filename,
            "sha256": hashlib.sha256(content).hexdigest(),
            "points": len(dates),
            "first": min(dates),
            "last": max(dates),
        }
    merged = {symbol: rows for panel in panels.values() for symbol, rows in panel.items()}

    class ArchivedSource:
        source_name = "archived-real-cli-validation"

        def stock_detail(self, symbol, **kwargs):
            return {"kline": merged[symbol], "quote": {"data_source": self.source_name}}

    monkeypatch.setattr(get_settings(), "data_mode", "real")
    monkeypatch.setenv("ALL_IN_ONE_DATA_MODE", "real")
    monkeypatch.setattr("src.engine.backtest.runner.DataSourceManager", ArchivedSource)
    results = []
    for item in config["strategies"]:
        started = perf_counter()
        strategy = cli_command(
            "strategy",
            "examples",
            "import",
            "--example",
            f"egs/strategy_examples/{item['name']}_strategy.py",
            "--name",
            f"cli-real-{item['name']}",
        )["data"]
        cli_command("strategy", "enable", strategy["strategy_id"])
        request = {
            **config["backtest"],
            "strategy_id": strategy["strategy_id"],
            "symbols": list(panels[item["panel"]]),
            "start_date": evidence[item["panel"]]["first"],
            "end_date": evidence[item["panel"]]["last"],
        }
        if item.get("profile"):
            request.update(parameter_profile=item["profile"], params={"universe": "cn_core"})
        request_file = tmp_path / (item["name"] + ".json")
        request_file.write_text(json.dumps(request), encoding="utf-8")
        task = cli_command("backtest", "run", "--file", request_file, "--require-real", timeout=180)["data"]
        task_id = task["task_id"]
        metrics = cli_command("backtest", "metrics", task_id, "--require-real")["data"]
        curve = cli_command("backtest", "curve", task_id)["data"]
        trades = cli_command("backtest", "trades", task_id, "--all", "--max-items", 10000)["data"]["items"]
        snapshot = cli_command("backtest", "snapshot", task_id)["data"]
        assert len(curve["dates"]) == evidence[item["panel"]]["points"]
        assert all(request["start_date"] <= day <= request["end_date"] for day in curve["dates"])
        assert snapshot["run"]["symbols"] == request["symbols"]
        assert snapshot["data"]["market"] == "CN" and metrics["data_source"] == ArchivedSource.source_name
        assert all(trade["commission"] >= 0 and trade["order_type"] == "open" for trade in trades)
        assert (
            abs(sum(float(trade["pnl"]) for trade in trades) - (curve["equity"][-1] - request["initial_capital"])) < 1
        )
        if item["panel"] == "models":
            model = metrics["model_diagnostics"]
            assert model["fit_count"] > 0 and model["evaluated_prediction_count"] > 0
            assert all(fit["label_end"] < fit["validation_start"] <= fit["as_of"] for fit in model["fit_history"])
        else:
            assert metrics["asset_type"] == "etf" and metrics["tracking_error"] >= 0
        assert cli_command("backtest", "attribution", task_id)["data"]["by_symbol"]
        results.append(
            {
                "strategy": item["name"],
                "task_id": task_id,
                "status": "passed",
                "duration_ms": round((perf_counter() - started) * 1000),
                "metrics": metrics,
                "trades": len(trades),
                "snapshot": snapshot,
            }
        )
    report = {
        "kind": "archived_real_ohlcv_subprocess_cli_http",
        "live_fetch": False,
        "evidence": evidence,
        "results": results,
    }
    (ROOT / config["report"]).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
