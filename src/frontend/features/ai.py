"""Gradio UI for the ai domain."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import gradio as gr

from ..handlers import DomainHandler
from .ai_console_page import render_console
from .ai_insights_page import render_insights_page
from .ai_workflow_page import render_workflow
from .ai_workflow_panels import WorkflowDefaults


def render_ai(
    service: DomainHandler,
    default_ai_task_type: str,
    default_ai_expert: str,
    default_ai_team: str,
    default_ai_job_template: str,
    on_load: Callable[..., Any] | None = None,
) -> None:
    with gr.Tab("AI工作台"):
        with gr.Tabs(elem_classes=["module-tabs", "ai-workspace-pages"]):
            render_console(service, on_load)
            render_insights_page(service, on_load)
            render_workflow(
                service,
                WorkflowDefaults(default_ai_task_type, default_ai_expert, default_ai_team, default_ai_job_template),
                on_load,
            )
