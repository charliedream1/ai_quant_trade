"""UI adapters for durable background one-click backtests."""

import gradio as gr
from src.core.repository import Repository
from src.engine.backtest import BacktestRunner
from src.engine.backtest.capabilities import strategy_capability
from src.engine.backtest.config import backtest_config
from src.engine.backtest.jobs import cancel, submit
from src.strategy.parameters import StrategyParameters

from ..common.navigation import workspace_link
from .execution_costs import cost_markdown
from .foundation import parse_csv, parse_json, require_id, require_text, to_frame, ui_error_message


class QuickBacktestMixin:
    def quick_history(self):
        return to_frame(
            BacktestRunner().list(page_size=20),
            [
                "task_id",
                "strategy_id",
                "engine",
                "status",
                "progress",
                "start_date",
                "end_date",
                "current_date",
                "error_msg",
            ],
        )

    def quick_capability(self, strategy_id):
        if not strategy_id:
            return "点击策略列表中的一行，或输入策略 ID。", "auto"
        value = require_id(strategy_id, "策略 ID")
        resolution = StrategyParameters().resolve(value, None, None)
        cap = strategy_capability(value, resolution["resolved_params"], Repository())
        link = (
            f"[打开此冻结图形方案](/app/?module=strategy&view=workshop&pipeline_version={cap['version']})"
            if cap["pipeline_id"]
            else ""
        )
        return f"实际引擎 **{cap['engine']}** · 入口 {cap['entry']} · 冻结版本 {cap['version']} · {link}", "auto"

    def quick_start(
        self, strategy_id, symbols, start_date, end_date, capital, params, engine, profile, execution_costs=None
    ):
        try:
            cfg = backtest_config()["quick"]
            payload = {
                **cfg,
                "strategy_id": require_id(strategy_id, "策略 ID"),
                "symbols": parse_csv(require_text(symbols, "回测标的")),
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": float(capital),
                "params": parse_json(params or "{}", "参数"),
                "engine": engine or "auto",
                "parameter_profile": profile or None,
                "execution_costs": execution_costs,
            }
            task = submit(payload)
            return (
                f"任务 **{task['task_id']}** · {task['status']} · {task['engine']}，可切页后返回查看。",
                task["task_id"],
                gr.update(active=True),
            )
        except Exception as exc:
            return f"未提交：{ui_error_message(exc)}", None, gr.update(active=False)

    def quick_poll(self, task_id):
        if not task_id:
            return gr.skip(), gr.skip(), gr.update(active=False)
        task = BacktestRunner().detail(int(task_id))
        active = task["status"] in {"queued", "running"}
        evidence = (task.get("parameter_snapshot") or {}).get("data") or {}
        text = f"任务 **{task_id}** · **{task['status']}** · {task['engine']} · 进度 {task['progress']}%"
        text += "\n\n" + workspace_link(
            "打开统一回测结果", "simulation", "backtest", task_id=task_id, strategy_id=task["strategy_id"]
        )
        if task.get("error_msg"):
            text += f"\n\n{task['error_msg']}"
        if evidence.get("first_date"):
            text += f"\n\n请求 {task['start_date']}～{task['end_date']}；实际 {evidence['first_date']}～{evidence['last_date']}，{evidence['equity_points']}个交易日。"
        if task["status"] == "finished":
            text += cost_markdown(BacktestRunner().performance(int(task_id)))
        return text, self.quick_history(), gr.update(active=active)

    def quick_cancel(self, task_id):
        return cancel(require_id(task_id, "回测任务 ID"))
