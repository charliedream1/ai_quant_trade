"""Reusable parameter scheme selector and resolved parameter viewer."""

from __future__ import annotations

from dataclasses import dataclass

import gradio as gr

from ..common.callbacks import safe
from ..handlers import DomainHandler


@dataclass
class ParameterControls:
    overrides: gr.Code
    profile: gr.Dropdown
    resolved: gr.Code
    status: gr.Markdown


def render_parameter_controls(service: DomainHandler, strategy_id: gr.Number) -> ParameterControls:
    with gr.Accordion("参数方案与本次覆盖", open=True, elem_classes=["strategy-parameter-controls"]):
        gr.Markdown(
            "本次覆盖 → YAML 参数方案 → 已保存默认值 → 源码 / 模型默认值。"
            "对象按字段合并，列表整体替换；空对象保留下层参数。"
            "预览保留上次点击结果，修改后请重新预览；回测完成后显示实际留档值。",
            elem_classes=["compact-note"],
        )
        with gr.Row():
            profile = gr.Dropdown(choices=[("继承策略默认", "")], value="", label="参数方案", scale=3)
            refresh = gr.Button("刷新方案", elem_classes=["parameter-secondary"])
        overrides = gr.Code(value="{}", language="json", label="本次参数覆盖（JSON）", lines=5)
        preview = gr.Button("预览生效参数", variant="primary")
        status = gr.Markdown("填写策略 ID 后，可预览全部声明参数。", elem_classes=["compact-note"])
        with gr.Accordion("最终生效参数", open=False):
            resolved = gr.Code(value="{}", language="json", label="生效参数（只读）", interactive=False, lines=8)
        outputs = [profile, overrides, resolved, status]
        refresh.click(safe(service.parameter_profiles), inputs=strategy_id, outputs=outputs)
        strategy_id.change(safe(service.parameter_profiles), inputs=strategy_id, outputs=outputs)
        preview.click(
            safe(service.preview_strategy_parameters),
            inputs=[strategy_id, overrides, profile],
            outputs=[resolved, status],
        )
    return ParameterControls(overrides, profile, resolved, status)
