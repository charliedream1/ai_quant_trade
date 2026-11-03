"""Gradio UI for the simulation domain."""

from __future__ import annotations

import gradio as gr

from ..common.callbacks import safe as _safe
from ..common.components import plot as _plot
from ..common.components import table as _table
from ..handlers import DomainHandler
from ..service.foundation import (
    BACKTEST_ENGINE_CHOICES,
    BACKTEST_ORDER_TYPE_CHOICES,
    BACKTEST_PRICE_ADJUSTMENT_CHOICES,
)
from .analysis import render_analysis
from .execution_costs import render_execution_controls
from .parameters import render_parameter_controls


def render_simulation(service: DomainHandler) -> None:
    with gr.Tab("策略仿真"):
        with gr.Tabs(elem_classes=["module-tabs"]):
            with gr.Tab("回测与模拟"):
                with gr.Tabs():
                    with gr.Tab("回测"):
                        with gr.Row():
                            backtest_strategy_id = gr.Number(
                                label="策略 ID", precision=0, elem_id="route-backtest-strategy-id"
                            )
                            backtest_symbols = gr.Textbox(value="600519,300750", label="标的代码")
                            backtest_capital = gr.Number(value=1000000, label="初始资金")
                            backtest_engine = gr.Dropdown(
                                BACKTEST_ENGINE_CHOICES,
                                value="auto",
                                label="回测引擎",
                            )
                        with gr.Row():
                            backtest_start = gr.Textbox(value="2026-01-01", label="开始日期")
                            backtest_end = gr.Textbox(value="2026-06-30", label="结束日期")
                        parameter_controls = render_parameter_controls(service, backtest_strategy_id)
                        with gr.Accordion("订单与组合约束", open=True):
                            with gr.Row():
                                backtest_order_type = gr.Dropdown(
                                    BACKTEST_ORDER_TYPE_CHOICES,
                                    value="market",
                                    label="订单类型",
                                )
                                backtest_price_adjustment = gr.Dropdown(
                                    BACKTEST_PRICE_ADJUSTMENT_CHOICES,
                                    value="qfq",
                                    label="复权方式",
                                )
                                backtest_slippage = gr.State(0.0)
                            with gr.Row():
                                backtest_max_position_count = gr.Slider(
                                    1,
                                    20,
                                    value=5,
                                    step=1,
                                    label="最大持仓数",
                                )
                                backtest_max_position_weight = gr.Slider(
                                    0.01,
                                    1.0,
                                    value=0.3,
                                    step=0.01,
                                    label="单票最大权重",
                                )
                                backtest_lot_size = gr.State(100)
                        execution_costs = render_execution_controls(service, strategy_id=backtest_strategy_id)
                        with gr.Row():
                            backtest_create = gr.Button("开始回测", variant="primary")
                            backtest_refresh = gr.Button("刷新任务", elem_classes=["page-refresh-btn"])
                            backtest_task_id = gr.Number(label="任务 ID", precision=0, elem_id="route-backtest-task-id")
                            backtest_view = gr.Button("查看结果", elem_id="route-backtest-open")
                            backtest_delete = gr.Button("删除任务", variant="stop")
                        backtest_status = gr.Markdown(elem_classes=["status-strip"])
                        with gr.Column(elem_classes=["backtest-results-panel"]):
                            gr.Markdown("#### 回测结果总览")
                            backtest_explanation = gr.Markdown(
                                "- 运行回测后，这里会显示数据源、样本量和指标解读。",
                                elem_classes=["compact-note", "backtest-explanation"],
                            )
                            backtest_metrics = _table("绩效指标（按收益 / 风险 / 交易 / 执行分组）", 360)
                            backtest_plot = _plot(
                                label="净值与回撤",
                                elem_classes=["chart-panel"],
                            )
                            with gr.Row():
                                backtest_monthly_plot = _plot(
                                    label="月度收益热力",
                                    elem_classes=["chart-panel"],
                                )
                                backtest_rolling_plot = _plot(
                                    label="滚动风险指标",
                                    elem_classes=["chart-panel"],
                                )
                            with gr.Row():
                                backtest_trade_plot = _plot(
                                    label="交易盈亏分布",
                                    elem_classes=["chart-panel"],
                                )
                                backtest_exposure_plot = _plot(
                                    label="持仓暴露与组合规模",
                                    elem_classes=["chart-panel"],
                                )
                            with gr.Row():
                                backtest_attribution_plot = _plot(
                                    label="标的盈亏归因",
                                    elem_classes=["chart-panel"],
                                )
                                backtest_attribution_table = _table("归因明细与风险提示", 300)
                            with gr.Accordion("交易明细", open=False):
                                backtest_trades = _table("已平仓交易", 320)
                        with gr.Accordion("回测证据与模拟衔接", open=False, elem_classes=["backtest-evidence-panel"]):
                            gr.Markdown("#### 回测证据与模拟衔接")
                            with gr.Row():
                                backtest_snapshot_btn = gr.Button("查看参数快照")
                                backtest_export_trades = gr.Button("导出交易日志")
                                backtest_trade_file = gr.Textbox(label="交易日志文件路径", interactive=False)
                            backtest_snapshot = gr.Markdown(elem_classes=["compact-note"])
                            backtest_export_status = gr.Markdown(elem_classes=["status-strip"])
                            with gr.Row():
                                backtest_paper_name = gr.Textbox(label="模拟账户名称（可选）")
                                backtest_paper_cash = gr.Number(label="模拟初始资金（留空用回测资金）")
                                backtest_to_paper = gr.Button("一键创建模拟账户", variant="primary")
                            backtest_paper_status = gr.Markdown(elem_classes=["status-strip"])
                        with gr.Accordion("回测参数对比", open=False):
                            with gr.Row():
                                backtest_compare_ids = gr.Textbox(
                                    label="回测任务 ID（逗号分隔，留空取最近任务）",
                                    placeholder="如：12,13,14",
                                    scale=3,
                                )
                                backtest_compare_latest = gr.Slider(
                                    1,
                                    10,
                                    value=5,
                                    step=1,
                                    label="最近任务数",
                                )
                                backtest_compare_run = gr.Button("对比回测", variant="primary")
                            backtest_compare_status = gr.Markdown(elem_classes=["status-strip"])
                            backtest_compare_plot = _plot(
                                label="参数对比图",
                                elem_classes=["chart-panel"],
                            )
                            backtest_compare_table = _table("回测指标对比", 260)
                            backtest_compare_params = _table("回测参数摘要", 240)
                        with gr.Accordion("任务与引擎", open=False):
                            backtest_engine_status = _table("回测引擎状态", 220)
                            backtest_table = _table("回测任务", 300)

                        def _create_backtest(*values):
                            return service.create_backtest(
                                *values[:14], execution_costs=execution_costs.parse(values[14:])
                            )

                        backtest_create_event = backtest_create.click(
                            _safe(_create_backtest),
                            inputs=[
                                backtest_strategy_id,
                                backtest_symbols,
                                backtest_start,
                                backtest_end,
                                backtest_capital,
                                parameter_controls.overrides,
                                backtest_engine,
                                backtest_order_type,
                                backtest_price_adjustment,
                                backtest_max_position_count,
                                backtest_max_position_weight,
                                backtest_lot_size,
                                backtest_slippage,
                                parameter_controls.profile,
                                *execution_costs.inputs,
                            ],
                            outputs=[
                                backtest_status,
                                backtest_task_id,
                                backtest_table,
                                backtest_metrics,
                                backtest_plot,
                                backtest_trades,
                                backtest_attribution_plot,
                                backtest_attribution_table,
                            ],
                        )
                        backtest_create_event.success(
                            _safe(service.backtest_resolved_parameters),
                            inputs=backtest_task_id,
                            outputs=[parameter_controls.resolved, parameter_controls.status],
                        )
                        backtest_create_event.success(
                            _safe(service.backtest_analysis),
                            inputs=backtest_task_id,
                            outputs=[
                                backtest_explanation,
                                backtest_monthly_plot,
                                backtest_rolling_plot,
                                backtest_trade_plot,
                                backtest_exposure_plot,
                            ],
                        )
                        backtest_refresh.click(_safe(service.backtests), outputs=backtest_table)
                        backtest_refresh.click(_safe(service.backtest_engines), outputs=backtest_engine_status)
                        backtest_view_event = backtest_view.click(
                            _safe(service.backtest_detail),
                            inputs=backtest_task_id,
                            outputs=[
                                backtest_metrics,
                                backtest_plot,
                                backtest_trades,
                                backtest_attribution_plot,
                                backtest_attribution_table,
                            ],
                        )
                        backtest_view_event.success(
                            _safe(service.backtest_resolved_parameters),
                            inputs=backtest_task_id,
                            outputs=[parameter_controls.resolved, parameter_controls.status],
                        )
                        backtest_view_event.success(
                            _safe(service.backtest_analysis),
                            inputs=backtest_task_id,
                            outputs=[
                                backtest_explanation,
                                backtest_monthly_plot,
                                backtest_rolling_plot,
                                backtest_trade_plot,
                                backtest_exposure_plot,
                            ],
                        )
                        backtest_snapshot_btn.click(
                            _safe(service.backtest_param_snapshot),
                            inputs=backtest_task_id,
                            outputs=backtest_snapshot,
                        )
                        backtest_export_trades.click(
                            _safe(service.export_backtest_trades),
                            inputs=backtest_task_id,
                            outputs=[backtest_export_status, backtest_trade_file],
                        )
                        backtest_compare_run.click(
                            _safe(service.compare_backtests),
                            inputs=[backtest_compare_ids, backtest_compare_latest],
                            outputs=[
                                backtest_compare_status,
                                backtest_compare_table,
                                backtest_compare_plot,
                                backtest_compare_params,
                            ],
                        )
                        backtest_delete_event = backtest_delete.click(
                            _safe(service.delete_backtest),
                            inputs=backtest_task_id,
                            outputs=[
                                backtest_status,
                                backtest_table,
                                backtest_metrics,
                                backtest_plot,
                                backtest_trades,
                                backtest_attribution_plot,
                                backtest_attribution_table,
                            ],
                        )
                        backtest_delete_event.then(
                            _safe(service.empty_backtest_analysis),
                            outputs=[
                                backtest_explanation,
                                backtest_monthly_plot,
                                backtest_rolling_plot,
                                backtest_trade_plot,
                                backtest_exposure_plot,
                            ],
                        )
                    with gr.Tab("模拟交易"):
                        with gr.Accordion("新建账户", open=True):
                            with gr.Row():
                                paper_name = gr.Textbox(label="账户名称")
                                paper_strategy_id = gr.Number(label="策略 ID（可选）", precision=0)
                                paper_capital = gr.Number(value=1000000, label="初始资金")
                                paper_create = gr.Button("创建账户", variant="primary")
                        paper_status = gr.Markdown(elem_classes=["status-strip"])
                        with gr.Row():
                            paper_account_id = gr.Number(label="账户 ID", precision=0, elem_id="route-paper-account-id")
                            paper_refresh = gr.Button("刷新账户", elem_classes=["page-refresh-btn"])
                        paper_overview = gr.Code(language="json", label="账户概览")
                        with gr.Row():
                            paper_positions = _table("持仓", 300)
                            paper_orders = _table("委托", 300)
                        paper_nav = _plot(
                            label="账户净值",
                            elem_classes=["chart-panel"],
                        )
                        with gr.Accordion("委托下单", open=True):
                            with gr.Row():
                                paper_symbol = gr.Textbox(value="600519", label="股票代码/名称")
                                paper_side = gr.Radio(["buy", "sell"], value="buy", label="方向")
                                paper_order_type = gr.Radio(["market", "limit"], value="market", label="订单类型")
                                paper_price = gr.Number(label="委托价格")
                                paper_quantity = gr.Number(value=100, label="数量", precision=0)
                                paper_submit = gr.Button("提交委托", variant="primary")
                        with gr.Row():
                            paper_cancel_order_id = gr.Number(label="撤单订单 ID", precision=0)
                            paper_cancel = gr.Button("撤销委托", variant="stop")
                            paper_match = gr.Button("撮合挂单", variant="primary")
                        paper_create.click(
                            _safe(service.create_paper_account),
                            inputs=[paper_name, paper_strategy_id, paper_capital],
                            outputs=[
                                paper_status,
                                paper_account_id,
                                paper_overview,
                                paper_positions,
                                paper_orders,
                                paper_nav,
                            ],
                        )
                        paper_refresh.click(
                            _safe(service.paper_overview),
                            inputs=paper_account_id,
                            outputs=[paper_overview, paper_positions, paper_orders, paper_nav],
                        )
                        paper_submit.click(
                            _safe(service.paper_order),
                            inputs=[
                                paper_account_id,
                                paper_symbol,
                                paper_side,
                                paper_order_type,
                                paper_price,
                                paper_quantity,
                            ],
                            outputs=[
                                paper_status,
                                paper_overview,
                                paper_positions,
                                paper_orders,
                                paper_nav,
                            ],
                        )
                        paper_cancel.click(
                            _safe(service.paper_cancel),
                            inputs=[paper_account_id, paper_cancel_order_id],
                            outputs=[
                                paper_status,
                                paper_overview,
                                paper_positions,
                                paper_orders,
                                paper_nav,
                            ],
                        )
                        paper_match.click(
                            _safe(service.paper_match_orders),
                            inputs=paper_account_id,
                            outputs=[
                                paper_status,
                                paper_overview,
                                paper_positions,
                                paper_orders,
                                paper_nav,
                            ],
                        )
                        backtest_to_paper.click(
                            _safe(service.backtest_to_paper_account),
                            inputs=[backtest_task_id, backtest_paper_name, backtest_paper_cash],
                            outputs=[
                                backtest_paper_status,
                                paper_account_id,
                                paper_overview,
                                paper_positions,
                                paper_orders,
                                paper_nav,
                            ],
                        )

            with gr.Tab("运行归因"):
                render_analysis(service)
