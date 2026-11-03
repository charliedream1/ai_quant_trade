"""Gradio UI for the strategy domain."""

from __future__ import annotations

import gradio as gr
from src.engine.backtest.config import backtest_config

from ..common.callbacks import safe as _safe
from ..common.components import plot as _plot
from ..common.components import table as _table
from ..common.navigation import workspace_link
from ..handlers import DomainHandler
from ..service.foundation import (
    BACKTEST_ENGINE_CHOICES,
    CLI_TYPE_CHOICES,
    QLIB_RUN_TYPE_CHOICES,
    STRATEGY_PARAM_TYPE_CHOICES,
)
from .alpha import render_alpha
from .composition import render_composition
from .execution_costs import render_execution_controls
from .factor_monitor import render_factor_monitor
from .parameters import render_parameter_controls
from .source_review import render_source_review


def render_strategy(service: DomainHandler, strategy_examples: list[tuple[str, str]]) -> None:
    with gr.Tab("策略构建"):
        with gr.Tabs(elem_classes=["module-tabs"]):
            with gr.Tab("因子研究与监控"):
                render_factor_monitor(service, strategy=True)

            with gr.Tab("Alpha研究") as alpha_tab:
                render_alpha(service, alpha_tab)

            with gr.Tab("Qlib实验"):
                qlib_workflow_path, qlib_provider_uri, qlib_params_value = service.qlib_workflow_defaults()
                with gr.Column(elem_classes=["ai-workbench-panel"]):
                    gr.HTML(
                        "<section class='ai-workbench-overview'>"
                        "<div class='ai-overview-hero'><span>Qlib Lab</span>"
                        "<strong>数据集、Workflow、参数和运行记录</strong>"
                        "<p>先登记 Qlib 实验配置和运行记录，后续接入真实 pyqlib runner 后，"
                        "可继续沉淀模型训练、回测指标和产物路径。</p></div>"
                        "</section>",
                        elem_id="ai-qlib-workflow",
                    )
                    with gr.Row():
                        ai_qlib_run_type = gr.Dropdown(
                            QLIB_RUN_TYPE_CHOICES,
                            value="workflow",
                            label="运行类型",
                            scale=1,
                        )
                        ai_qlib_workflow_path = gr.Textbox(
                            value=qlib_workflow_path,
                            label="Workflow YAML",
                            scale=3,
                        )
                        ai_qlib_provider_uri = gr.Textbox(
                            value=qlib_provider_uri,
                            label="provider_uri",
                            scale=3,
                        )
                    ai_qlib_params = gr.Code(
                        value=qlib_params_value,
                        language="json",
                        label="运行参数",
                    )
                    with gr.Row():
                        ai_qlib_refresh = gr.Button(
                            "刷新Qlib状态",
                            variant="primary",
                            elem_classes=["page-refresh-btn"],
                        )
                        ai_qlib_register = gr.Button("登记Workflow运行")
                    ai_qlib_status = gr.Markdown(elem_classes=["status-strip"])
                    with gr.Row():
                        ai_qlib_config = _table("Qlib配置", 300)
                        ai_qlib_runs = _table("Qlib运行历史", 340)
                ai_qlib_refresh.click(
                    _safe(service.qlib_workflow_status),
                    inputs=ai_qlib_run_type,
                    outputs=[ai_qlib_status, ai_qlib_config, ai_qlib_runs],
                    queue=False,
                )
                ai_qlib_register.click(
                    _safe(service.qlib_workflow_create_run),
                    inputs=[
                        ai_qlib_run_type,
                        ai_qlib_workflow_path,
                        ai_qlib_provider_uri,
                        ai_qlib_params,
                    ],
                    outputs=[ai_qlib_status, ai_qlib_runs],
                )
            with gr.Tab("ETF研究") as etf_tab:
                with gr.Column(elem_classes=["ai-workbench-panel"]):
                    with gr.Row():
                        etf_universe = gr.Dropdown(
                            choices=service.etf_universe_choices(),
                            value=(service.etf_universe_choices() or [("A股核心宽基 ETF", "cn_core")])[0][1],
                            label="ETF池",
                            scale=3,
                        )
                        etf_refresh = gr.Button("刷新 ETF 数据", variant="primary")
                    etf_status = gr.Markdown(elem_classes=["status-strip"])
                    etf_table = _table("ETF 元数据与数据源快照", 360)
                etf_refresh.click(
                    _safe(service.etf_universe_snapshot),
                    inputs=etf_universe,
                    outputs=[etf_status, etf_table],
                    queue=False,
                )
                etf_tab.select(
                    _safe(service.etf_universe_snapshot),
                    inputs=etf_universe,
                    outputs=[etf_status, etf_table],
                    queue=False,
                )
            with gr.Tab("图形策略工坊"):
                workshop_activate = gr.Button("打开策略工坊", elem_id="workspace-activate-composition")

                def _activate_workshop():
                    return gr.update(visible=False)

                workshop_activate.click(_activate_workshop, outputs=workshop_activate, queue=False)

                @gr.render(triggers=[workshop_activate.click], queue=False)
                def _render_workshop():
                    render_composition(service)

            with gr.Tab("策略管理"):
                gr.HTML(workspace_link("＋ 打开图形策略工坊，组合规则、模型与风控", "strategy", "workshop"))
                with gr.Tabs():
                    with gr.Tab("生命周期"):
                        strategy_lifecycle_refresh = gr.Button(
                            "刷新生命周期", variant="primary", elem_classes=["page-refresh-btn"]
                        )
                        strategy_lifecycle_summary = gr.Markdown(elem_classes=["status-strip"])
                        strategy_lifecycle_board = gr.HTML()
                        strategy_lifecycle_table = _table("策略生命周期明细", 360)
                        strategy_lifecycle_refresh.click(
                            _safe(service.strategy_lifecycle),
                            outputs=[
                                strategy_lifecycle_summary,
                                strategy_lifecycle_board,
                                strategy_lifecycle_table,
                            ],
                            queue=False,
                        )

                    with gr.Tab("策略库"):
                        with gr.Row():
                            strategy_keyword = gr.Textbox(label="策略搜索")
                            strategy_refresh = gr.Button("刷新", variant="primary", elem_classes=["page-refresh-btn"])
                        strategy_table = _table("策略列表", 360)
                        strategy_stat_plot = _plot(
                            label="策略分布",
                            elem_classes=["chart-panel"],
                        )
                        with gr.Row():
                            strategy_id = gr.Number(label="策略 ID", precision=0)
                            strategy_detail_btn = gr.Button("查看详情")
                            strategy_enable = gr.Button("启用")
                            strategy_disable = gr.Button("停用")
                            strategy_delete = gr.Button("删除", variant="stop")
                        strategy_status = gr.Markdown(elem_classes=["status-strip"])
                        strategy_meta = gr.Code(language="json", label="策略信息")
                        strategy_params_view = gr.Code(language="json", label="默认参数")
                        strategy_interface_view = gr.Code(language="json", label="接口检查")
                        strategy_code_view = gr.Code(language="python", label="策略代码")
                        render_source_review(strategy_id)
                        with gr.Accordion("策略版本对比", open=True):
                            strategy_compare_versions = gr.Button("生成策略版本对比", variant="primary")
                            strategy_compare_status = gr.Markdown(elem_classes=["status-strip"])
                            strategy_compare_table = _table("策略版本对比", 260)
                        with gr.Accordion("策略一键回测", open=True):
                            quick_defaults = backtest_config()["quick"]
                            quick_capability = gr.Markdown("点击列表中的策略行即可选择；默认跟随策略的实际执行能力。")
                            with gr.Row():
                                strategy_quick_symbols = gr.Textbox(
                                    value=quick_defaults["symbols"], label="回测标的", scale=2
                                )
                                strategy_quick_capital = gr.Number(
                                    value=quick_defaults["initial_capital"], label="初始资金"
                                )
                                strategy_quick_engine = gr.Dropdown(
                                    BACKTEST_ENGINE_CHOICES,
                                    value="auto",
                                    label="回测引擎",
                                )
                            with gr.Row():
                                strategy_quick_start = gr.Textbox(value=quick_defaults["start_date"], label="开始日期")
                                strategy_quick_end = gr.Textbox(value=quick_defaults["end_date"], label="结束日期")
                            parameter_controls = render_parameter_controls(service, strategy_id)
                            quick_execution_costs = render_execution_controls(service, strategy_id=strategy_id)
                            with gr.Row():
                                strategy_quick_run = gr.Button("策略一键回测", variant="primary")
                                strategy_quick_cancel = gr.Button("取消回测")
                                strategy_quick_refresh = gr.Button("刷新回测任务")
                                strategy_quick_task_id = gr.Number(
                                    label="回测任务 ID（可恢复）", precision=0, interactive=True
                                )
                            strategy_quick_status = gr.Markdown(elem_classes=["status-strip"])
                            strategy_quick_timer = gr.Timer(
                                backtest_config()["execution"]["poll_seconds"], active=False
                            )
                            strategy_quick_backtests = _table("最近回测任务", 260)

                        def _select_strategy(frame, evt: gr.SelectData):
                            if "strategy_id" not in frame.columns:
                                return gr.skip()
                            return int(frame.iloc[evt.index[0]]["strategy_id"])

                        strategy_table.select(_select_strategy, inputs=strategy_table, outputs=strategy_id, queue=False)
                        strategy_id.change(
                            _safe(service.quick_capability),
                            inputs=strategy_id,
                            outputs=[quick_capability, strategy_quick_engine],
                            queue=False,
                        )
                        strategy_quick_timer.tick(
                            _safe(service.quick_poll),
                            inputs=strategy_quick_task_id,
                            outputs=[strategy_quick_status, strategy_quick_backtests, strategy_quick_timer],
                            queue=False,
                        )
                        strategy_quick_cancel.click(
                            _safe(service.quick_cancel),
                            inputs=strategy_quick_task_id,
                            outputs=strategy_quick_status,
                            queue=False,
                        )
                        strategy_quick_refresh.click(
                            _safe(service.quick_history), outputs=strategy_quick_backtests, queue=False
                        )
                        strategy_quick_task_id.change(
                            _safe(service.quick_poll),
                            inputs=strategy_quick_task_id,
                            outputs=[strategy_quick_status, strategy_quick_backtests, strategy_quick_timer],
                            queue=False,
                        )
                        strategy_refresh.click(
                            _safe(service.strategies_with_stats),
                            inputs=strategy_keyword,
                            outputs=[strategy_table, strategy_stat_plot],
                        )
                        strategy_detail_btn.click(
                            _safe(service.strategy_detail),
                            inputs=strategy_id,
                            outputs=[
                                strategy_code_view,
                                strategy_meta,
                                strategy_params_view,
                                strategy_interface_view,
                            ],
                        )
                        strategy_compare_versions.click(
                            _safe(service.strategy_version_compare),
                            inputs=strategy_id,
                            outputs=[strategy_compare_status, strategy_compare_table],
                        )
                        strategy_enable.click(
                            _safe(lambda sid: service.set_strategy_status(sid, True)),
                            inputs=strategy_id,
                            outputs=[strategy_status, strategy_table],
                        )
                        strategy_disable.click(
                            _safe(lambda sid: service.set_strategy_status(sid, False)),
                            inputs=strategy_id,
                            outputs=[strategy_status, strategy_table],
                        )
                        strategy_delete.click(
                            _safe(service.delete_strategy),
                            inputs=strategy_id,
                            outputs=[strategy_status, strategy_table],
                        )

                        def _start_quick(*values):
                            return service.quick_start(
                                *values[:8], execution_costs=quick_execution_costs.parse(values[8:])
                            )

                        strategy_quick_run.click(
                            _safe(_start_quick),
                            inputs=[
                                strategy_id,
                                strategy_quick_symbols,
                                strategy_quick_start,
                                strategy_quick_end,
                                strategy_quick_capital,
                                parameter_controls.overrides,
                                strategy_quick_engine,
                                parameter_controls.profile,
                                *quick_execution_costs.inputs,
                            ],
                            outputs=[
                                strategy_quick_status,
                                strategy_quick_task_id,
                                strategy_quick_timer,
                            ],
                        )
                        strategy_quick_task_id.change(
                            _safe(
                                lambda value: (
                                    service.backtest_resolved_parameters(value) if value else (gr.skip(), gr.skip())
                                )
                            ),
                            inputs=strategy_quick_task_id,
                            outputs=[parameter_controls.resolved, parameter_controls.status],
                        )

                    with gr.Tab("预制策略") as preset_strategy_tab:
                        with gr.Row():
                            preset_refresh = gr.Button(
                                "刷新预制策略",
                                variant="primary",
                                elem_classes=["page-refresh-btn"],
                            )
                            preset_strategy = gr.Dropdown(
                                choices=strategy_examples,
                                value=strategy_examples[0][1] if strategy_examples else None,
                                label="预制策略",
                                scale=3,
                            )
                            preset_preview = gr.Button("查看策略", scale=0, min_width=120)
                            preset_import = gr.Button("导入策略库", variant="primary", scale=0, min_width=120)
                        preset_table = _table("预制策略列表", 280)
                        with gr.Row():
                            preset_name = gr.Textbox(label="入库名称（可选，留空用策略标题）")
                            preset_description = gr.Textbox(label="导入描述", lines=1)
                        preset_status = gr.Markdown(elem_classes=["status-strip"])
                        with gr.Tabs():
                            with gr.Tab("策略介绍"):
                                preset_intro = gr.Markdown(elem_classes=["preset-intro"])
                            with gr.Tab("策略代码"):
                                preset_code = gr.Code(language="python", label="策略代码", lines=16)
                            with gr.Tab("超参设置"):
                                gr.Markdown("按 YAML 键值对修改默认超参，点击“导入策略库”时随策略一起保存。")
                                preset_params_yaml = gr.Code(language="yaml", label="默认超参（YAML）", lines=12)
                        with gr.Accordion("接口检查", open=False):
                            preset_meta = gr.Code(language="json", label="接口信息")
                        preset_refresh.click(_safe(service.preset_strategies), outputs=preset_table)
                        preset_detail_inputs = [preset_strategy]
                        preset_detail_outputs = [
                            preset_intro,
                            preset_code,
                            preset_params_yaml,
                            preset_meta,
                        ]
                        preset_preview.click(
                            _safe(service.preset_strategy_detail),
                            inputs=preset_detail_inputs,
                            outputs=preset_detail_outputs,
                        )
                        preset_strategy.change(
                            _safe(service.preset_strategy_detail),
                            inputs=preset_detail_inputs,
                            outputs=preset_detail_outputs,
                        )
                        preset_import.click(
                            _safe(service.import_strategy_example),
                            inputs=[
                                preset_strategy,
                                preset_name,
                                preset_description,
                                preset_params_yaml,
                            ],
                            outputs=[preset_status, strategy_table],
                        )
                        preset_strategy_tab.select(
                            _safe(service.preset_strategy_detail),
                            inputs=preset_detail_inputs,
                            outputs=preset_detail_outputs,
                        )

                    with gr.Tab("上传策略"):
                        with gr.Row():
                            strategy_name = gr.Textbox(label="策略名称")
                            strategy_version = gr.Textbox(value="v1", label="版本")
                            strategy_tags = gr.Textbox(label="标签", placeholder="趋势, 双均线")
                        strategy_description = gr.Textbox(label="策略描述", lines=2)
                        strategy_default_params = gr.Code(value="{}", language="json", label="默认参数")
                        with gr.Accordion("参数 schema 辅助编辑", open=True):
                            with gr.Row():
                                strategy_param_name = gr.Textbox(label="参数名", placeholder="fast_window")
                                strategy_param_type = gr.Dropdown(
                                    STRATEGY_PARAM_TYPE_CHOICES,
                                    value="int",
                                    label="参数类型",
                                )
                                strategy_param_default = gr.Textbox(label="默认值", placeholder="5")
                                strategy_param_description = gr.Textbox(label="说明", lines=1)
                            with gr.Row():
                                strategy_param_add = gr.Button("追加参数字段", variant="primary")
                                strategy_param_extract = gr.Button("从源码提取参数")
                                strategy_param_preview = gr.Button("刷新参数预览")
                            strategy_param_status = gr.Markdown(elem_classes=["status-strip"])
                            strategy_param_table = _table("参数 schema 预览", 220)
                        strategy_source = gr.Code(language="python", label="策略代码", lines=18)
                        strategy_file = gr.File(label="Python 文件", file_types=[".py"], type="filepath")
                        strategy_create = gr.Button("保存策略", variant="primary")
                        strategy_create_status = gr.Markdown(elem_classes=["status-strip"])
                        strategy_param_add.click(
                            _safe(service.strategy_param_schema_add),
                            inputs=[
                                strategy_default_params,
                                strategy_param_name,
                                strategy_param_type,
                                strategy_param_default,
                                strategy_param_description,
                            ],
                            outputs=[
                                strategy_param_status,
                                strategy_default_params,
                                strategy_param_table,
                            ],
                        )
                        strategy_param_extract.click(
                            _safe(service.strategy_param_schema_extract),
                            inputs=[strategy_source, strategy_file],
                            outputs=[
                                strategy_param_status,
                                strategy_default_params,
                                strategy_param_table,
                            ],
                        )
                        strategy_param_preview.click(
                            _safe(service.strategy_param_schema_preview),
                            inputs=strategy_default_params,
                            outputs=[
                                strategy_param_status,
                                strategy_default_params,
                                strategy_param_table,
                            ],
                        )
                        strategy_create.click(
                            _safe(service.create_strategy),
                            inputs=[
                                strategy_name,
                                strategy_version,
                                strategy_description,
                                strategy_tags,
                                strategy_default_params,
                                strategy_source,
                                strategy_file,
                            ],
                            outputs=[strategy_create_status, strategy_table],
                        )
                        with gr.Accordion("egs 示例策略", open=True):
                            with gr.Row():
                                strategy_example = gr.Dropdown(
                                    choices=strategy_examples,
                                    value=strategy_examples[0][1] if strategy_examples else None,
                                    label="示例文件",
                                    scale=3,
                                )
                                strategy_example_name = gr.Textbox(label="入库名称（可选）")
                                strategy_example_preview = gr.Button("查看示例", scale=0, min_width=120)
                                strategy_example_import = gr.Button(
                                    "导入示例", variant="primary", scale=0, min_width=120
                                )
                            strategy_example_description = gr.Textbox(label="导入描述", lines=2)
                            strategy_example_status = gr.Markdown(elem_classes=["status-strip"])
                            strategy_example_meta = gr.Code(language="json", label="示例接口信息")
                            strategy_example_code = gr.Code(language="python", label="示例代码", lines=14)
                            strategy_example_preview.click(
                                _safe(service.strategy_example_detail),
                                inputs=strategy_example,
                                outputs=[strategy_example_code, strategy_example_meta],
                            )
                            strategy_example_import.click(
                                _safe(service.import_strategy_example),
                                inputs=[
                                    strategy_example,
                                    strategy_example_name,
                                    strategy_example_description,
                                ],
                                outputs=[strategy_example_status, strategy_table],
                            )

                    with gr.Tab("CLI 工作台"):
                        with gr.Row():
                            cli_type = gr.Dropdown(CLI_TYPE_CHOICES, value="trae", label="CLI")
                            cli_requirement = gr.Textbox(label="策略需求", lines=5, scale=4)
                        cli_build = gr.Button("生成策略", variant="primary")
                        cli_session = gr.Code(language="json", label="会话状态")
                        cli_logs = gr.Textbox(label="执行日志", lines=8)
                        cli_artifacts = _table("生成产物", 200)
                        with gr.Accordion("CLI 会话列表与失败重试", open=True):
                            cli_sessions_refresh = gr.Button(
                                "刷新会话列表",
                                variant="primary",
                                elem_classes=["page-refresh-btn"],
                            )
                            cli_sessions_table = _table("CLI 会话列表", 260)
                            cli_retry = gr.Button("重试会话")
                        cli_build.click(
                            _safe(service.cli_build_with_sessions),
                            inputs=[cli_type, cli_requirement],
                            outputs=[cli_session, cli_logs, cli_artifacts, cli_sessions_table],
                        )
                        cli_sessions_refresh.click(
                            _safe(service.cli_sessions),
                            outputs=cli_sessions_table,
                            queue=False,
                        )
                        with gr.Accordion("导入产物", open=False):
                            with gr.Row():
                                cli_session_id = gr.Number(label="会话 ID", precision=0)
                                cli_artifact_path = gr.Textbox(label="产物路径")
                                cli_strategy_name = gr.Textbox(label="策略名称")
                            cli_strategy_description = gr.Textbox(label="策略描述")
                            cli_import = gr.Button("导入策略库", variant="primary")
                            cli_import_status = gr.Markdown(elem_classes=["status-strip"])
                            cli_import.click(
                                _safe(service.import_cli_artifact),
                                inputs=[
                                    cli_session_id,
                                    cli_artifact_path,
                                    cli_strategy_name,
                                    cli_strategy_description,
                                ],
                                outputs=[cli_import_status, strategy_table],
                            )
                        cli_retry.click(
                            _safe(service.cli_retry),
                            inputs=cli_session_id,
                            outputs=[cli_session, cli_logs, cli_artifacts, cli_sessions_table],
                        )
