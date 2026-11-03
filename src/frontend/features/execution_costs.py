"""Shared execution controls for regular, quick and graphical backtests."""

import json
from dataclasses import dataclass

import gradio as gr
from src.engine.execution.config import cost_config

PERCENT = 100


@dataclass
class ExecutionControls:
    inputs: list

    def parse(self, values):
        return build_cost_request(*values)


def build_cost_request(profile, mode, slip_mode, regulatory, extra, *values):
    request = json.loads(extra or "{}")
    if not isinstance(request, dict):
        raise ValueError("高级执行覆盖必须为JSON对象")
    request.update(
        {
            item["key"]: float(value) / PERCENT if item.get("percent") else float(value)
            for item, value in zip(cost_config()["ui"]["controls"], values, strict=True)
            if value not in (None, "")
        }
    )
    if slip_mode:
        request["slippage_mode"] = slip_mode
    if regulatory != "inherit":
        request["commission_includes_regulatory"] = regulatory == "included"
    if not request and profile == "inherit" and mode == "research":
        return None
    return {**request, "profile": profile, "validation_mode": mode}


def render_execution_controls(service, strategy_id=None, definition=None):
    cfg = cost_config()
    sid = strategy_id if strategy_id is not None else gr.State(None)
    text = definition if definition is not None else gr.State(None)
    with gr.Accordion(cfg["ui"]["title"], open=False):
        gr.Markdown(cfg["ui"]["rate_unit"] + "。覆盖项留空继承方案；策略参数与执行费用分别保存。")
        with gr.Row():
            profile = gr.Dropdown(
                [(item["label"], key) for key, item in cfg["profiles"].items()],
                value="inherit",
                label="费用方案",
                interactive=True,
            )
            mode = gr.Dropdown(
                [("研究（列出能力缺口）", "research"), ("严格（缺口阻断）", "strict")],
                value="research",
                label="执行校验模式",
                interactive=True,
            )
        inputs = []
        for offset in range(0, len(cfg["ui"]["controls"]), 3):
            with gr.Row():
                for item in cfg["ui"]["controls"][offset : offset + 3]:
                    inputs.append(
                        gr.Textbox(value="", label=item["label"], placeholder="留空继承方案", interactive=True)
                    )
        with gr.Row():
            slip_mode = gr.Dropdown(
                [("比例滑点", "ratio"), ("最小价位数", "ticks"), ("无滑点", "none")],
                value=None,
                label="滑点模式（留空继承）",
                interactive=True,
            )
            regulatory = gr.Dropdown(
                [("继承", "inherit"), ("佣金已含规费", "included"), ("佣金不含规费", "excluded")],
                value="inherit",
                label="规费包含关系",
                interactive=True,
            )
        with gr.Accordion("高级执行覆盖", open=False):
            extra = gr.Code(value="{}", language="json", label="执行参数JSON（非策略参数）", interactive=True)
        preview = gr.Button("预览实际执行配置")
        status = gr.Markdown(cfg["ui"]["gaps"])
        resolved = gr.Code(language="json", label="本次执行配置预览")
    fields = [profile, mode, slip_mode, regulatory, extra, *inputs]

    def _preview(*values):
        try:
            raw = build_cost_request(*values[:-2])
            return service.execution_cost_preview(raw, values[-2], values[-1])
        except Exception as exc:
            return "{}", f"执行配置无效：{exc}"

    preview.click(_preview, inputs=[*fields, sid, text], outputs=[resolved, status], queue=False)
    return ExecutionControls(fields)
