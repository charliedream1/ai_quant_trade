"""Gradio UI for the live domain."""

from __future__ import annotations

import pandas as pd

import gradio as gr

from ..common.callbacks import safe as _safe
from ..common.components import table as _table
from ..common.navigation import workspace_link
from ..handlers import DomainHandler
from ..service.foundation import LIVE_BROKER_EVENT_CHOICES


def render_live(service: DomainHandler) -> None:
    with gr.Tab("实盘模块"):
        with gr.Tabs(elem_classes=["module-tabs"]):
            with gr.Tab("发布策略"):
                gr.Markdown("## 实盘管理", elem_classes=["section-title"])
                live_status_message = gr.Markdown(elem_classes=["status-strip"])
                with gr.Row():
                    live_refresh = gr.Button("刷新配置", variant="primary", elem_classes=["page-refresh-btn"])
                    live_config_id = gr.Number(label="配置 ID", precision=0)
                    live_start = gr.Button("启动")
                    live_run_id = gr.Number(label="运行 ID", precision=0)
                    live_query = gr.Button("查询状态")
                    live_pause = gr.Button("暂停")
                    live_resume = gr.Button("恢复")
                    live_stop = gr.Button("停止", variant="stop")
                with gr.Row():
                    live_error_reason = gr.Textbox(
                        value="人工标记异常冻结",
                        label="异常原因",
                        placeholder="输入异常冻结原因",
                    )
                    live_mark_error = gr.Button("标记异常", variant="secondary")
                live_configs = _table("实盘配置", 320)
                live_runs = _table("运行记录", 260)
                with gr.Accordion("通道适配器与事件", open=True):
                    with gr.Row():
                        live_adapter_refresh = gr.Button("查看通道适配器")
                        live_event_type = gr.Dropdown(
                            LIVE_BROKER_EVENT_CHOICES,
                            value="heartbeat",
                            label="事件类型",
                        )
                        live_event_message = gr.Textbox(
                            value="broker心跳中断",
                            label="事件说明",
                            placeholder="心跳可留空；异常事件需填写原因",
                        )
                        live_event_submit = gr.Button("写入通道事件", variant="secondary")
                    live_broker_adapters = _table("通道适配器", 260)
                with gr.Accordion("新建实盘配置", open=True):
                    with gr.Row():
                        live_name = gr.Textbox(label="配置名称")
                        live_strategy_id = gr.Number(label="策略 ID", precision=0)
                        live_channel = gr.Dropdown(["paper", "broker"], value="paper", label="通道")
                        live_capital = gr.Number(value=100000, label="资金")
                    with gr.Row():
                        live_params = gr.Code(value="{}", language="json", label="策略参数")
                        live_risk = gr.Code(
                            value='{"max_position_count": 5, "daily_loss_limit": 0.03}',
                            language="json",
                            label="风控参数",
                        )
                    with gr.Row():
                        live_validation_backtest_id = gr.Number(
                            label="验证回测 ID",
                            precision=0,
                        )
                        live_validation_account_id = gr.Number(
                            label="验证模拟账户 ID",
                            precision=0,
                        )
                    live_create = gr.Button("保存配置", variant="primary")
                with gr.Accordion("风控与运行监控", open=True):
                    with gr.Row():
                        live_risk_refresh = gr.Button("查看风控摘要")
                        live_risk_update = gr.Button("更新风控阈值", variant="primary")
                        live_monitor_refresh = gr.Button("刷新运行监控")
                    live_risk_patch = gr.Code(
                        value='{"max_position_count": 5, "daily_loss_limit": 0.03}',
                        language="json",
                        label="风控阈值编辑",
                    )
                    live_monitor_summary = gr.Markdown(elem_classes=["status-strip"])
                    with gr.Row():
                        live_risk_table = _table(
                            "风控摘要",
                            280,
                            value=pd.DataFrame(
                                [
                                    {
                                        "item": "配置选择",
                                        "value": "-",
                                        "status": "待选择",
                                        "note": "输入配置 ID 后查看风控阈值",
                                    }
                                ]
                            ),
                        )
                        live_alerts = _table(
                            "异常告警",
                            280,
                            value=pd.DataFrame(
                                [
                                    {
                                        "severity": "info",
                                        "title": "待选择运行",
                                        "message": "输入运行 ID 后刷新异常告警",
                                        "triggered_at": "-",
                                    }
                                ]
                            ),
                        )
                    live_logs = _table(
                        "运行日志",
                        300,
                        value=pd.DataFrame(
                            [
                                {
                                    "time": "-",
                                    "level": "info",
                                    "event": "待刷新",
                                    "detail": "输入运行 ID 后查看运行日志",
                                }
                            ]
                        ),
                    )
                with gr.Accordion("发布验证门槛", open=True):
                    live_validation_refresh = gr.Button("查看发布验证")
                    live_validation_table = _table(
                        "发布验证",
                        260,
                        value=pd.DataFrame(
                            [
                                {
                                    "检查项": "配置选择",
                                    "当前值": "-",
                                    "状态": "待选择",
                                    "说明": "输入配置 ID 后查看回测/模拟发布验证",
                                }
                            ]
                        ),
                    )
                with gr.Accordion("dry-run订单计划", open=True):
                    with gr.Row():
                        live_plan_symbols = gr.Textbox(
                            value="000001,300750",
                            label="计划标的",
                            placeholder="输入股票代码、名称、拼音或别名，逗号分隔",
                        )
                        live_plan_side = gr.Radio(
                            ["买入", "卖出"],
                            value="买入",
                            label="方向",
                        )
                        live_plan_order_type = gr.Radio(
                            ["市价", "限价"],
                            value="市价",
                            label="订单类型",
                        )
                    with gr.Row():
                        live_plan_weight = gr.Slider(
                            minimum=0.01,
                            maximum=1.0,
                            step=0.01,
                            value=0.5,
                            label="目标资金占比",
                        )
                        live_plan_max_orders = gr.Slider(
                            minimum=1,
                            maximum=20,
                            step=1,
                            value=5,
                            label="最多订单数",
                        )
                        live_plan_refresh = gr.Button("生成dry-run订单计划")
                        live_precheck_start = gr.Button("检查并启动", variant="primary")
                    live_plan_summary = gr.Markdown(elem_classes=["status-strip"])
                    with gr.Row():
                        live_plan_orders = _table("订单计划", 320)
                        live_precheck_table = _table("运行前风控", 320)
                live_run_status = gr.Code(language="json", label="运行状态机")
                with gr.Row():
                    live_orders = _table("订单", 320)
                    live_positions = _table("持仓", 320)
                live_refresh.click(_safe(service.live_configs), outputs=live_configs)
                live_refresh.click(_safe(service.live_runs), outputs=live_runs)
                live_refresh.click(_safe(service.live_broker_adapters), outputs=live_broker_adapters)
                live_adapter_refresh.click(
                    _safe(service.live_broker_adapters),
                    outputs=live_broker_adapters,
                )
                live_create.click(
                    _safe(service.create_live_config),
                    inputs=[
                        live_name,
                        live_strategy_id,
                        live_channel,
                        live_capital,
                        live_params,
                        live_risk,
                        live_validation_backtest_id,
                        live_validation_account_id,
                    ],
                    outputs=[live_status_message, live_configs],
                )
                live_risk_refresh.click(
                    _safe(service.live_risk_summary),
                    inputs=live_config_id,
                    outputs=live_risk_table,
                )
                live_risk_update.click(
                    _safe(service.update_live_risk),
                    inputs=[live_config_id, live_risk_patch],
                    outputs=[live_status_message, live_configs, live_risk_table],
                )
                live_validation_refresh.click(
                    _safe(service.live_validation_summary),
                    inputs=live_config_id,
                    outputs=live_validation_table,
                )
                live_monitor_refresh.click(
                    _safe(service.live_monitor),
                    inputs=live_run_id,
                    outputs=[live_monitor_summary, live_alerts, live_logs],
                )
                live_plan_refresh.click(
                    _safe(service.live_dry_run_plan),
                    inputs=[
                        live_config_id,
                        live_plan_symbols,
                        live_plan_side,
                        live_plan_order_type,
                        live_plan_weight,
                        live_plan_max_orders,
                    ],
                    outputs=[live_plan_summary, live_plan_orders, live_precheck_table],
                )
                live_precheck_start.click(
                    _safe(service.live_precheck_start),
                    inputs=[
                        live_config_id,
                        live_plan_symbols,
                        live_plan_side,
                        live_plan_order_type,
                        live_plan_weight,
                        live_plan_max_orders,
                    ],
                    outputs=[
                        live_status_message,
                        live_run_id,
                        live_run_status,
                        live_orders,
                        live_positions,
                        live_plan_summary,
                        live_plan_orders,
                        live_precheck_table,
                    ],
                )
                live_precheck_start.click(_safe(service.live_runs), outputs=live_runs)
                live_precheck_start.click(
                    _safe(service.live_monitor),
                    inputs=live_run_id,
                    outputs=[live_monitor_summary, live_alerts, live_logs],
                )
                live_start.click(
                    _safe(service.live_start),
                    inputs=live_config_id,
                    outputs=[
                        live_status_message,
                        live_run_id,
                        live_run_status,
                        live_orders,
                        live_positions,
                    ],
                )
                live_start.click(_safe(service.live_runs), outputs=live_runs)
                live_query.click(
                    _safe(service.live_status),
                    inputs=live_run_id,
                    outputs=[live_run_status, live_orders, live_positions],
                )
                live_query.click(
                    _safe(service.live_monitor),
                    inputs=live_run_id,
                    outputs=[live_monitor_summary, live_alerts, live_logs],
                )
                live_stop.click(
                    _safe(service.live_stop),
                    inputs=live_run_id,
                    outputs=[live_status_message, live_run_status, live_orders, live_positions],
                )
                live_stop.click(_safe(service.live_runs), outputs=live_runs)
                live_stop.click(
                    _safe(service.live_monitor),
                    inputs=live_run_id,
                    outputs=[live_monitor_summary, live_alerts, live_logs],
                )
                live_pause.click(
                    _safe(service.live_pause),
                    inputs=live_run_id,
                    outputs=[live_status_message, live_run_status, live_orders, live_positions],
                )
                live_pause.click(_safe(service.live_runs), outputs=live_runs)
                live_pause.click(
                    _safe(service.live_monitor),
                    inputs=live_run_id,
                    outputs=[live_monitor_summary, live_alerts, live_logs],
                )
                live_resume.click(
                    _safe(service.live_resume),
                    inputs=live_run_id,
                    outputs=[live_status_message, live_run_status, live_orders, live_positions],
                )
                live_resume.click(_safe(service.live_runs), outputs=live_runs)
                live_resume.click(
                    _safe(service.live_monitor),
                    inputs=live_run_id,
                    outputs=[live_monitor_summary, live_alerts, live_logs],
                )
                live_mark_error.click(
                    _safe(service.live_mark_error),
                    inputs=[live_run_id, live_error_reason],
                    outputs=[live_status_message, live_run_status, live_orders, live_positions],
                )
                live_mark_error.click(_safe(service.live_runs), outputs=live_runs)
                live_mark_error.click(
                    _safe(service.live_monitor),
                    inputs=live_run_id,
                    outputs=[live_monitor_summary, live_alerts, live_logs],
                )
                live_event_submit.click(
                    _safe(service.live_broker_event),
                    inputs=[live_run_id, live_event_type, live_event_message],
                    outputs=[live_status_message, live_run_status, live_orders, live_positions],
                )
                live_event_submit.click(_safe(service.live_runs), outputs=live_runs)
                live_event_submit.click(
                    _safe(service.live_monitor),
                    inputs=live_run_id,
                    outputs=[live_monitor_summary, live_alerts, live_logs],
                )

            with gr.Tab("归因分析"):
                gr.Markdown("实盘运行与回测/模拟账户在同一分析工作区查看，来源和账本保持独立。")
                gr.HTML(workspace_link("打开实盘运行归因", "simulation", "attribution", analysis_mode="live"))
