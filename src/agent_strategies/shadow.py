"""Execute frozen research targets through the existing physical portfolio ledger."""

from copy import deepcopy
from importlib import import_module
from typing import Any

from src.strategy.composition.validation import compile_plan

from .ports import ShadowPermit


def target_weights(proposal: dict, maximum: float) -> dict[str, float]:
    scores = {
        row["symbol"]: row["score"] for row in proposal["decisions"] if row["action"] == "select" and row["score"] > 0
    }
    total = sum(scores.values())
    return {symbol: min(maximum, value / total) for symbol, value in scores.items()} if total else {}


def shadow_book(run: dict, history: dict, days: list[str], weights: dict) -> dict:
    simulation = import_module("src.engine.composition.simulation").CompositionSimulation
    request = run["request"]
    definition: dict[str, Any] = {
        "name": "冻结研究影子账本",
        "schema_version": 1,
        "universe": {"symbols": sorted(history)},
        "nodes": [{"id": "frozen", "component": "eligibility", "inputs": ["universe"], "params": {}}],
        "output": "frozen",
        "portfolio": {"component": "equal", "params": {"top_k": len(history), "max_weight": 1.0, "exposure": 1.0}},
        "risk": request.get("risk") or {},
        "execution": request.get("execution") or {},
        "rebalance_sessions": 1,
        "variants": {"baseline": {}},
    }
    base = compile_plan(definition)
    active = deepcopy(base)
    active["nodes"][0]["component"] = "agent_shadow"
    active["portfolio"]["component"] = "agent_budget"
    payload = {
        "mode": "backtest",
        "market": request.get("market", "CN"),
        "start_date": days[0],
        "end_date": days[-1],
        "agent_mode": "off",
        "execution_cost_snapshot": request.get("execution_cost_snapshot"),
    }
    snapshot = {
        "history": history,
        "metadata": {},
        "source": "frozen_agent_shadow",
        "is_mock": False,
        "market": payload["market"],
        "limitations": ["shadow_not_live_account", "uses_available_historical_capabilities"],
    }
    actual = simulation(
        active, snapshot, {**payload, "_agent_strategy_permit": ShadowPermit(weights)}, None, lambda *args: None
    ).run()
    baseline = simulation(base, snapshot, payload, None, lambda *args: None).run()
    if actual["decision_errors"] or baseline["decision_errors"]:
        raise ValueError("影子账本决定失败")
    return {
        "metrics": {k: v for k, v in actual["metrics"].items() if k != "execution_orders"},
        "baseline_metrics": {k: v for k, v in baseline["metrics"].items() if k != "execution_orders"},
        "net_excess": actual["metrics"]["total_return"] - baseline["metrics"]["total_return"],
        "curve": actual["curve"],
        "orders": actual["orders"],
        "trades": actual["trades"],
        "accounting": "actual_same_cost_portfolio_ledger_not_mean_of_stock_returns",
    }
