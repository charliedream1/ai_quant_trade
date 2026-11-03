"""A focused section of the existing Gradio AI workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import gradio as gr

from ..common.callbacks import safe as _safe
from ..common.components import chatbot as _chatbot
from ..common.components import table as _table
from ..constants import DEFAULT_JOB_PARAMS, JOB_TYPE_OPTIONS
from ..service.foundation import (
    ACCOUNT_MODE_CHOICES,
    AI_EXPERT_CHOICES,
    AI_EXPERT_GROUP_CHOICES,
    AI_JOB_TEMPLATE_CHOICES,
    AI_TASK_TYPE_CHOICES,
    AI_TEAM_CHOICES,
)
from .research_team import render_research_team


@dataclass
class WorkflowDefaults:
    default_ai_task_type: str
    default_ai_expert: str
    default_ai_team: str
    default_ai_job_template: str


@dataclass
class TaskWidgets:
    ai_task_account_mode: Any
    ai_task_brief: Any
    ai_task_context: Any
    ai_task_expert: Any
    ai_task_input: Any
    ai_task_type: Any


def render_overview(service, defaults, widgets=None, on_load=None):
    with gr.Tab("工作台总览") as ai_overview_tab:
        with gr.Column(elem_classes=["ai-workbench-panel"]):
            with gr.Row():
                ai_overview_account_mode = gr.Radio(ACCOUNT_MODE_CHOICES, value="paper", label="账户视角")
                ai_overview_refresh = gr.Button("刷新总览", variant="primary", elem_classes=["page-refresh-btn"])
            ai_overview_board = gr.HTML(elem_id="ai-workbench-overview")
        for ai_overview_event in (ai_overview_refresh.click, ai_overview_tab.select, ai_overview_account_mode.change):
            ai_overview_event(
                _safe(service.ai_workbench_overview),
                inputs=ai_overview_account_mode,
                outputs=ai_overview_board,
                queue=False,
            )


def render_task(service, defaults, widgets=None, on_load=None):
    with gr.Tab("AI任务对话"):
        with gr.Row(elem_classes=["ai-workbench-shell"]):
            with gr.Column(scale=1, min_width=260, elem_classes=["ai-workbench-left"]):
                ai_task_type = gr.Dropdown(AI_TASK_TYPE_CHOICES, value=defaults.default_ai_task_type, label="任务类型")
                ai_task_account_mode = gr.Radio(ACCOUNT_MODE_CHOICES, value="paper", label="账户视角")
                ai_task_expert = gr.Dropdown(AI_EXPERT_CHOICES, value=defaults.default_ai_expert, label="专家")
                gr.HTML(
                    "<div class='compact-note'><p>进入专家助手并点击刷新后加载专家市场卡片。</p></div>",
                    elem_id="ai-task-expert-scout",
                )
            with gr.Column(scale=3, min_width=520, elem_classes=["ai-workbench-chat"]):
                ai_task_brief = gr.Markdown(
                    service.ai_workbench_brief(defaults.default_ai_task_type, "paper", defaults.default_ai_expert),
                    elem_classes=["status-strip", "ai-workbench-brief"],
                )
                ai_task_history = _chatbot("任务对话", 560, "ai-workbench-chat-history")
                ai_task_status = gr.Markdown("等待任务输入", elem_id="ai-workbench-chat-status")
                with gr.Column(elem_classes=["ai-composer"]):
                    ai_task_input = gr.Textbox(
                        label="任务内容",
                        placeholder="描述你要完成的投研、策略、风控或任务编排目标",
                        lines=4,
                        max_lines=8,
                    )
                    with gr.Row():
                        ai_task_clear = gr.Button("清空对话")
                        ai_task_send = gr.Button("发送任务", variant="primary")
            with gr.Column(scale=1, min_width=280, elem_classes=["ai-workbench-context-col"]):
                ai_task_context = gr.HTML(
                    service.ai_workbench_context(defaults.default_ai_task_type, "paper", defaults.default_ai_expert),
                    elem_id="ai-workbench-context-panel",
                )
        for ai_state_event in (ai_task_type.change, ai_task_account_mode.change, ai_task_expert.change):
            ai_state_event(
                _safe(service.ai_workbench_state),
                inputs=[ai_task_type, ai_task_account_mode, ai_task_expert],
                outputs=[ai_task_brief, ai_task_context],
                queue=False,
            )
        for trigger in (ai_task_input.submit, ai_task_send.click):
            trigger(
                _safe(service.ai_workbench_chat),
                inputs=[ai_task_type, ai_task_account_mode, ai_task_expert, ai_task_input, ai_task_history],
                outputs=[ai_task_history, ai_task_input, ai_task_status],
            )
        ai_task_clear.click(
            lambda: ([], "", "等待任务输入"), outputs=[ai_task_history, ai_task_input, ai_task_status], queue=False
        )
    return TaskWidgets(
        ai_task_account_mode=ai_task_account_mode,
        ai_task_brief=ai_task_brief,
        ai_task_context=ai_task_context,
        ai_task_expert=ai_task_expert,
        ai_task_input=ai_task_input,
        ai_task_type=ai_task_type,
    )


def render_experts(service, defaults, widgets=None, on_load=None):
    with gr.Tab("专家助手"):
        with gr.Column(elem_classes=["ai-workbench-panel"]):
            with gr.Row():
                ai_expert_group = gr.Radio(AI_EXPERT_GROUP_CHOICES, value="all", label="专家分组")
                ai_expert_selected = gr.Dropdown(AI_EXPERT_CHOICES, value=defaults.default_ai_expert, label="选中专家")
                ai_expert_refresh = gr.Button("刷新专家", variant="primary", elem_classes=["page-refresh-btn"])
                ai_expert_open = gr.Button("查看详情")
                ai_expert_use = gr.Button("带入任务对话", variant="primary")
            with gr.Row():
                with gr.Column(scale=3, min_width=520):
                    ai_expert_market = gr.HTML(
                        "<div class='compact-note'><p>点击“刷新专家”后加载专家市场卡片。</p></div>",
                        elem_id="ai-expert-market",
                    )
                with gr.Column(scale=1, min_width=300):
                    ai_expert_detail = gr.Markdown(label="专家详情", elem_classes=["compact-note"])
            with gr.Accordion("专家明细数据", open=False):
                ai_expert_table = _table("专家库", 360)
        ai_expert_group.change(
            _safe(service.ai_expert_catalog),
            inputs=ai_expert_group,
            outputs=[ai_expert_market, ai_expert_table],
            queue=False,
        )
        ai_expert_refresh.click(
            _safe(service.ai_expert_catalog),
            inputs=ai_expert_group,
            outputs=[ai_expert_market, ai_expert_table],
            queue=False,
        )
        ai_expert_open.click(
            _safe(service.ai_expert_detail), inputs=ai_expert_selected, outputs=ai_expert_detail, queue=False
        )
        ai_expert_selected.change(
            _safe(service.ai_expert_detail), inputs=ai_expert_selected, outputs=ai_expert_detail, queue=False
        )
        ai_expert_use.click(
            _safe(service.ai_expert_to_task_state),
            inputs=[ai_expert_selected, widgets.ai_task_account_mode],
            outputs=[
                widgets.ai_task_type,
                widgets.ai_task_expert,
                widgets.ai_task_input,
                widgets.ai_task_brief,
                widgets.ai_task_context,
            ],
            queue=False,
        )


def render_team(service, defaults, widgets=None, on_load=None):
    with gr.Tab("专家团"):
        render_research_team(service)
        with gr.Column(elem_classes=["ai-workbench-panel"]):
            with gr.Row():
                ai_team_group = gr.Radio(AI_EXPERT_GROUP_CHOICES, value="all", label="专家团分组")
                ai_team_selected = gr.Dropdown(AI_TEAM_CHOICES, value=defaults.default_ai_team, label="选中专家团")
                ai_team_refresh = gr.Button("刷新专家团", variant="primary", elem_classes=["page-refresh-btn"])
                ai_team_open = gr.Button("查看分工")
                ai_team_use = gr.Button("带入任务对话", variant="primary")
            with gr.Row():
                with gr.Column(scale=3, min_width=560):
                    ai_team_market = gr.HTML(service.ai_team_cards("all"), elem_id="ai-team-market")
                with gr.Column(scale=1, min_width=320):
                    ai_team_detail = gr.Markdown(label="专家团详情", elem_classes=["compact-note"])
            with gr.Accordion("专家团明细数据", open=False):
                ai_team_table = _table("专家团", 360)
        ai_team_group.change(
            _safe(service.ai_team_catalog), inputs=ai_team_group, outputs=[ai_team_market, ai_team_table], queue=False
        )
        ai_team_refresh.click(
            _safe(service.ai_team_catalog), inputs=ai_team_group, outputs=[ai_team_market, ai_team_table], queue=False
        )
        ai_team_open.click(_safe(service.ai_team_detail), inputs=ai_team_selected, outputs=ai_team_detail, queue=False)
        ai_team_selected.change(
            _safe(service.ai_team_detail), inputs=ai_team_selected, outputs=ai_team_detail, queue=False
        )
        ai_team_use.click(
            _safe(service.ai_team_to_task_state),
            inputs=[ai_team_selected, widgets.ai_task_account_mode],
            outputs=[
                widgets.ai_task_type,
                widgets.ai_task_expert,
                widgets.ai_task_input,
                widgets.ai_task_brief,
                widgets.ai_task_context,
            ],
            queue=False,
        )


def render_jobs(service, defaults, widgets=None, on_load=None):
    with gr.Tab("定时任务助手"):
        with gr.Column(elem_classes=["ai-workbench-panel"]):
            with gr.Row():
                ai_job_template = gr.Dropdown(
                    AI_JOB_TEMPLATE_CHOICES, value=defaults.default_ai_job_template, label="任务模板"
                )
                ai_job_apply = gr.Button("套用模板")
                ai_job_refresh = gr.Button("刷新任务", variant="primary", elem_classes=["page-refresh-btn"])
                ai_job_id = gr.Number(label="任务 ID", precision=0)
                ai_job_trigger = gr.Button("立即执行")
            with gr.Row():
                with gr.Column(scale=2, min_width=520):
                    ai_job_template_gallery = gr.HTML(
                        service.ai_job_template_cards(), elem_id="ai-job-template-gallery"
                    )
                with gr.Column(scale=1, min_width=320):
                    ai_job_status = gr.Code(language="json", label="操作结果")
            with gr.Accordion("创建定时任务", open=True):
                with gr.Row():
                    ai_job_name = gr.Textbox(label="任务名称")
                    ai_job_type = gr.Dropdown(
                        JOB_TYPE_OPTIONS, value="market_refresh", allow_custom_value=True, label="任务类型"
                    )
                    ai_job_cron = gr.Textbox(value="25 9 * * 1-5", label="Cron")
                    ai_job_enabled = gr.Checkbox(value=True, label="启用")
                ai_job_params = gr.Code(value=DEFAULT_JOB_PARAMS, language="json", label="任务参数")
                ai_job_create = gr.Button("保存任务", variant="primary")
            with gr.Accordion("任务执行明细", open=False):
                with gr.Row():
                    ai_job_table = _table("任务列表", 300)
                    ai_job_history = _table("执行历史", 300)
            with gr.Accordion("任务模板明细", open=False):
                ai_job_templates = _table("任务模板", 300)
        ai_job_apply.click(
            _safe(service.ai_job_template_form),
            inputs=ai_job_template,
            outputs=[ai_job_name, ai_job_type, ai_job_cron, ai_job_params, ai_job_enabled],
            queue=False,
        )
        ai_job_refresh.click(
            _safe(service.ai_job_catalog), outputs=[ai_job_template_gallery, ai_job_templates], queue=False
        )
        ai_job_refresh.click(_safe(service.jobs), outputs=ai_job_table, queue=False)
        ai_job_create.click(
            _safe(service.create_job),
            inputs=[ai_job_name, ai_job_type, ai_job_cron, ai_job_params, ai_job_enabled],
            outputs=[ai_job_status, ai_job_table],
        )
        ai_job_trigger.click(
            _safe(lambda value: service.job_action(value, "trigger")),
            inputs=ai_job_id,
            outputs=[ai_job_status, ai_job_table, ai_job_history],
        )


def render_capabilities(service, defaults, widgets=None, on_load=None):
    with gr.Tab("能力设置"):
        with gr.Column(elem_classes=["ai-workbench-panel"]):
            ai_capability_refresh = gr.Button("刷新能力", variant="primary", elem_classes=["page-refresh-btn"])
            ai_capability_cards = gr.HTML("<div class='ai-empty-state'>点击“刷新能力”读取 Skill 与 MCP 状态。</div>")
            with gr.Accordion("Skill 与 MCP 明细", open=False):
                with gr.Row():
                    ai_capability_skills = _table("Skill 包", 340)
                    ai_capability_mcps = _table("MCP 工具", 340)
        ai_capability_refresh.click(
            _safe(service.ai_capability_catalog),
            outputs=[ai_capability_cards, ai_capability_skills, ai_capability_mcps],
            queue=False,
        )
