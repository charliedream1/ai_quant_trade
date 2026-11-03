"""Compact research-team controls inside the existing expert-team page."""

from __future__ import annotations

import gradio as gr

from ..common.components import table
from ..common.provider_controls import provider_controls
from ..handlers import DomainHandler


def render_research_team(service: DomainHandler) -> None:
    with gr.Accordion("多Agent回测复核", open=True):
        with gr.Row():
            task = gr.Number(label="已完成的回测 ID", precision=0)
            model = gr.Dropdown(choices=service.research_team_model_choices(), value=0, label="使用模型")
            workflow = gr.Dropdown(
                choices=[("普通模型回测复核", "backtest_review"), ("ETF策略投研复核", "etf_review")],
                value="backtest_review",
                label="复核工作流",
            )
        objective = gr.Textbox(label="研究目标", lines=2)
        backend, model_name = provider_controls("research-team")
        reasoning = gr.Dropdown(["", "low", "medium", "high", "xhigh"], value="", label="思考强度")
        with gr.Accordion("按角色选择后端（可选）", open=False):
            role_models = gr.Code(value="{}", language="yaml", label="analyst / risk / reviewer / chair", lines=5)
        start = gr.Button("开始多Agent复核", variant="primary")
        status = gr.Markdown()
        roles = table("角色执行与证据", 280)
        report = gr.Markdown()
        start.click(
            service.research_team_review,
            inputs=[task, objective, model, workflow, backend, model_name, reasoning, role_models],
            outputs=[status, roles, report],
        )
