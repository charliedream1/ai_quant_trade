"""Gradio Blocks application definition."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import gradio as gr

from .common.callbacks import callback_location as _callback_location
from .common.callbacks import safe as _safe
from .common.components import chatbot as _chatbot
from .common.components import supports_parameter as _supports_parameter
from .common.components import table as _table
from .features.learning import render_learning
from .handlers import build_frontend_handlers
from .header import header_html
from .services import (
    AI_EXPERT_CHOICES,
    AI_JOB_TEMPLATE_CHOICES,
    AI_TASK_TYPE_CHOICES,
    AI_TEAM_CHOICES,
    RELATION_TYPE_CHOICES,
    FrontendService,
    current_market,
    strategy_example_choices,
)
from .theme import APP_JS, CSS, HOME_CSS, gradio_mount_options
from .theme import theme as _theme

__all__ = [
    "APP_JS",
    "CSS",
    "_callback_location",
    "_chatbot",
    "_safe",
    "_supports_parameter",
    "_table",
    "build_gradio_app",
    "gradio_mount_options",
]


@lru_cache(maxsize=1)
def build_gradio_app() -> gr.Blocks:
    """Build the complete compatibility UI from the same domain renderers."""
    from .features import (
        render_admin,
        render_ai,
        render_dashboard,
        render_floating_assistant,
        render_knowledge,
        render_live,
        render_market,
        render_research,
        render_simulation,
        render_strategy,
    )

    service = FrontendService()
    handlers = build_frontend_handlers(service)
    strategy_examples = strategy_example_choices()
    default_relation_types = [value for _, value in RELATION_TYPE_CHOICES]
    default_ai_task_type = AI_TASK_TYPE_CHOICES[0][1] if AI_TASK_TYPE_CHOICES else "general"
    default_ai_expert = AI_EXPERT_CHOICES[0][1] if AI_EXPERT_CHOICES else ""
    default_ai_team = AI_TEAM_CHOICES[0][1] if AI_TEAM_CHOICES else ""
    default_ai_job_template = AI_JOB_TEMPLATE_CHOICES[0][1] if AI_JOB_TEMPLATE_CHOICES else ""
    blocks_options: dict[str, Any] = {"title": "一体化量化交易平台", "fill_width": True}
    if _supports_parameter(gr.Blocks, "theme"):
        blocks_options.update(theme=_theme(), css=CSS + HOME_CSS, js=APP_JS)

    with gr.Blocks(**blocks_options) as demo:
        gr.HTML(header_html())
        with gr.Row(elem_id="market-switcher-row"):
            market_switcher = gr.Radio(
                ["A股", "美股"],
                value=None,
                label="市场",
                interactive=True,
                elem_id="market-switcher",
                scale=0,
                min_width=260,
            )
            market_status = gr.Markdown(
                f"当前市场：**{'美股' if current_market() == 'US' else 'A股'}**  ·  切换后按需刷新当前模块",
                elem_classes=["market-status-strip"],
            )

        with gr.Tabs(elem_id="main-navigation"):
            render_dashboard(handlers.dashboard, market_switcher, market_status, demo.load)
            render_market(handlers.market, default_relation_types)
            render_research(handlers.research)
            render_strategy(handlers.strategy, strategy_examples)
            render_simulation(handlers.simulation)
            render_live(handlers.live)
            render_ai(
                handlers.ai,
                default_ai_task_type,
                default_ai_expert,
                default_ai_team,
                default_ai_job_template,
            )
            render_knowledge(handlers.knowledge)
            render_learning()
            render_admin(handlers.admin)

        render_floating_assistant(handlers.assistant)
        gr.HTML(
            "<div class='compact-note'><p>仅供学习和研究使用，不构成投资建议。"
            "数据源与交易通道状态以系统配置为准。</p></div>"
        )

    return demo.queue(default_concurrency_limit=8)
