"""Composition through the existing persistent backtest lifecycle."""

from src.core.logger import get_logger
from src.engine.execution.runtime import prepare_execution
from src.strategy.composition.config import fail
from src.strategy.composition.store import PipelineStore
from src.strategy.composition.validation import digest

from .data import load_snapshot
from .preflight import preflight
from .simulation import CompositionSimulation


class CompositionBacktestEngine:
    key = "composition"
    label = "组合目标权重引擎"
    description = "按日期对齐、子策略净额及独立风控的日线研究引擎。"

    def run(self, payload, symbols, initial_cash, strategy=None, data=None):
        if strategy is None or strategy.entry_name != "CompositePipelineStrategy":
            raise fail("execution_only")
        store = PipelineStore()
        params = payload.get("params") or {}
        version = store.version(int(params["pipeline_version"]), True)
        if (
            version["pipeline_id"] != int(params["pipeline_id"])
            or payload.get("strategy_id")
            and version["strategy_id"] != int(payload["strategy_id"])
        ):
            raise fail("invalid", "version binding")
        if store.repo.get("strategy_pipelines", version["pipeline_id"])["status"] == "disabled":
            raise fail("invalid", "pipeline disabled")
        log = get_logger("composition.backtest")

        def emit(kind, text, value=None):
            if payload.get("_checkpoint"):
                payload["_checkpoint"]()
            log.debug("{} | {} | {}", kind, text, value)

        request = {
            **payload,
            "symbols": symbols,
            "market": payload.get("market") or "CN",
            "mode": "backtest",
            "agent_mode": "off",
        }
        plan = prepare_execution(version["compiled"], request)
        snapshot = load_snapshot(request, plan, emit, data)
        preflight(plan, snapshot, request)
        plan["execution"] = {**plan["execution"], "initial_capital": initial_cash}
        result = CompositionSimulation(plan, snapshot, request, store, emit).run()
        if result["decision_errors"]:
            raise fail("unavailable", result["decision_errors"])
        metrics = {
            **result["metrics"],
            "data_source": snapshot["source"],
            "is_mock": snapshot["is_mock"],
            "data_fingerprint": digest(snapshot["history"]),
            "bars_by_symbol": {s: len(rows) for s, rows in snapshot["history"].items()},
            "pipeline_version": version["id"],
            "pipeline_digest": version["digest"],
            "pipeline_diagnostics": result["diagnostics"],
            "pipeline_targets": result["targets"],
            "pipeline_orders": result["orders"],
            "pipeline_limitations": result["limitations"],
        }
        return metrics, result["curve"], result["trades"]
