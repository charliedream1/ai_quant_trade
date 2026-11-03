"""Backtest runner that persists task metadata and executable results."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.logger import get_logger
from src.core.repository import Repository, json_loads
from src.core.security_config import security_config
from src.core.task_control import TaskEvent
from src.core.timeutil import utc_now_iso
from src.data import DataSourceManager
from src.engine.execution.config import resolve_costs
from src.strategy import StrategyLoader, StrategyStore
from src.strategy.parameters import StrategyParameters

from .capabilities import resolve_engine, strategy_capability
from .engines import (
    DEFAULT_COMMISSION_RATE,
    _lot_size,
    _max_position_count,
    _max_position_weight,
    _normalize_order_type,
    _normalize_price_adjustment,
    engine_diagnostics,
    get_backtest_engine,
)
from .experiments import complete_snapshot, experiment_snapshot

SymbolList = list[str]
LOG = get_logger("backtest.runner")


class BacktestRunner:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()

    def create(self, payload: dict[str, Any], *, deferred: bool = False) -> dict[str, Any]:
        strategy_id = int(payload["strategy_id"])
        self.repo.get("strategies", strategy_id)
        symbols = _normalize_symbols(payload.get("symbols") or payload.get("universe") or ["000001"])
        resolution = StrategyParameters(repo=self.repo).resolve(
            strategy_id, payload.get("params"), payload.get("parameter_profile")
        )
        params = resolution["resolved_params"]
        capability = strategy_capability(strategy_id, params, self.repo)
        engine_key = resolve_engine(payload.get("engine"), capability)
        if engine_key == "qlib" and payload.get("execution_costs"):
            raise BusinessError(
                ErrorCode.INVALID_PARAM, "Qlib原生Workflow费用需在Workflow配置；不接受未映射的通用执行覆盖"
            )
        execution_config = _execution_config({"order_type": capability["order_type"], **payload})
        if engine_key == "composition":
            execution_config.update(
                {
                    "order_type": "open",
                    "price_adjustment": "none",
                    "lot_size": capability["execution"]["lot_size"],
                    "slippage_rate": capability["execution"]["slippage_rate"],
                    "max_position_weight": capability["risk"]["max_weight"],
                    "max_position_count": capability["risk"]["max_positions"],
                }
            )
        strategy_store = StrategyStore(repo=self.repo)
        interface_report = strategy_store.interface_report(strategy_id, params=deepcopy(params), symbols=symbols)
        if not interface_report.get("valid"):
            raise BusinessError(
                ErrorCode.STRATEGY_INVALID, f"策略标准端口预检失败：{interface_report.get('error', '未知错误')}"
            )
        now = utc_now_iso()
        initial_cash = float(payload.get("initial_capital") or payload.get("initial_cash") or 1000000)
        commission_rate = float(
            payload["commission_rate"] if payload.get("commission_rate") is not None else DEFAULT_COMMISSION_RATE
        )
        if engine_key == "composition":
            commission_rate = float(capability["execution"]["commission_rate"])
        costs = resolve_costs(
            payload.get("execution_costs"),
            {**capability["execution"], **execution_config, "commission_rate": commission_rate},
        )
        execution_config.update(
            execution_costs=costs, slippage_rate=costs["slippage_rate"], lot_size=int(costs["lot_size"])
        )
        commission_rate = costs["buy_commission_rate"]
        if engine_key == "qlib":
            execution_config.pop("execution_costs", None)
        run_payload = {
            **payload,
            **execution_config,
            "params": params,
            "engine": engine_key,
            "initial_capital": initial_cash,
            "commission_rate": commission_rate,
        }
        snapshot = experiment_snapshot(resolution, run_payload, symbols, execution_config)
        LOG.info(
            "backtest parameters resolved | strategy_id={} profile={} parameter_count={} source_sha256={}",
            strategy_id,
            (resolution["profile"] or {}).get("id") or "defaults",
            len(params),
            snapshot["strategy"]["source_sha256"],
        )
        task = self.repo.insert(
            "backtest_tasks",
            {
                "strategy_id": strategy_id,
                "engine": engine_key,
                "symbols": json.dumps(symbols, ensure_ascii=False),
                "start_date": payload["start_date"],
                "end_date": payload["end_date"],
                "initial_cash": initial_cash,
                "commission_rate": commission_rate,
                "params": json.dumps(_stored_params(params, execution_config, snapshot), ensure_ascii=False),
                "benchmark": payload.get("benchmark") or "等权标的基准",
                "status": "queued",
                "progress": 0,
                "current_date": "",
                "error_msg": "",
                "created_at": now,
                "started_at": None,
                "finished_at": None,
            },
        )
        if deferred:
            return self.detail(task["id"])
        return self.execute(task["id"], run_payload=run_payload)

    def execute(
        self, task_id: int, *, run_payload: dict[str, Any] | None = None, checkpoint=None, data=None, _owned_event=None
    ) -> dict[str, Any]:
        task = self.detail(task_id)
        if task["status"] in {"finished", "failed", "cancelled", "timeout"}:
            raise BusinessError(ErrorCode.INVALID_PARAM, "该回测已结束，请创建新任务而非覆盖旧结果")
        lease = None
        try:
            lease = (
                None
                if _owned_event is not None
                else TaskEvent("backtest", task_id, self.repo, security_config()["limits"]["backtest_pending"])
            )
        except ValueError as exc:
            self.repo.update(
                "backtest_tasks", task_id, {"status": "failed", "error_msg": str(exc), "finished_at": utc_now_iso()}
            )
            raise BusinessError(ErrorCode.INVALID_PARAM, str(exc), {"task_id": task_id}) from exc
        stop = _owned_event or lease
        assert stop is not None

        def check():
            if checkpoint:
                checkpoint()
            if stop.is_set():
                raise InterruptedError("已在安全检查点停止回测")

        try:
            return self._execute_task(task_id, run_payload=run_payload, checkpoint=check, data=data)
        finally:
            if lease:
                lease.close()

    def _execute_task(
        self, task_id: int, *, run_payload: dict[str, Any] | None = None, checkpoint=None, data=None
    ) -> dict[str, Any]:
        task = self.detail(task_id)
        stored = dict(task["params"])
        execution = stored.pop("_backtest", {})
        snapshot = task["parameter_snapshot"]
        payload = run_payload or {**snapshot["run"], **execution, "strategy_id": task["strategy_id"], "params": stored}
        payload = {**payload, "_checkpoint": checkpoint, "_cost_policy": execution.get("execution_costs")}
        self.repo.update("backtest_tasks", task_id, {"status": "running", "started_at": utc_now_iso(), "progress": 5})
        try:
            if checkpoint:
                checkpoint()
            row = self.repo.get("strategies", task["strategy_id"])
            storage = StrategyStore(repo=self.repo).storage
            current_source = storage.read_text(row["file_path"])
            if hashlib.sha256(current_source.encode("utf-8")).hexdigest() != snapshot["strategy"]["source_sha256"]:
                raise BusinessError(ErrorCode.STRATEGY_INVALID, "策略源码已改变，请创建新回测任务")
            loaded = StrategyLoader(StrategyStore(repo=self.repo).storage).load_from_file(
                row["file_path"], params=deepcopy(stored)
            )
            metrics, curve, trades = get_backtest_engine(task["engine"]).run(
                payload,
                task["symbols"],
                task["initial_cash"],
                strategy=loaded.adapter,
                data=data or DataSourceManager(),
            )
            if checkpoint:
                checkpoint()
            with self.repo.db.transaction():
                self._save_result(task_id, stored, execution, snapshot, metrics, curve, trades)
        except Exception as exc:
            state = (
                "cancelled"
                if isinstance(exc, InterruptedError)
                else "timeout"
                if isinstance(exc, TimeoutError)
                else "failed"
            )
            self.repo.update(
                "backtest_tasks", task_id, {"status": state, "error_msg": str(exc), "finished_at": utc_now_iso()}
            )
            LOG.exception("backtest failed | task_id={}", task_id)
            raise BusinessError(
                getattr(exc, "code", ErrorCode.UNKNOWN), f"回测任务 {task_id}：{exc}", {"task_id": task_id}
            ) from exc
        return self.detail(task_id)

    def _save_result(self, task_id, params, execution, snapshot, metrics, curve, trades) -> None:
        complete_snapshot(snapshot, metrics, curve)
        now = utc_now_iso()
        self.repo.insert(
            "backtest_results",
            {
                "task_id": task_id,
                "metrics": json.dumps(metrics, ensure_ascii=False),
                "equity_curve": json.dumps(curve, ensure_ascii=False),
                "trades": json.dumps(trades, ensure_ascii=False),
                "trades_path": "",
                "report_path": "",
                "created_at": now,
            },
        )
        self.repo.update(
            "backtest_tasks",
            task_id,
            {
                "status": "finished",
                "progress": 100,
                "finished_at": now,
                "current_date": (curve.get("dates") or [""])[-1],
                "params": _stored_params(params, execution, snapshot),
                "benchmark": metrics.get("benchmark_label") or "等权标的基准",
            },
        )
        LOG.info(
            "backtest experiment saved | task_id={} data_source={} points={}",
            task_id,
            snapshot["data"]["source"],
            snapshot["data"]["equity_points"],
        )

    def engines(self) -> list[dict[str, str]]:
        return engine_diagnostics()

    def list(
        self, strategy_id: int | None = None, status: str | None = None, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        where: list[str] = []
        params: list[Any] = []
        if strategy_id:
            where.append("strategy_id = ?")
            params.append(strategy_id)
        if status:
            where.append("status = ?")
            params.append(status)
        result = self.repo.page(
            "backtest_tasks", page, page_size, " AND ".join(where), params, order_by="created_at DESC"
        )
        for item in result["items"]:
            item["task_id"] = item["id"]
            item["symbols"] = json_loads(item.get("symbols"), [])
            item["params"] = json_loads(item.get("params"), {})
            item["parameter_snapshot"] = item["params"].pop("_experiment", None)
        return result

    def detail(self, task_id: int) -> dict[str, Any]:
        row = self.repo.get("backtest_tasks", task_id)
        row["task_id"] = row["id"]
        row["symbols"] = json_loads(row.get("symbols"), [])
        row["params"] = json_loads(row.get("params"), {})
        row["parameter_snapshot"] = row["params"].pop("_experiment", None)
        return row

    def delete(self, task_id: int) -> None:
        self.repo.delete("backtest_tasks", task_id)

    def performance(self, task_id: int) -> dict[str, Any]:
        row = self.repo.db.query_one("SELECT * FROM backtest_results WHERE task_id = ?", (task_id,))
        if not row:
            from src.core.exceptions import BusinessError, ErrorCode

            raise BusinessError(ErrorCode.TASK_NOT_FINISHED, "回测任务尚未完成")
        return json.loads(row["metrics"])

    def equity_curve(self, task_id: int) -> dict[str, Any]:
        row = self.repo.db.query_one("SELECT * FROM backtest_results WHERE task_id = ?", (task_id,))
        if not row:
            from src.core.exceptions import BusinessError, ErrorCode

            raise BusinessError(ErrorCode.TASK_NOT_FINISHED, "回测任务尚未完成")
        return json.loads(row["equity_curve"])

    def trades(self, task_id: int, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        row = self.repo.db.query_one("SELECT * FROM backtest_results WHERE task_id = ?", (task_id,))
        trades = json.loads(row["trades"] or "[]") if row else []
        start = (max(page, 1) - 1) * page_size
        return {"items": trades[start : start + page_size], "page": page, "page_size": page_size, "total": len(trades)}

    def attribution(self, task_id: int) -> dict[str, Any]:
        task = self.repo.get("backtest_tasks", task_id)
        row = self.repo.db.query_one("SELECT * FROM backtest_results WHERE task_id = ?", (task_id,))
        if not row:
            from src.core.exceptions import BusinessError, ErrorCode

            raise BusinessError(ErrorCode.TASK_NOT_FINISHED, "回测任务尚未完成")
        return _build_attribution(
            task,
            json_loads(row.get("metrics"), {}),
            json_loads(row.get("equity_curve"), {}),
            json_loads(row.get("trades"), []),
        )


def _normalize_symbols(value: Any) -> SymbolList:
    if isinstance(value, str):
        parts = value.replace("，", ",").replace(";", ",").replace(" ", ",").split(",")
        return [item.strip() for item in parts if item.strip()] or ["000001"]
    if isinstance(value, list | tuple | set):
        symbols = [str(item).strip() for item in value if str(item).strip()]
        return symbols or ["000001"]
    return ["000001"]


def _execution_config(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_type": _normalize_order_type(payload.get("order_type")),
        "price_adjustment": _normalize_price_adjustment(payload.get("price_adjustment")),
        "max_position_count": _max_position_count(payload),
        "max_position_weight": _max_position_weight(payload),
        "lot_size": _lot_size(payload),
        "slippage_rate": max(_execution_float(payload.get("slippage_rate"), 0.0), 0.0),
    }


def _stored_params(params: Any, execution_config: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    if isinstance(params, dict):
        stored = dict(params)
    else:
        stored = {}
    stored["_backtest"] = execution_config
    stored["_experiment"] = snapshot
    return stored


def _execution_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def _build_attribution(
    task: dict[str, Any], metrics: dict[str, Any], curve: dict[str, Any], trades: list[dict[str, Any]]
) -> dict[str, Any]:
    by_symbol = _group_trade_attribution(trades, "symbol", float(task.get("initial_cash") or 0.0))
    by_signal = _group_trade_attribution(trades, "signal", float(task.get("initial_cash") or 0.0))
    drawdown = _drawdown_attribution(curve)
    summary = _attribution_summary(metrics, by_symbol, drawdown)
    risks = _risk_flags(metrics, by_symbol, trades)
    return {
        "summary": summary,
        "by_symbol": by_symbol,
        "by_signal": by_signal,
        "drawdown": drawdown,
        "risk_flags": risks,
    }


def _group_trade_attribution(trades: list[dict[str, Any]], key: str, initial_cash: float) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for trade in trades:
        name = str(trade.get(key) or "未标记")
        pnl = _float(trade.get("pnl"))
        bucket = grouped.setdefault(name, {"name": name, "trade_count": 0, "pnl": 0.0, "wins": 0})
        bucket["trade_count"] += 1
        bucket["pnl"] += pnl
        if pnl > 0:
            bucket["wins"] += 1
    rows = []
    for item in grouped.values():
        trade_count = int(item["trade_count"])
        pnl = float(item["pnl"])
        rows.append(
            {
                "name": item["name"],
                "trade_count": trade_count,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl / initial_cash, 4) if initial_cash else 0.0,
                "win_rate": round(int(item["wins"]) / trade_count, 4) if trade_count else 0.0,
            }
        )
    return sorted(rows, key=lambda row: abs(float(row["pnl"])), reverse=True)


def _drawdown_attribution(curve: dict[str, Any]) -> dict[str, Any]:
    dates = list(curve.get("dates") or [])
    equity = [float(item) for item in curve.get("equity") or []]
    drawdown = [float(item) for item in curve.get("drawdown") or []]
    if not dates or not equity or (not drawdown):
        return {"max_drawdown": 0.0, "peak_date": "", "trough_date": "", "peak_equity": 0.0, "trough_equity": 0.0}
    trough_index = min(range(len(drawdown)), key=lambda index: drawdown[index])
    peak_index = max(range(trough_index + 1), key=lambda index: equity[index])
    return {
        "max_drawdown": round(drawdown[trough_index], 4),
        "peak_date": dates[peak_index],
        "trough_date": dates[trough_index],
        "peak_equity": round(equity[peak_index], 2),
        "trough_equity": round(equity[trough_index], 2),
    }


def _attribution_summary(
    metrics: dict[str, Any], by_symbol: list[dict[str, Any]], drawdown: dict[str, Any]
) -> list[dict[str, Any]]:
    best = max(by_symbol, key=lambda row: float(row["pnl"]), default={})
    losses = [row for row in by_symbol if float(row["pnl"]) < 0]
    worst = min(losses, key=lambda row: float(row["pnl"]), default={})
    return [
        {
            "item": "收益来源",
            "value": best.get("name") or "-",
            "note": f"贡献 {best.get('pnl', 0.0):+.2f}" if best else "暂无交易",
        },
        {
            "item": "主要拖累",
            "value": worst.get("name") or "-",
            "note": f"贡献 {worst.get('pnl', 0.0):+.2f}" if worst else "暂无亏损标的",
        },
        {
            "item": "最大回撤段",
            "value": f"{drawdown.get('peak_date', '')} → {drawdown.get('trough_date', '')}",
            "note": _percent(_float(drawdown.get("max_drawdown"))),
        },
        {
            "item": "交易画像",
            "value": f"{int(_float(metrics.get('trade_count')))} 笔",
            "note": f"胜率 {_percent(_float(metrics.get('win_rate')))} / 盈亏比 {_float(metrics.get('profit_loss_ratio')):.2f}",
        },
    ]


def _risk_flags(
    metrics: dict[str, Any], by_symbol: list[dict[str, Any]], trades: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if _float(metrics.get("max_drawdown")) <= -0.08:
        rows.append({"severity": "warning", "title": "回撤偏大", "message": "最大回撤超过 8%，需要复核仓位和止损。"})
    if _float(metrics.get("win_rate")) < 0.45 and trades:
        rows.append(
            {"severity": "warning", "title": "胜率偏低", "message": "胜率低于 45%，建议拆分市场环境检查信号质量。"}
        )
    if len(trades) < 3:
        rows.append({"severity": "info", "title": "样本偏少", "message": "交易笔数不足 3 笔，归因结论仅作流程验证。"})
    total_abs_pnl = sum(abs(float(row["pnl"])) for row in by_symbol)
    if by_symbol and total_abs_pnl > 0:
        top = by_symbol[0]
        concentration = abs(float(top["pnl"])) / total_abs_pnl
        if concentration >= 0.65:
            rows.append(
                {
                    "severity": "info",
                    "title": "收益集中",
                    "message": f"{top['name']} 贡献占绝对盈亏 {_percent(concentration)}，需要扩展股票池验证。",
                }
            )
    return rows


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _percent(value: float) -> str:
    return f"{value * 100:+.2f}%"
