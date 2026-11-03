"""A focused section of the existing Gradio AI workspace."""

from __future__ import annotations

import gradio as gr

from ..common.navigation import workspace_link
from .ai_workflow_panels import (
    render_capabilities,
    render_experts,
    render_jobs,
    render_overview,
    render_task,
    render_team,
)


def render_workflow(service, defaults, on_load=None):
    with gr.Tab("工作流中心"):
        gr.HTML(workspace_link("Alpha挖掘、主题精炼与体制实验", "strategy", "alpha"))
        gr.HTML(workspace_link("中文多空与双团队竞赛：在图形工坊方案库选择Agent方案", "strategy", "workshop"))
        gr.HTML(service.ai_workbench_header(), elem_id="ai-command-center")
        with gr.Row(elem_classes=["ai-workbench-frame"]):
            with gr.Column(scale=1, min_width=180):
                gr.HTML(service.ai_workbench_nav(), elem_id="ai-workbench-nav")
            with gr.Column(scale=6, min_width=720, elem_classes=["ai-workbench-main"]):
                with gr.Tabs(elem_classes=["ai-workbench-stage-tabs"]):
                    render_overview(service, defaults, None, on_load)
                    widgets = render_task(service, defaults, None, on_load)
                    render_experts(service, defaults, widgets, on_load)
                    render_team(service, defaults, widgets, on_load)
                    render_jobs(service, defaults, widgets, on_load)
                    render_capabilities(service, defaults, widgets, on_load)
                    with gr.Tab("闭环流程"):
                        gr.Markdown("统一在运行归因中核对回测、模拟与实盘证据，保存分析和查看历史。")
                        gr.HTML(workspace_link("打开运行归因与闭环分析", "simulation", "attribution"))
                    with gr.Tab("知识问答"):
                        gr.Markdown("资料范围、会话历史和引用统一在知识与资料中维护。")
                        gr.HTML(workspace_link("打开知识库AI问答", "knowledge", "qa"))
                    with gr.Tab("CLI 助手"):
                        gr.Markdown("实时对话在主界面选择CLI后台；策略生成、重试和导入统一在策略管理中操作。")
                        gr.HTML(
                            workspace_link("打开CLI实时对话", "ai", "main")
                            + " · "
                            + workspace_link("生成与导入策略产物", "strategy", "management", tab="CLI 工作台")
                        )
