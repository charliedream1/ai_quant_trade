"""Live trading configuration and run state manager."""

import json
from datetime import datetime, timezone
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.integration.broker import default_broker_registry

VALIDATION_PARAM_KEY = "_live_validation"
LIVE_STATUS_STARTING = "starting"
LIVE_STATUS_RUNNING = "running"
LIVE_STATUS_PAUSED = "paused"
LIVE_STATUS_STOPPING = "stopping"
LIVE_STATUS_STOPPED = "stopped"
LIVE_STATUS_ERROR = "error"
ACTIVE_RUN_STATUSES = {
    LIVE_STATUS_STARTING,
    LIVE_STATUS_RUNNING,
    LIVE_STATUS_PAUSED,
    LIVE_STATUS_STOPPING,
    LIVE_STATUS_ERROR,
}
TERMINAL_RUN_STATUSES = {LIVE_STATUS_STOPPED}
PAUSABLE_RUN_STATUSES = {LIVE_STATUS_RUNNING}
RESUMABLE_RUN_STATUSES = {LIVE_STATUS_PAUSED, LIVE_STATUS_ERROR}
STOPPABLE_RUN_STATUSES = ACTIVE_RUN_STATUSES
STATUS_LABELS = {
    LIVE_STATUS_STARTING: "启动中",
    LIVE_STATUS_RUNNING: "运行中",
    LIVE_STATUS_PAUSED: "已暂停",
    LIVE_STATUS_STOPPING: "停止中",
    LIVE_STATUS_STOPPED: "已停止",
    LIVE_STATUS_ERROR: "错误",
}


