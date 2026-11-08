"""Quant workflow SOP, attribution and iteration services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from src.core.logger import get_logger
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOP_PATH = PROJECT_ROOT / "egs" / "config" / "platform" / "quant_workflow_sops.yaml"

SIMULATION_MODE = "simulation"
LIVE_MODE = "live"
WORKFLOW_MODES = {SIMULATION_MODE, LIVE_MODE}

DRAWDOWN_WARNING = -0.08
LOW_SHARPE_WARNING = 0.5
LOW_WIN_RATE_WARNING = 0.45
LOW_FACTOR_IC_WARNING = 0.02
HIGH_PENDING_ORDER_COUNT = 0
HIGH_CONCENTRATION_RATIO = 0.45


class QuantWorkflowService:
    """Build auditable quant workflow snapshots from platform data."""

    def __init__(
        self,
        repo: Repository | None = None,
        sop_path: Path | None = None,
    ) -> None:
        self.repo = repo or Repository()
        self.sop_path = sop_path or DEFAULT_SOP_PATH
        self.log = get_logger("quant_workflow")

    def modes(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._config().get("workflow_modes") or [] if isinstance(item, dict)]

    def sops(self, mode: str | None = None) -> list[dict[str, Any]]:
        selected_mode = _normalize_mode(mode) if mode else ""
        rows: list[dict[str, Any]] = []
        for item in self._config().get("sops") or []:
            if not isinstance(item, dict):
                continue
            if selected_mode and item.get("mode") != selected_mode:
                continue
            rows.append(dict(item))
        return rows

    def snapshot(
        self,
        mode: str = SIMULATION_MODE,
        sop_id: str | None = None,
        strategy_id: int | None = None,
        backtest_id: int | None = None,
        account_id: int | None = None,
        live_run_id: int | None = None,
    ) -> dict[str, Any]:
        selected_mode = _normalize_mode(mode)
        sop = self._select_sop(selected_mode, sop_id)
        context = {
            "mode": selected_mode,
            "sop_id": sop["id"],
            "strategy_id": strategy_id,
            "backtest_id": backtest_id,
            "account_id": account_id,
            "live_run_id": live_run_id,
        }
        evidence = self._collect_evidence(
            selected_mode,
            strategy_id=strategy_id,
            backtest_id=backtest_id,
            account_id=account_id,
            live_run_id=live_run_id,
        )
        insights = self._build_insights(selected_mode, evidence)
        advice = self._build_advice(selected_mode, evidence, insights)
        questions = self._build_questions(selected_mode, evidence, insights, advice)
        artifacts = self._build_artifacts(selected_mode, evidence, insights, advice)
        steps = self._build_steps(sop, evidence, insights, advice)
        summary = self._summary(selected_mode, evidence, insights, advice)
        return {
            "mode": selected_mode,
            "sop": _public_sop(sop),
            "context": context,
            "summary": summary,
            "steps": steps,
            "insights": insights,
            "questions": questions,
            "advice": advice,
            "artifacts": artifacts,
            "evidence": evidence,
        }

    def create_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        snapshot = self.snapshot(
            mode=str(payload.get("mode") or SIMULATION_MODE),
            sop_id=str(payload.get("sop_id") or "") or None,
            strategy_id=_optional_int(payload.get("strategy_id")),
            backtest_id=_optional_int(payload.get("backtest_id")),
            account_id=_optional_int(payload.get("account_id")),
            live_run_id=_optional_int(payload.get("live_run_id")),
        )
        now = utc_now_iso()
        run = self.repo.insert(
            "quant_workflow_runs",
            {
                "mode": snapshot["mode"],
                "sop_id": snapshot["sop"]["id"],
                "title": payload.get("title") or snapshot["sop"]["name"],
                "status": _overall_status(snapshot["steps"]),
                "context": json.dumps(snapshot["context"], ensure_ascii=False),
                "summary": snapshot["summary"],
                "created_at": now,
                "updated_at": now,
            },
        )
        run_id = int(run["id"])
        for index, step in enumerate(snapshot["steps"], start=1):
            self.repo.insert(
                "quant_workflow_steps",
                {
                    "run_id": run_id,
                    "step_order": index,
                    "stage_key": step["stage_key"],
                    "title": step["title"],
                    "status": step["status"],
                    "evidence": step["evidence"],
                    "artifacts": json.dumps(step.get("artifact_refs") or [], ensure_ascii=False),
                    "created_at": now,
                },
            )
        for artifact in snapshot["artifacts"]:
            self.repo.insert(
                "quant_workflow_artifacts",
                {
                    "run_id": run_id,
                    "artifact_type": artifact["artifact_type"],
                    "title": artifact["title"],
                    "ref_type": artifact.get("ref_type") or "",
                    "ref_id": str(artifact.get("ref_id") or ""),
                    "summary": artifact.get("summary") or "",
                    "data": json.dumps(artifact.get("data") or {}, ensure_ascii=False),
                    "created_at": now,
                },
            )
        self.log.info(
            "quant workflow run created | run_id={} mode={} sop_id={}",
            run_id,
            snapshot["mode"],
            snapshot["sop"]["id"],
        )
        return self.detail(run_id)

    def list_runs(self, mode: str | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        where = ""
        params: list[Any] = []
        if mode:
            where = "mode = ?"
            params.append(_normalize_mode(mode))
        result = self.repo.page(
            "quant_workflow_runs",
            page=page,
            page_size=page_size,
            where=where,
            params=params,
            order_by="created_at DESC",
        )
        for item in result["items"]:
            item["run_id"] = item["id"]
            item["context"] = json_loads(item.get("context"), {})
        return result

    def detail(self, run_id: int) -> dict[str, Any]:
        run = self.repo.get("quant_workflow_runs", run_id)
        run["run_id"] = run["id"]
        run["context"] = json_loads(run.get("context"), {})
        run["steps"] = self.repo.list(
            "quant_workflow_steps",
            where="run_id = ?",
            params=(run_id,),
            order_by="step_order ASC",
        )
        for step in run["steps"]:
            step["artifact_refs"] = json_loads(step.get("artifacts"), [])
        run["artifacts"] = self.repo.list(
            "quant_workflow_artifacts",
            where="run_id = ?",
            params=(run_id,),
            order_by="id ASC",
        )
        for artifact in run["artifacts"]:
            artifact["data"] = json_loads(artifact.get("data"), {})
        return run

    def _config(self) -> dict[str, Any]:
        payload = yaml.safe_load(self.sop_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError("量化闭环 SOP 配置必须是 YAML 对象")
        return payload

    def _select_sop(self, mode: str, sop_id: str | None) -> dict[str, Any]:
        selected = str(sop_id or "").strip()
        candidates = self.sops(mode)
        for item in candidates:
            if str(item.get("id") or "") == selected:
                return item
        if not candidates:
            raise ValueError(f"未配置 {mode} 模式的闭环 SOP")
        return candidates[0]

    def _collect_evidence(
        self,
        mode: str,
        strategy_id: int | None,
        backtest_id: int | None,
        account_id: int | None,
        live_run_id: int | None,
    ) -> dict[str, Any]:
        evidence: dict[str, Any] = {
            "strategy": self._strategy(strategy_id),
            "backtest": self._backtest(backtest_id, strategy_id),
            "factor": self._factor_snapshot(),
            "paper": self._paper_snapshot(account_id),
            "live": self._live_snapshot(live_run_id),
        }
        if mode == SIMULATION_MODE and evidence["backtest"].get("task"):
            evidence["strategy"] = evidence["strategy"] or self._strategy(
                _optional_int(evidence["backtest"]["task"].get("strategy_id"))
            )
        return evidence

    def _strategy(self, strategy_id: int | None) -> dict[str, Any]:
        if strategy_id:
            return self.repo.get_optional("strategies", strategy_id) or {}
        return self.repo.db.query_one("SELECT * FROM strategies ORDER BY updated_at DESC LIMIT 1") or {}

    def _backtest(self, backtest_id: int | None, strategy_id: int | None) -> dict[str, Any]:
        task: dict[str, Any] | None = None
        if backtest_id:
            task = self.repo.get_optional("backtest_tasks", backtest_id)
        elif strategy_id:
            task = self.repo.db.query_one(
                "SELECT * FROM backtest_tasks WHERE strategy_id = ? ORDER BY created_at DESC LIMIT 1",
                (strategy_id,),
            )
        else:
            task = self.repo.db.query_one("SELECT * FROM backtest_tasks ORDER BY created_at DESC LIMIT 1")
        if not task:
            return {"task": {}, "metrics": {}, "curve": {}, "trades": []}
        result = self.repo.db.query_one("SELECT * FROM backtest_results WHERE task_id = ?", (task["id"],)) or {}
        attribution: dict[str, Any] = {}
        if result:
            try:
                from src.engine.backtest import BacktestRunner

                attribution = BacktestRunner(repo=self.repo).attribution(int(task["id"]))
            except Exception as exc:
                self.log.warning("backtest attribution snapshot failed | task_id={} error={}", task["id"], exc)
        return {
            "task": task,
            "metrics": json_loads(result.get("metrics"), {}),
            "curve": json_loads(result.get("equity_curve"), {}),
            "trades": json_loads(result.get("trades"), []),
            "attribution": attribution,
        }

    def _factor_snapshot(self) -> dict[str, Any]:
        metrics = self.repo.list("factor_metrics_daily", order_by="metric_date DESC, id DESC", limit=12)
        alerts = self.repo.list("factor_alerts", where="status = 'open'", order_by="triggered_at DESC", limit=8)
        definitions = self.repo.list("factor_definitions", where="enabled = 1", order_by="id ASC", limit=20)
        return {"metrics": metrics, "alerts": alerts, "definitions": definitions}

    def _paper_snapshot(self, account_id: int | None) -> dict[str, Any]:
        account = None
        if account_id:
            account = self.repo.get_optional("paper_accounts", account_id)
        if not account:
            account = self.repo.db.query_one("SELECT * FROM paper_accounts ORDER BY updated_at DESC LIMIT 1")
        if not account:
            return {"account": {}, "positions": [], "orders": [], "trades": [], "nav": []}
        selected_id = int(account["id"])
        return {
            "account": account,
            "positions": self.repo.list(
                "paper_positions",
                where="account_id = ? AND quantity > 0",
                params=(selected_id,),
                order_by="market_value DESC",
            ),
            "orders": self.repo.list(
                "paper_orders",
                where="account_id = ?",
                params=(selected_id,),
                order_by="created_at DESC",
                limit=20,
            ),
            "trades": self.repo.list(
                "paper_trades",
                where="account_id = ?",
                params=(selected_id,),
                order_by="traded_at DESC",
                limit=30,
            ),
            "nav": self.repo.list(
                "paper_nav_history",
                where="account_id = ?",
                params=(selected_id,),
                order_by="nav_date DESC",
                limit=30,
            ),
        }

    def _live_snapshot(self, live_run_id: int | None) -> dict[str, Any]:
        run = None
        if live_run_id:
            run = self.repo.get_optional("live_runs", live_run_id)
        if not run:
            run = self.repo.db.query_one("SELECT * FROM live_runs ORDER BY started_at DESC LIMIT 1")
        if not run:
            config = self.repo.db.query_one("SELECT * FROM live_configs ORDER BY updated_at DESC LIMIT 1") or {}
            return {"config": config, "run": {}, "orders": [], "positions": []}
        config = self.repo.get_optional("live_configs", int(run["config_id"])) or {}
        return {
            "config": config,
            "run": run,
            "orders": self.repo.list(
                "live_orders",
                where="run_id = ?",
                params=(run["id"],),
                order_by="created_at DESC",
                limit=20,
            ),
            "positions": [],
        }

    def _build_steps(
        self,
        sop: dict[str, Any],
        evidence: dict[str, Any],
        insights: list[dict[str, Any]],
        advice: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        steps = []
        for stage in sop.get("stages") or []:
            if not isinstance(stage, dict):
                continue
            key = str(stage.get("key") or "")
            status, evidence_text = self._stage_status(key, evidence, insights, advice)
            steps.append(
                {
                    "stage_key": key,
                    "title": str(stage.get("title") or key),
                    "goal": str(stage.get("goal") or ""),
                    "status": status,
                    "evidence": evidence_text,
                    "artifact_refs": [item["title"] for item in self._stage_artifacts(key, evidence)],
                }
            )
        return steps

    def _stage_status(
        self,
        key: str,
        evidence: dict[str, Any],
        insights: list[dict[str, Any]],
        advice: list[dict[str, Any]],
    ) -> tuple[str, str]:
        if key == "analysis":
            metrics_count = len(evidence["factor"].get("metrics") or [])
            return (
                ("completed", f"已读取因子指标 {metrics_count} 条")
                if metrics_count
                else ("not_started", "暂无因子或市场指标")
            )
        if key == "strategy_build":
            strategy = evidence.get("strategy") or {}
            return (
                ("completed", f"策略：{strategy.get('name')} v{strategy.get('version')}")
                if strategy
                else (
                    "not_started",
                    "暂无策略版本",
                )
            )
        if key == "simulation":
            task = evidence["backtest"].get("task") or {}
            paper = evidence["paper"].get("account") or {}
            if task:
                return "completed", f"回测任务 {task.get('id')} · {task.get('status')}"
            if paper:
                return "in_progress", f"模拟账户 {paper.get('name')} 已存在"
            return "not_started", "暂无回测或模拟账户"
        if key == "trading":
            run = evidence["live"].get("run") or {}
            orders = evidence["live"].get("orders") or []
            if run:
                return "completed", f"运行 {run.get('id')} · 订单 {len(orders)} 笔"
            return "not_started", "暂无实盘运行记录"
        if key == "observation":
            paper = evidence["paper"].get("account") or {}
            live = evidence["live"].get("config") or {}
            if paper or live:
                return "in_progress", "已读取账户或实盘配置快照"
            return "not_started", "暂无可观测账户"
        if key == "attribution":
            return ("completed", f"归因洞察 {len(insights)} 条") if insights else ("not_started", "暂无归因洞察")
        if key == "iteration":
            return ("completed", f"迭代建议 {len(advice)} 条") if advice else ("not_started", "暂无迭代建议")
        return "not_started", "等待执行"

    @staticmethod
    def _stage_artifacts(key: str, evidence: dict[str, Any]) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        if key in {"simulation", "attribution"} and evidence["backtest"].get("task"):
            task = evidence["backtest"]["task"]
            artifacts.append({"title": f"回测任务 {task.get('id')}", "ref_type": "backtest", "ref_id": task.get("id")})
        if key in {"analysis", "attribution"} and evidence["factor"].get("metrics"):
            artifacts.append({"title": "因子监控快照", "ref_type": "factor", "ref_id": "latest"})
        if key in {"observation", "trading"} and evidence["paper"].get("account"):
            account = evidence["paper"]["account"]
            artifacts.append(
                {"title": f"模拟账户 {account.get('id')}", "ref_type": "paper_account", "ref_id": account.get("id")}
            )
        if key in {"observation", "trading"} and evidence["live"].get("run"):
            run = evidence["live"]["run"]
            artifacts.append({"title": f"实盘运行 {run.get('id')}", "ref_type": "live_run", "ref_id": run.get("id")})
        return artifacts

    def _build_insights(self, mode: str, evidence: dict[str, Any]) -> list[dict[str, Any]]:
        insights: list[dict[str, Any]] = []
        metrics = evidence["backtest"].get("metrics") or {}
        if metrics:
            total_return = _float(metrics.get("total_return"))
            max_drawdown = _float(metrics.get("max_drawdown"))
            sharpe = _float(metrics.get("sharpe"))
            severity = "warning" if max_drawdown <= DRAWDOWN_WARNING or sharpe < LOW_SHARPE_WARNING else "info"
            insights.append(
                _insight(
                    "performance",
                    "回测绩效归因",
                    f"收益 {_percent(total_return)}，最大回撤 {_percent(max_drawdown)}，夏普 {sharpe:.2f}",
                    "收益、回撤和风险收益比共同决定是否进入下一轮验证。",
                    severity,
                )
            )
            win_rate = _float(metrics.get("win_rate"))
            trade_count = int(_float(metrics.get("trade_count")))
            trade_severity = "warning" if win_rate < LOW_WIN_RATE_WARNING else "info"
            insights.append(
                _insight(
                    "trade",
                    "交易胜率归因",
                    f"交易次数 {trade_count}，胜率 {_percent(win_rate)}，盈亏比 {_float(metrics.get('profit_loss_ratio')):.2f}",
                    "交易次数过少时应优先扩大样本，胜率偏低时复核入场和离场条件。",
                    trade_severity,
                )
            )
            by_symbol = (evidence["backtest"].get("attribution") or {}).get("by_symbol") or []
            if by_symbol:
                best_symbol = max(by_symbol, key=lambda item: _float(item.get("pnl")))
                insights.append(
                    _insight(
                        "symbol",
                        "标的贡献归因",
                        f"{best_symbol.get('name')} 贡献 {_float(best_symbol.get('pnl')):+.2f}",
                        "标的贡献用于判断策略收益是否过度依赖单一股票池样本。",
                        "info",
                    )
                )
        factor_metrics = evidence["factor"].get("metrics") or []
        if factor_metrics:
            rank_ics = [_float(item.get("rank_ic")) for item in factor_metrics if item.get("rank_ic") is not None]
            avg_rank_ic = sum(rank_ics) / len(rank_ics) if rank_ics else 0.0
            severity = "warning" if abs(avg_rank_ic) < LOW_FACTOR_IC_WARNING else "info"
            insights.append(
                _insight(
                    "factor",
                    "因子有效性归因",
                    f"最近 {len(factor_metrics)} 条因子指标，平均 RankIC {avg_rank_ic:.3f}",
                    "RankIC 偏弱时，策略信号需要增加市场环境过滤或改用其他因子组合。",
                    severity,
                )
            )
        alerts = evidence["factor"].get("alerts") or []
        if alerts:
            insights.append(
                _insight(
                    "risk",
                    "因子告警归因",
                    f"存在 {len(alerts)} 条打开状态因子告警",
                    "告警代表样本、覆盖率、单调性或 RankIC 存在需要复核的口径。",
                    "warning",
                )
            )
        paper = evidence["paper"]
        account = paper.get("account") or {}
        if account:
            positions = paper.get("positions") or []
            orders = paper.get("orders") or []
            pending_orders = [item for item in orders if item.get("status") not in {"已成交", "已撤销"}]
            total_value = _float(account.get("current_cash")) + sum(
                _float(item.get("market_value")) for item in positions
            )
            max_position = max((_float(item.get("market_value")) for item in positions), default=0.0)
            concentration = max_position / total_value if total_value > 0 else 0.0
            severity = "warning" if pending_orders or concentration > HIGH_CONCENTRATION_RATIO else "info"
            insights.append(
                _insight(
                    "account",
                    "账户观测归因",
                    f"持仓 {len(positions)} 个，未完成委托 {len(pending_orders)} 笔，单一持仓占比 {_percent(concentration)}",
                    "集中度和未完成委托会影响下一轮回测假设与模拟交易复盘。",
                    severity,
                )
            )
        live = evidence["live"]
        run = live.get("run") or {}
        if mode == LIVE_MODE and (run or live.get("config")):
            orders = live.get("orders") or []
            insights.append(
                _insight(
                    "live",
                    "真实交易观测",
                    f"运行状态 {run.get('status', '未运行')}，订单 {len(orders)} 笔",
                    "当前实盘通道以配置和运行记录为主；真实券商未接入时不得视为真实成交闭环。",
                    "warning" if not run else "info",
                )
            )
        return insights

    @staticmethod
    def _build_advice(
        mode: str,
        evidence: dict[str, Any],
        insights: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        advice: list[dict[str, Any]] = []
        metrics = evidence["backtest"].get("metrics") or {}
        if not metrics and mode == SIMULATION_MODE:
            advice.append(
                _advice(
                    "P1",
                    "补充回测验证",
                    "尚未找到可用回测结果，闭环缺少模拟验证证据。",
                    "先选择策略和股票池运行一次 simple 回测，再进入归因。",
                    "不要把未回测策略带入实盘建议。",
                )
            )
        if metrics and _float(metrics.get("max_drawdown")) <= DRAWDOWN_WARNING:
            advice.append(
                _advice(
                    "P1",
                    "降低回撤暴露",
                    f"最大回撤为 {_percent(_float(metrics.get('max_drawdown')))}，已触发回撤复核阈值。",
                    "增加市场环境过滤器，或降低单次仓位后重新回测。",
                    "同一参数不得只凭单次回测直接进入实盘。",
                )
            )
        if metrics and _float(metrics.get("sharpe")) < LOW_SHARPE_WARNING:
            advice.append(
                _advice(
                    "P2",
                    "复核收益稳定性",
                    f"夏普比率 {_float(metrics.get('sharpe')):.2f} 偏低。",
                    "拆分上涨、震荡、下跌市场分别评估策略表现。",
                    "不要只看总收益率，必须同时观察回撤和交易明细。",
                )
            )
        factor_alerts = evidence["factor"].get("alerts") or []
        if factor_alerts:
            advice.append(
                _advice(
                    "P2",
                    "处理因子告警",
                    f"仍有 {len(factor_alerts)} 条因子告警未关闭。",
                    "先复核覆盖率、RankIC 和分位单调性，再决定是否保留相关信号。",
                    "因子有效性不足时，策略优化应优先回到研究阶段。",
                )
            )
        paper = evidence["paper"]
        pending_orders = [item for item in paper.get("orders") or [] if item.get("status") not in {"已成交", "已撤销"}]
        if len(pending_orders) > HIGH_PENDING_ORDER_COUNT:
            advice.append(
                _advice(
                    "P1",
                    "先处理未完成委托",
                    f"模拟账户存在 {len(pending_orders)} 笔未完成委托。",
                    "完成撤单、成交确认或重新同步后再做盘后归因。",
                    "未完成委托会污染账户净值和交易归因。",
                )
            )
        if mode == LIVE_MODE:
            live_run = evidence["live"].get("run") or {}
            if not live_run:
                advice.append(
                    _advice(
                        "P1",
                        "先确认实盘运行状态",
                        "未找到实盘运行记录，当前只能做配置级观测。",
                        "进入实盘页启动模拟通道或接入真实券商后再做交易归因。",
                        "真实资金交易必须保留人工确认和风控审计。",
                    )
                )
        if not advice:
            advice.append(
                _advice(
                    "P3",
                    "进入下一轮验证",
                    "当前闭环没有触发高优先级阻断项。",
                    "固定参数快照，扩大样本区间或切换股票池做交叉验证。",
                    "仍需人工确认数据口径和交易成本假设。",
                )
            )
        return advice

    @staticmethod
    def _build_questions(
        mode: str,
        evidence: dict[str, Any],
        insights: list[dict[str, Any]],
        advice: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        metrics = evidence["backtest"].get("metrics") or {}
        factor_alerts = evidence["factor"].get("alerts") or []
        paper_positions = evidence["paper"].get("positions") or []
        rows = [
            {
                "question": "这一轮闭环最关键的问题是什么？",
                "answer": advice[0]["action"] if advice else "继续交叉验证。",
                "evidence": advice[0]["rationale"] if advice else "暂无阻断项。",
            },
            {
                "question": "回测是否足以进入下一轮？",
                "answer": "可以进入扩样验证" if metrics else "还不能，需要先生成回测任务。",
                "evidence": f"绩效字段 {len(metrics)} 个，归因洞察 {len(insights)} 条。",
            },
            {
                "question": "因子侧有没有明显风险？",
                "answer": "有告警需要处理" if factor_alerts else "未发现打开状态因子告警。",
                "evidence": f"打开告警 {len(factor_alerts)} 条。",
            },
        ]
        if mode == LIVE_MODE:
            rows.append(
                {
                    "question": "真实交易闭环当前能做什么？",
                    "answer": "优先做运行状态、订单、持仓和风险观测。",
                    "evidence": "真实券商未接入时只给配置和模拟通道建议。",
                }
            )
        else:
            rows.append(
                {
                    "question": "模拟账户是否暴露集中风险？",
                    "answer": f"当前持仓 {len(paper_positions)} 个。",
                    "evidence": "需要结合持仓市值和账户净值继续判断集中度。",
                }
            )
        return rows

    @staticmethod
    def _build_artifacts(
        mode: str,
        evidence: dict[str, Any],
        insights: list[dict[str, Any]],
        advice: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        task = evidence["backtest"].get("task") or {}
        if task:
            artifacts.append(
                {
                    "artifact_type": "backtest",
                    "title": f"回测任务 {task.get('id')}",
                    "ref_type": "backtest",
                    "ref_id": task.get("id"),
                    "summary": f"{task.get('start_date')} 至 {task.get('end_date')} · {task.get('status')}",
                    "data": {"metrics": evidence["backtest"].get("metrics") or {}},
                }
            )
        if evidence["factor"].get("metrics"):
            artifacts.append(
                {
                    "artifact_type": "factor_monitor",
                    "title": "因子监控快照",
                    "ref_type": "factor",
                    "ref_id": "latest",
                    "summary": f"指标 {len(evidence['factor'].get('metrics') or [])} 条，告警 {len(evidence['factor'].get('alerts') or [])} 条",
                    "data": {"alerts": evidence["factor"].get("alerts") or []},
                }
            )
        account = evidence["paper"].get("account") or {}
        if account:
            artifacts.append(
                {
                    "artifact_type": "paper_account",
                    "title": f"模拟账户 {account.get('name')}",
                    "ref_type": "paper_account",
                    "ref_id": account.get("id"),
                    "summary": f"持仓 {len(evidence['paper'].get('positions') or [])} 个，委托 {len(evidence['paper'].get('orders') or [])} 笔",
                    "data": {"account_id": account.get("id")},
                }
            )
        live_run = evidence["live"].get("run") or {}
        if mode == LIVE_MODE and live_run:
            artifacts.append(
                {
                    "artifact_type": "live_run",
                    "title": f"实盘运行 {live_run.get('id')}",
                    "ref_type": "live_run",
                    "ref_id": live_run.get("id"),
                    "summary": f"状态 {live_run.get('status')}，订单 {len(evidence['live'].get('orders') or [])} 笔",
                    "data": {"run_id": live_run.get("id")},
                }
            )
        artifacts.append(
            {
                "artifact_type": "diagnosis",
                "title": "归因与迭代建议",
                "ref_type": "quant_workflow",
                "ref_id": mode,
                "summary": f"洞察 {len(insights)} 条，建议 {len(advice)} 条",
                "data": {"insights": insights, "advice": advice},
            }
        )
        return artifacts

    @staticmethod
    def _summary(
        mode: str,
        evidence: dict[str, Any],
        insights: list[dict[str, Any]],
        advice: list[dict[str, Any]],
    ) -> str:
        mode_label = "模拟研究闭环" if mode == SIMULATION_MODE else "真实交易观测闭环"
        task = evidence["backtest"].get("task") or {}
        strategy = evidence.get("strategy") or {}
        main_advice = advice[0]["action"] if advice else "继续验证"
        parts = [
            f"{mode_label}快照已生成。",
            f"策略：{strategy.get('name', '未选择')}",
            f"回测：{task.get('id', '暂无')}",
            f"洞察：{len(insights)} 条",
            f"首要建议：{main_advice}",
        ]
        return " · ".join(parts)


def _normalize_mode(mode: str | None) -> str:
    normalized = str(mode or SIMULATION_MODE).strip().lower()
    if normalized not in WORKFLOW_MODES:
        return SIMULATION_MODE
    return normalized


def _public_sop(sop: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": sop.get("id"),
        "mode": sop.get("mode"),
        "name": sop.get("name"),
        "description": sop.get("description"),
        "stages": [
            {
                "key": item.get("key"),
                "title": item.get("title"),
                "goal": item.get("goal"),
            }
            for item in sop.get("stages") or []
            if isinstance(item, dict)
        ],
    }


def _overall_status(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return "not_started"
    if any(step["status"] == "not_started" for step in steps):
        return "in_progress"
    if any(step["status"] == "in_progress" for step in steps):
        return "in_progress"
    return "completed"


def _optional_int(value: Any) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _percent(value: float) -> str:
    return f"{value * 100:+.2f}%"


def _insight(
    insight_type: str,
    title: str,
    conclusion: str,
    evidence: str,
    severity: str,
) -> dict[str, Any]:
    confidence = "高" if severity == "info" else "中"
    return {
        "insight_type": insight_type,
        "title": title,
        "conclusion": conclusion,
        "evidence": evidence,
        "severity": severity,
        "confidence": confidence,
    }


def _advice(
    priority: str,
    action: str,
    rationale: str,
    next_step: str,
    guardrail: str,
) -> dict[str, str]:
    return {
        "priority": priority,
        "action": action,
        "rationale": rationale,
        "next_step": next_step,
        "guardrail": guardrail,
    }
