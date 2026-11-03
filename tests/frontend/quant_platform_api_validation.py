"""Run a small isolated API validation for strategy, backtest, factor, Qlib and paper flows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests
from loguru import logger


def run(base_url: str) -> dict:
    base = base_url.rstrip("/") + "/api/v1"
    session = requests.Session()
    code = Path("egs/strategy_examples/dual_ma_strategy.py").read_text(encoding="utf-8")
    strategy = session.post(
        f"{base}/strategies",
        json={
            "name": "validation_20261018",
            "description": "isolated validation",
            "code": code,
            "default_params": {"fast_window": 5},
        },
        timeout=30,
    ).json()["data"]
    strategy_id = int(strategy["strategy_id"])
    enabled = session.post(f"{base}/strategies/{strategy_id}/enable", timeout=30).json()["data"]
    payload = {
        "strategy_id": strategy_id,
        "symbols": ["600519", "300750"],
        "start_date": "2026-01-05",
        "end_date": "2026-01-16",
        "initial_capital": 1_000_000,
        "params": {},
        "order_type": "market",
        "price_adjustment": "qfq",
        "max_position_count": 2,
        "max_position_weight": 0.25,
        "lot_size": 100,
        "slippage_rate": 0.001,
    }
    backtest = session.post(f"{base}/backtests", json=payload, timeout=60).json()["data"]
    task_id = int(backtest["task_id"])
    performance = session.get(f"{base}/backtests/{task_id}/performance", timeout=30).json()["data"]
    curve = session.get(f"{base}/backtests/{task_id}/equity-curve", timeout=30).json()["data"]
    trades = session.get(f"{base}/backtests/{task_id}/trades", timeout=30).json()["data"]
    attribution = session.get(f"{base}/backtests/{task_id}/attribution", timeout=30).json()["data"]
    factor = session.get(f"{base}/factors/monitor", params={"universe": "600519,300750,000001"}, timeout=60).json()
    qlib_status = session.get(f"{base}/qlib-workflows/status", timeout=30).json()["data"]
    qlib_run = session.post(
        f"{base}/qlib-workflows/runs",
        json={"run_type": "workflow", "params": {"experiment_name": "validation_20261018"}},
        timeout=30,
    ).json()["data"]
    account = session.post(
        f"{base}/paper-accounts",
        json={"name": "validation_20261018", "initial_capital": 1_000_000, "strategy_id": strategy_id},
        timeout=30,
    ).json()["data"]
    order = session.post(
        f"{base}/paper-accounts/{account['account_id']}/orders",
        json={"symbol": "300750", "side": "buy", "order_type": "market", "quantity": 100},
        timeout=30,
    ).json()["data"]
    overview = session.get(f"{base}/paper-accounts/{account['account_id']}/overview", timeout=30).json()["data"]
    result = {
        "strategy": {"id": strategy_id, "status": enabled["status"]},
        "backtest": {
            "id": task_id,
            "status": backtest["status"],
            "metrics": performance,
            "curve_points": len(curve["dates"]),
            "curve_in_range": all(
                payload["start_date"] <= str(value)[:10] <= payload["end_date"] for value in curve["dates"]
            ),
            "trade_count": trades["total"],
            "attribution_items": len(attribution.get("summary") or []),
        },
        "factor": {
            "code": factor["code"],
            "metric_count": len(factor["data"].get("metrics") or []) if factor["code"] == 0 else 0,
            "ic_decay": len(factor["data"].get("ic_decay") or []) if factor["code"] == 0 else 0,
            "qlib": factor["data"].get("qlib") if factor["code"] == 0 else factor.get("message"),
        },
        "qlib": {
            "status": qlib_status["status"],
            "diagnostic": qlib_status["diagnostic"],
            "run_status": qlib_run["status"],
            "run_error": qlib_run.get("error_msg"),
        },
        "paper": {
            "account_id": account["account_id"],
            "order_status": order["status"],
            "position_count": overview["position_count"],
            "total_asset": overview["total_asset"],
        },
    }
    logger.info("{}", json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.base_url)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