class LiveTradingService:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()

    def list_configs(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        result = self.repo.page("live_configs", page, page_size, order_by="updated_at DESC, id DESC")
        for item in result["items"]:
            self._shape_config(item)
        return result

    def create_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.repo.get("strategies", int(payload["strategy_id"]))
        now = utc_now_iso()
        row = self.repo.insert(
            "live_configs",
            {
                "name": payload["name"],
                "strategy_id": payload["strategy_id"],
                "params": json.dumps(payload.get("params") or {}, ensure_ascii=False),
                "channel": payload.get("channel") or "paper",
                "capital": float(payload.get("capital") or 100000),
                "risk_controls": json.dumps(
                    payload.get("risk_controls") or {"max_position_count": 5, "daily_loss_limit": 0.03},
                    ensure_ascii=False,
                ),
                "status": "启用",
                "created_at": now,
                "updated_at": now,
            },
        )
        return self.detail_config(row["id"])

    def detail_config(self, config_id: int) -> dict[str, Any]:
        return self._shape_config(self.repo.get("live_configs", config_id))

    def update_config(self, config_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, Any] = {"updated_at": utc_now_iso()}
        for key in ("name", "strategy_id", "channel", "capital", "status"):
            if key in payload and payload[key] is not None:
                values[key] = payload[key]
        if "params" in payload:
            values["params"] = json.dumps(payload["params"] or {}, ensure_ascii=False)
        if "risk_controls" in payload:
            values["risk_controls"] = json.dumps(payload["risk_controls"] or {}, ensure_ascii=False)
        self.repo.update("live_configs", config_id, values)
        return self.detail_config(config_id)

    def delete_config(self, config_id: int) -> None:
        self.repo.delete("live_configs", config_id)

    def patch_risk(self, config_id: int, risk_controls: dict[str, Any]) -> dict[str, Any]:
        config = self.repo.get("live_configs", config_id)
        merged = json_loads(config.get("risk_controls"), {})
        merged.update(risk_controls or {})
        self.repo.update(
            "live_configs",
            config_id,
            {"risk_controls": json.dumps(merged, ensure_ascii=False), "updated_at": utc_now_iso()},
        )
        return merged

    def validation_checks(self, config_id: int) -> list[dict[str, Any]]:
        config = self.detail_config(config_id)
        return _validation_checks(config, self.repo)

    def start_blockers(self, config_id: int) -> list[str]:
        config = self.detail_config(config_id)
        return _start_blockers(config, self.repo)

    def start_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = self.detail_config(int(payload["config_id"]))
        blockers = _start_blockers(config, self.repo)
        if blockers:
            raise BusinessError(
                ErrorCode.LIVE_PRECHECK_FAILED,
                "实盘前置校验失败：" + "；".join(blockers),
                {"blockers": blockers, "validation": _validation_checks(config, self.repo)},
            )
        if str(config.get("status") or "") not in {"启用", "enabled", "active"}:
            raise BusinessError(ErrorCode.LIVE_STATE_ERROR, f"配置 {config['id']} 未启用，不能启动运行")
        active_run = self._active_run(int(config["id"]))
        if active_run:
            raise BusinessError(
                ErrorCode.LIVE_STATE_ERROR,
                f"配置 {config['id']} 已有运行 {active_run['id']} 处于 {active_run['status']} 状态",
                {"run_id": active_run["id"], "status": active_run["status"]},
            )
        now = utc_now_iso()
        row = self.repo.insert(
            "live_runs",
            {
                "config_id": config["id"],
                "status": LIVE_STATUS_STARTING,
                "started_at": now,
                "stopped_at": None,
                "heartbeat_at": now,
                "error_msg": "",
                "log_path": "",
            },
        )
        self.repo.update("live_runs", int(row["id"]), {"status": LIVE_STATUS_RUNNING, "heartbeat_at": utc_now_iso()})
        return self.status(row["id"])

    def stop_run(self, run_id: int, graceful: bool = True) -> dict[str, Any]:
        row = self.repo.get("live_runs", run_id)
        status = str(row.get("status") or "")
        if status in TERMINAL_RUN_STATUSES:
            raise BusinessError(ErrorCode.LIVE_STATE_ERROR, f"运行 {run_id} 已处于终态：{_status_label(status)}")
        if status not in STOPPABLE_RUN_STATUSES:
            raise BusinessError(ErrorCode.LIVE_STATE_ERROR, f"运行 {run_id} 状态不允许停止：{status or '-'}")
        now = utc_now_iso()
        self.repo.update("live_runs", run_id, {"status": LIVE_STATUS_STOPPING, "heartbeat_at": now})
        self.repo.update(
            "live_runs",
            run_id,
            {"status": LIVE_STATUS_STOPPED, "stopped_at": utc_now_iso(), "heartbeat_at": utc_now_iso()},
        )
        return self.status(run_id)

    def pause_run(self, run_id: int) -> dict[str, Any]:
        row = self.repo.get("live_runs", run_id)
        status = str(row.get("status") or "")
        if status not in PAUSABLE_RUN_STATUSES:
            raise BusinessError(ErrorCode.LIVE_STATE_ERROR, f"运行 {run_id} 状态不允许暂停：{_status_label(status)}")
        self.repo.update("live_runs", run_id, {"status": LIVE_STATUS_PAUSED, "heartbeat_at": utc_now_iso()})
        return self.status(run_id)

    def resume_run(self, run_id: int) -> dict[str, Any]:
        row = self.repo.get("live_runs", run_id)
        status = str(row.get("status") or "")
        if status not in RESUMABLE_RUN_STATUSES:
            raise BusinessError(ErrorCode.LIVE_STATE_ERROR, f"运行 {run_id} 状态不允许恢复：{_status_label(status)}")
        self.repo.update(
            "live_runs",
            run_id,
            {"status": LIVE_STATUS_RUNNING, "heartbeat_at": utc_now_iso(), "error_msg": ""},
        )
        return self.status(run_id)

    def mark_error(self, run_id: int, message: str | None = None) -> dict[str, Any]:
        row = self.repo.get("live_runs", run_id)
        status = str(row.get("status") or "")
        if status in TERMINAL_RUN_STATUSES:
            raise BusinessError(ErrorCode.LIVE_STATE_ERROR, f"运行 {run_id} 已处于终态：{_status_label(status)}")
        reason = str(message or "").strip() or "人工标记异常冻结"
        self.repo.update(
            "live_runs",
            run_id,
            {"status": LIVE_STATUS_ERROR, "heartbeat_at": utc_now_iso(), "error_msg": reason},
        )
        return self.status(run_id)

    def status(self, run_id: int) -> dict[str, Any]:
        row = self.repo.get("live_runs", run_id)
        status = str(row.get("status") or "")
        uptime_seconds = _uptime_seconds(row.get("started_at"), row.get("stopped_at"))
        return {
            "run_id": row["id"],
            "config_id": row["config_id"],
            "status": status,
            "status_label": _status_label(status),
            "terminal": status in TERMINAL_RUN_STATUSES,
            "can_pause": status in PAUSABLE_RUN_STATUSES,
            "can_resume": status in RESUMABLE_RUN_STATUSES,
            "can_stop": status in STOPPABLE_RUN_STATUSES,
            "frozen": status == LIVE_STATUS_ERROR,
            "uptime_seconds": uptime_seconds,
            "today_trade_count": 0,
            "today_pnl": 0.0,
            "last_heartbeat_at": row["heartbeat_at"],
            "last_error": row.get("error_msg") or "",
        }

    def orders(
        self,
        run_id: int,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        where = "run_id = ?"
        params: list[Any] = [run_id]
        if status:
            where += " AND status = ?"
            params.append(status)
        return self.repo.page("live_orders", page, page_size, where, params, order_by="created_at DESC")

    def positions(self, run_id: int):
        row = self.repo.get("live_runs", run_id)
        config = self.repo.get("live_configs", row["config_id"])
        return [
            {
                "symbol": "CASH",
                "name": "模拟现金",
                "quantity": 1,
                "available_qty": 1,
                "avg_cost": config["capital"],
                "latest_price": config["capital"],
                "market_value": config["capital"],
                "channel_check": "ok",
            }
        ]

    def _shape_config(self, row: dict[str, Any]) -> dict[str, Any]:
        row["config_id"] = row["id"]
        row["params"] = json_loads(row.get("params"), {})
        row["risk_controls"] = json_loads(row.get("risk_controls"), {})
        return row

    def _active_run(self, config_id: int) -> dict[str, Any] | None:
        placeholders = ", ".join("?" for _ in ACTIVE_RUN_STATUSES)
        return self.repo.db.query_one(
            f"""SELECT *
                  FROM live_runs
                 WHERE config_id = ?
                   AND status IN ({placeholders})
                 ORDER BY started_at DESC, id DESC
                 LIMIT 1""",
            (config_id, *sorted(ACTIVE_RUN_STATUSES)),
        )


def _start_blockers(config: dict[str, Any], repo: Repository) -> list[str]:
    risk = config.get("risk_controls") or {}
    blockers: list[str] = []
    adapter_blocker = default_broker_registry().start_blocker(str(config.get("channel") or "paper"))
    if adapter_blocker:
        blockers.append(adapter_blocker)
    if _safe_float(config.get("capital")) <= 0:
        blockers.append("资金规模必须大于 0")
    if _safe_float(risk.get("max_position_count")) <= 0:
        blockers.append("缺少 max_position_count")
    if _safe_float(risk.get("daily_loss_limit")) <= 0:
        blockers.append("缺少 daily_loss_limit")
    for row in _validation_checks(config, repo):
        if row.get("状态") == "拦截":
            blockers.append(f"{row.get('检查项')}：{row.get('说明')}")
    return blockers


def _validation_checks(config: dict[str, Any], repo: Repository) -> list[dict[str, Any]]:
    validation = _validation_payload(config)
    strategy_id = _optional_int(config.get("strategy_id"))
    return [
        _backtest_validation_row(validation.get("backtest_id"), strategy_id, repo),
        _paper_validation_row(validation.get("paper_account_id"), strategy_id, repo),
    ]


def _validation_payload(config: dict[str, Any]) -> dict[str, int | None]:
    params = config.get("params") if isinstance(config.get("params"), dict) else json_loads(config.get("params"), {})
    raw: dict[str, Any] = {}
    if isinstance(params, dict):
        raw = params.get(VALIDATION_PARAM_KEY) or params.get("live_validation") or params.get("validation") or {}
    if not isinstance(raw, dict):
        raw = {}
    return {
        "backtest_id": _optional_int(raw.get("backtest_id") or raw.get("backtest_task_id")),
        "paper_account_id": _optional_int(raw.get("paper_account_id") or raw.get("account_id")),
    }


def _backtest_validation_row(backtest_id: int | None, strategy_id: int | None, repo: Repository) -> dict[str, Any]:
    if not backtest_id:
        return _check_row("回测验证", "-", "拦截", "缺少验证回测 ID，发布前必须选择已完成回测")
    task = repo.get_optional("backtest_tasks", backtest_id)
    if not task:
        return _check_row("回测验证", f"回测 {backtest_id}", "拦截", "验证回测不存在")
    task_strategy = _optional_int(task.get("strategy_id"))
    if strategy_id and task_strategy and task_strategy != strategy_id:
        return _check_row(
            "回测验证",
            f"回测 {backtest_id}",
            "拦截",
            f"回测策略 {task_strategy} 与配置策略 {strategy_id} 不一致",
        )
    status = str(task.get("status") or "").lower()
    if status not in {"finished", "success", "done", "已完成", "完成", "成功"}:
        return _check_row("回测验证", f"回测 {backtest_id}", "拦截", f"回测状态为 {task.get('status') or '-'}")
    result = repo.db.query_one("SELECT * FROM backtest_results WHERE task_id = ?", (backtest_id,))
    if not result:
        return _check_row("回测验证", f"回测 {backtest_id}", "拦截", "回测结果缺失，不能作为发布证据")
    metrics = json_loads(result.get("metrics"), {})
    total_return = _safe_float(metrics.get("total_return"))
    max_drawdown = _safe_float(metrics.get("max_drawdown"))
    trade_count = int(_safe_float(metrics.get("trade_count")))
    state = "警告" if trade_count <= 0 or total_return < -0.2 else "通过"
    note = (
        f"状态 {task.get('status')}，总收益 {_percent(total_return)}，"
        f"最大回撤 {_percent(max_drawdown)}，交易 {trade_count} 笔"
    )
    return _check_row("回测验证", f"回测 {backtest_id}", state, note)


def _paper_validation_row(account_id: int | None, strategy_id: int | None, repo: Repository) -> dict[str, Any]:
    if not account_id:
        return _check_row("模拟验证", "-", "拦截", "缺少验证模拟账户 ID，发布前必须选择模拟账户")
    account = repo.get_optional("paper_accounts", account_id)
    if not account:
        return _check_row("模拟验证", f"账户 {account_id}", "拦截", "验证模拟账户不存在")
    account_strategy = _optional_int(account.get("strategy_id"))
    if strategy_id and account_strategy and account_strategy != strategy_id:
        return _check_row(
            "模拟验证",
            f"账户 {account_id}",
            "拦截",
            f"模拟账户策略 {account_strategy} 与配置策略 {strategy_id} 不一致",
        )
    nav_count = int(repo.db.scalar("SELECT COUNT(*) FROM paper_nav_history WHERE account_id = ?", (account_id,)) or 0)
    position_count = int(
        repo.db.scalar("SELECT COUNT(*) FROM paper_positions WHERE account_id = ?", (account_id,)) or 0
    )
    order_count = int(repo.db.scalar("SELECT COUNT(*) FROM paper_orders WHERE account_id = ?", (account_id,)) or 0)
    state = "通过" if nav_count > 0 else "警告"
    note = (
        f"状态 {account.get('status') or '-'}，净值快照 {nav_count} 条，持仓 {position_count} 个，委托 {order_count} 笔"
    )
    if account_strategy is None:
        state = "警告"
        note += "；账户未绑定策略，请人工确认来源"
    return _check_row("模拟验证", f"账户 {account_id}", state, note)


def _check_row(item: str, value: str, status: str, note: str) -> dict[str, Any]:
    return {"检查项": item, "当前值": value, "状态": status, "说明": note}


def _optional_int(value: Any) -> int | None:
    try:
        result = int(float(value))
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _percent(value: Any) -> str:
    return f"{_safe_float(value):.2%}"


def _status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status or "-")


def _uptime_seconds(started_at: Any, stopped_at: Any = None) -> int:
    started = _parse_utc(started_at)
    if started is None:
        return 0
    ended = _parse_utc(stopped_at) or datetime.now(timezone.utc)
    return max(int((ended - started).total_seconds()), 0)


def _parse_utc(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
