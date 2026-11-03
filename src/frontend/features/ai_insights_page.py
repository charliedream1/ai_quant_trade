"""A focused section of the existing Gradio AI workspace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import gradio as gr

from ..common.callbacks import safe as _safe
from ..common.components import plot as _plot
from ..common.components import table as _table
from ..service.foundation import (
    ACCOUNT_MODE_CHOICES,
)
from .insights import render_insights


def render_insights_page(service, on_load=None):
    with gr.Tab("智能洞察"):
        with gr.Tabs():
            with gr.Tab("Skill 报告"):
                render_insights(service)
            with gr.Tab("每日行情") as ai_daily_market_tab:
                with gr.Column(elem_classes=["ai-workbench-panel"]):
                    with gr.Row():
                        ai_daily_account_mode = gr.Radio(ACCOUNT_MODE_CHOICES, value="paper", label="账户视角")
                        ai_daily_refresh = gr.Button(
                            "刷新每日行情", variant="primary", elem_classes=["page-refresh-btn"]
                        )
                    with gr.Row():
                        ai_daily_market_brief = gr.HTML()
                        ai_daily_news_cards = gr.HTML()
                    with gr.Row():
                        ai_daily_monitor = _table("短线监控雷达", 300)
                        ai_daily_style = _table("市场风格", 300)
                    with gr.Row():
                        ai_daily_theme_chain = _table("题材主动链", 300)
                        ai_daily_paths = _table("下一交易段路径", 300)
                    with gr.Row():
                        ai_daily_indices = _table("主要指数", 300)
                        ai_daily_watchlist = _table("自选行情", 300)
                    ai_daily_sector_plot = _plot(label="市场背景", elem_classes=["chart-panel"])
                ai_daily_market_outputs = [
                    ai_daily_monitor,
                    ai_daily_style,
                    ai_daily_theme_chain,
                    ai_daily_paths,
                    ai_daily_indices,
                    ai_daily_watchlist,
                    ai_daily_sector_plot,
                ]

                def _bind_ai_daily_market(event_method: Callable[..., Any], force_refresh: bool) -> None:
                    event_method(
                        _safe(lambda mode: service.dashboard_market_brief(mode, force_refresh=force_refresh)),
                        inputs=ai_daily_account_mode,
                        outputs=[ai_daily_market_brief, ai_daily_news_cards],
                        queue=False,
                    )
                    event_method(
                        _safe(lambda mode: service.dashboard_market(mode, force_refresh=force_refresh)),
                        inputs=ai_daily_account_mode,
                        outputs=ai_daily_market_outputs,
                        queue=False,
                    )

                _bind_ai_daily_market(ai_daily_refresh.click, True)
                _bind_ai_daily_market(ai_daily_market_tab.select, False)
                _bind_ai_daily_market(ai_daily_account_mode.change, False)
            with gr.Tab("问数"):
                with gr.Column(elem_classes=["ai-workbench-panel"]):
                    ai_insight_question = gr.Textbox(
                        label="问题", lines=4, placeholder="例如：今天市场主线和我的持仓风险有什么关系？"
                    )
                    with gr.Row():
                        ai_insight_category = gr.Number(label="分类 ID", precision=0)
                        ai_insight_top_k = gr.Slider(1, 10, value=5, step=1, label="引用数量")
                    ai_insight_ask = gr.Button("提问", variant="primary")
                    ai_insight_answer = gr.Markdown(label="回答")
                    ai_insight_sources = _table("引用来源", 280)
                ai_insight_ask.click(
                    _safe(service.kb_qa),
                    inputs=[ai_insight_question, ai_insight_category, ai_insight_top_k],
                    outputs=[ai_insight_answer, ai_insight_sources],
                )
