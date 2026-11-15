"""Chart-first homepage composition; detailed data stays in an expandable section."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import gradio as gr

from src.data import current_market, normalize_market

from ..common.callbacks import safe
from ..common.components import plot as _plot
from ..common.components import table
from ..handlers import DomainHandler
from ..service.foundation import ACCOUNT_MODE_CHOICES, switch_ui_market
from ..service.home_tables import home_styled_frame


def render_home(
    service: DomainHandler, market_switcher: gr.Radio, market_status: gr.Markdown, load_event: Callable[..., Any]
) -> None:
    selection = gr.State({"market": current_market(), "mode": "paper", "revision": 0, "refresh": False})
    with gr.Column(elem_id="home-dashboard"):
        with gr.Row(elem_classes=["home-control-row"]):
            gr.HTML("<div class='home-title'><span>PORTFOLIO OVERVIEW</span><strong>账户与市场总览</strong></div>")
            account_mode = gr.Radio(
                ACCOUNT_MODE_CHOICES,
                value="paper",
                label="账户视角",
                scale=0,
                elem_id="home-account-mode",
            )
            refresh = gr.Button(
                "刷新总览",
                variant="primary",
                scale=0,
                min_width=105,
                elem_id="home-refresh",
                elem_classes=["page-refresh-btn"],
            )
        status = gr.Markdown("正在读取账户、行情与任务快照。", elem_id="home-data-status")
        alerts = gr.HTML(elem_id="home-alerts")
        kpis = gr.HTML(elem_id="home-kpis")
        with gr.Row(elem_classes=["home-primary-row"]):
            with gr.Column(scale=2, min_width=340):
                trend = _plot(label="账户净值", show_label=False, elem_id="home-trend", elem_classes=["home-chart"])
            with gr.Column(scale=1, min_width=270):
                allocation = _plot(
                    label="资金配置", show_label=False, elem_id="home-allocation", elem_classes=["home-chart"]
                )
        with gr.Row(elem_classes=["home-risk-row"]):
            with gr.Column(scale=2, min_width=340):
                risk = gr.HTML(elem_id="home-risk")
                risk_alerts = gr.HTML(elem_id="home-risk-alerts")
            risk_radar = _plot(
                label="风险雷达", show_label=False, elem_id="home-risk-radar", elem_classes=["home-chart"]
            )
        market_brief = gr.HTML(elem_id="home-market-summary")
        with gr.Row(elem_classes=["home-secondary-row"]):
            sentiment = _plot(
                label="市场情绪雷达", show_label=False, elem_id="home-sentiment", elem_classes=["home-chart"]
            )
            sectors = _plot(label="板块涨跌概览", show_label=False, elem_id="home-sectors", elem_classes=["home-chart"])
            contribution = _plot(
                label="持仓浮动盈亏", show_label=False, elem_id="home-contribution", elem_classes=["home-chart"]
            )
        themes = gr.HTML(elem_id="home-themes")
        with gr.Row(elem_classes=["home-actions-row"]):
            with gr.Column(scale=2, min_width=310):
                gr.HTML("<div class='home-section-title'><strong>待处理事项</strong><span>按优先级排列</span></div>")
                actions_summary = gr.HTML(elem_id="home-actions")
            with gr.Column(scale=1, min_width=250):
                gr.HTML(
                    "<div class='home-section-title'><strong>执行状态</strong><span>回测、运行与定时任务</span></div>"
                )
                operations = gr.HTML(elem_id="dashboard-ai-workbench-entry")
        news = gr.HTML(elem_id="home-news")
        with gr.Accordion("完整数据与历史明细", open=False, elem_id="home-details") as details:
            gr.Markdown("数值色阶：红为正、绿为负，零值中性；蓝色表示规模，状态色另附文字。")
            holdings = table("持仓股票与行情", elem_classes=["home-semantic-table"])
            indices = table("主要指数", elem_classes=["home-semantic-table"])
            watchlist = table("自选行情", elem_classes=["home-semantic-table"])
            with gr.Row():
                monitor = table("短线监控雷达", elem_classes=["home-semantic-table"])
                style = table("市场风格", elem_classes=["home-semantic-table"])
            with gr.Row():
                theme = table("题材主动链", elem_classes=["home-semantic-table"])
                paths = table("下一交易段路径", elem_classes=["home-semantic-table"])
            risk_table = table("账户分层与风险", elem_classes=["home-semantic-table"])
            trade_history = table("历史交易与订单", elem_classes=["home-semantic-table"])
            with gr.Row():
                actions = table("待处理事项明细", elem_classes=["home-semantic-table"])
                strategy = table("策略与任务状态", elem_classes=["home-semantic-table"])

    def bind(event: Callable[..., Any], force: bool, market_event=False) -> None:
        def keep(state, revision):
            return state["revision"] == revision

        def account(mode, state):
            revision = state["revision"]
            if market_event and not state["refresh"]:
                return tuple(gr.skip() for _ in range(9))
            result = service.home_account(mode, force_refresh=force)
            return result if keep(state, revision) else tuple(gr.skip() for _ in range(9))

        def operations_load(mode, state):
            revision = state["revision"]
            if market_event and not state["refresh"]:
                return tuple(gr.skip() for _ in range(3))
            result = service.home_operations(mode, force_refresh=force)
            return result if keep(state, revision) else tuple(gr.skip() for _ in range(3))

        def market_load(mode, state):
            revision = state["revision"]
            if market_event and not state["refresh"]:
                return tuple(gr.skip() for _ in range(6))
            result = service.home_market(mode, force_refresh=force)
            return result if keep(state, revision) else tuple(gr.skip() for _ in range(6))

        def news_load(mode, state):
            revision = state["revision"]
            if market_event and not state["refresh"]:
                return gr.skip()
            result = service.home_news(mode, force_refresh=force)
            return result if keep(state, revision) else gr.skip()

        event(
            safe(account),
            inputs=[account_mode, selection],
            outputs=[status, kpis, risk, risk_alerts, risk_radar, trend, allocation, contribution, holdings],
            queue=False,
        ).then(
            safe(operations_load),
            inputs=[account_mode, selection],
            outputs=[alerts, actions_summary, operations],
            queue=False,
        )
        # Local task state is useful before account valuation; the chained update adds final valuation status.
        event(
            safe(operations_load),
            inputs=[account_mode, selection],
            outputs=[alerts, actions_summary, operations],
            queue=False,
        )
        event(
            safe(market_load),
            inputs=[account_mode, selection],
            outputs=[market_brief, sentiment, sectors, themes, indices, watchlist],
            queue=False,
        )
        event(safe(news_load), inputs=[account_mode, selection], outputs=news, queue=False)

    def market_changed(value: str, state):
        market = normalize_market(value)
        changed = market != state["market"]
        state.update(market=market, revision=state["revision"] + int(changed), refresh=changed)
        if changed:
            switch_ui_market(value)
        return f"Market: {market}", state

    market_event = market_switcher.input(
        safe(market_changed), inputs=[market_switcher, selection], outputs=[market_status, selection], queue=False
    )
    bind(market_event.then, True, market_event=True)
    bind(refresh.click, True)

    def account_changed(mode, state):
        changed = mode != state["mode"]
        state.update(mode=mode, revision=state["revision"] + int(changed))
        return state

    account_event = account_mode.input(
        account_changed, inputs=[account_mode, selection], outputs=selection, queue=False
    )
    bind(account_event.then, False)
    bind(load_event, False)

    def market_details(mode: str) -> tuple:
        return tuple(home_styled_frame(frame) for frame in service.dashboard_market(mode)[:4])

    details.expand(safe(market_details), inputs=account_mode, outputs=[monitor, style, theme, paths], queue=False)
    details.expand(
        safe(lambda mode: home_styled_frame(service.dashboard_account(mode)[0])),
        inputs=account_mode,
        outputs=risk_table,
        queue=False,
    )
    details.expand(safe(service.dashboard_trade_history), inputs=account_mode, outputs=trade_history, queue=False)
    details.expand(
        safe(lambda mode: tuple(home_styled_frame(frame) for frame in service.dashboard_strategy(mode))),
        inputs=account_mode,
        outputs=[actions, strategy],
        queue=False,
    )
