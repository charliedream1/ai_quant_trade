"""Shared, inexpensive parameter previews for strategy and simulation pages."""

from __future__ import annotations

from typing import Any

import gradio as gr
from src.engine.backtest import BacktestRunner
from src.strategy.parameters import StrategyParameters

from .foundation import compact_json, parse_json, require_id


class ParameterServiceMixin:
    def parameter_profiles(self, strategy_id: Any) -> tuple[dict[str, Any], str, str, str]:
        choices = [("继承策略默认", "")]
        if strategy_id:
            options = StrategyParameters().options(require_id(strategy_id, "策略 ID"))
            choices.extend((item["label"], item["id"]) for item in options)
        return gr.update(choices=choices, value=""), "{}", "{}", "方案已刷新，本次覆盖已重置；请预览生效参数。"

    def preview_strategy_parameters(self, strategy_id: Any, params: str, profile: str = "") -> tuple[str, str]:
        if not strategy_id:
            return "{}", "请先填写策略 ID，再选择参数方案。"
        resolution = StrategyParameters().resolve(
            require_id(strategy_id, "策略 ID"), parse_json(params, "本次参数覆盖"), profile
        )
        selected = resolution["profile"]
        label = selected.get("label") or "继承策略默认"
        note = selected.get("description") or "按模型配置、源码定义和已保存默认值合并。"
        return compact_json(resolution["resolved_params"]), f"预览方案：{label}。{note} 修改参数后请重新预览。"

    def backtest_resolved_parameters(self, task_id: Any) -> tuple[str, str]:
        task = BacktestRunner().detail(require_id(task_id, "回测任务 ID"))
        snapshot = task.get("parameter_snapshot")
        if not snapshot:
            params = {key: value for key, value in task.get("params", {}).items() if key != "_backtest"}
            return compact_json(params), "历史任务只有原始参数记录，未保存完整参数解析证据。"
        label = snapshot["profile"].get("label") or "继承策略默认"
        return compact_json(snapshot["resolved_params"]), f"任务 {task_id} 实际生效参数已留档，方案：{label}。"
