"""Gradio UI for the admin domain."""

from __future__ import annotations

import gradio as gr
from src.help_docs import help_docs_iframe_html

from ..common.callbacks import safe as _safe
from ..common.components import plot as _plot
from ..common.components import table as _table
from ..constants import DEFAULT_JOB_PARAMS, JOB_TYPE_OPTIONS
from ..handlers import DomainHandler


def render_admin(service: DomainHandler) -> None:
    with gr.Tab("帮助"):
        with gr.Tabs(elem_classes=["module-tabs"]):
            with gr.Tab("帮助文档"):
                gr.HTML(help_docs_iframe_html(), elem_id="help-docs-panel")

            with gr.Tab("定时任务"):
                job_status = gr.Code(language="json", label="操作结果")
                with gr.Row():
                    job_refresh = gr.Button("刷新任务", variant="primary", elem_classes=["page-refresh-btn"])
                    job_id = gr.Number(label="任务 ID", precision=0)
                    job_history_refresh = gr.Button("查看历史")
                    job_trigger = gr.Button("立即执行")
                    job_enable = gr.Button("启用")
                    job_disable = gr.Button("停用")
                    job_delete = gr.Button("删除", variant="stop")
                job_table = _table("任务列表", 360)
                job_history = _table("执行历史", 300)
                with gr.Accordion("新建任务", open=True):
                    with gr.Row():
                        job_name = gr.Textbox(label="任务名称")
                        job_type = gr.Dropdown(
                            JOB_TYPE_OPTIONS,
                            value="news_fetch",
                            allow_custom_value=True,
                            label="任务类型",
                        )
                        job_cron = gr.Textbox(value="*/10 * * * *", label="Cron")
                        job_enabled = gr.Checkbox(value=True, label="启用")
                    job_params = gr.Code(value=DEFAULT_JOB_PARAMS, language="json", label="任务参数")
                    job_create = gr.Button("保存任务", variant="primary")
                job_refresh.click(_safe(service.jobs), outputs=job_table)
                job_history_refresh.click(_safe(service.job_histories), inputs=job_id, outputs=job_history)
                job_create.click(
                    _safe(service.create_job),
                    inputs=[job_name, job_type, job_cron, job_params, job_enabled],
                    outputs=[job_status, job_table],
                )
                for button, action in (
                    (job_trigger, "trigger"),
                    (job_enable, "enable"),
                    (job_disable, "disable"),
                    (job_delete, "delete"),
                ):
                    button.click(
                        _safe(lambda value, selected=action: service.job_action(value, selected)),
                        inputs=job_id,
                        outputs=[job_status, job_table, job_history],
                    )

            with gr.Tab("系统配置"):
                with gr.Tabs():
                    with gr.Tab("系统设置"):
                        initial_settings = service.settings()
                        settings_status = gr.Markdown(
                            value="全局设置保存到 `egs/config.yaml`；环境变量优先级更高，路径类修改建议重启后生效。",
                            elem_classes=["status-strip"],
                        )
                        settings_runtime = gr.Markdown(
                            value=service.system_runtime_status(),
                            elem_classes=["status-strip"],
                        )
                        with gr.Accordion("数据与存储", open=True):
                            with gr.Row():
                                settings_data_dir = gr.Textbox(value=initial_settings[0], label="数据根目录")
                                settings_db_path = gr.Textbox(value=initial_settings[1], label="SQLite 主库路径")
                            with gr.Row():
                                settings_document_dir = gr.Textbox(
                                    value=initial_settings[2],
                                    label="文档存储目录",
                                )
                                settings_parquet_dir = gr.Textbox(
                                    value=initial_settings[3],
                                    label="Parquet 行情湖目录",
                                )
                                settings_duckdb_path = gr.Textbox(
                                    value=initial_settings[4],
                                    label="DuckDB 查询库路径",
                                )
                        with gr.Accordion("网络与缓存", open=True):
                            with gr.Row():
                                settings_timeout = gr.Number(
                                    value=initial_settings[5],
                                    label="请求超时秒数",
                                    precision=2,
                                )
                                settings_retries = gr.Number(
                                    value=initial_settings[6],
                                    label="HTTP 重试次数",
                                    precision=0,
                                )
                                settings_cache_ttl = gr.Number(
                                    value=initial_settings[7],
                                    label="行情缓存 TTL 秒数",
                                    precision=0,
                                )
                        with gr.Accordion("调度与日历", open=True):
                            with gr.Row():
                                settings_calendar_path = gr.Textbox(
                                    value=initial_settings[8],
                                    label="交易日历路径",
                                )
                                settings_executors_path = gr.Textbox(
                                    value=initial_settings[9],
                                    label="自定义执行体白名单",
                                )
                        with gr.Row():
                            settings_refresh = gr.Button("刷新", elem_classes=["page-refresh-btn"])
                            settings_save = gr.Button("保存设置", variant="primary")
                        settings_source_table = _table("配置来源", 360, value=initial_settings[10])
                        settings_storage_table = _table("存储选型", 320, value=initial_settings[11])
                        settings_lake_table = _table("行情湖状态", 320, value=initial_settings[12])
                        settings_inputs = [
                            settings_data_dir,
                            settings_db_path,
                            settings_document_dir,
                            settings_parquet_dir,
                            settings_duckdb_path,
                            settings_timeout,
                            settings_retries,
                            settings_cache_ttl,
                            settings_calendar_path,
                            settings_executors_path,
                        ]
                        settings_outputs = [
                            *settings_inputs,
                            settings_source_table,
                            settings_storage_table,
                            settings_lake_table,
                        ]
                        settings_refresh.click(
                            _safe(lambda: (service.system_runtime_status(), *service.settings())),
                            outputs=[settings_runtime, *settings_outputs],
                        )

                        settings_save.click(
                            _safe(service.save_settings_form),
                            inputs=settings_inputs,
                            outputs=[settings_status, *settings_outputs],
                        )

                    with gr.Tab("环境变量"):
                        environment_status = gr.Markdown(elem_classes=["status-strip"])
                        environment_table = _table("已导入变量", 320)
                        with gr.Row():
                            environment_file = gr.File(
                                label="环境变量文件",
                                file_types=[".env", ".llm_env", ".secrets", ".txt"],
                                type="filepath",
                            )
                            environment_overwrite = gr.Checkbox(value=False, label="覆盖同名变量")
                        with gr.Row():
                            environment_refresh = gr.Button("刷新", elem_classes=["page-refresh-btn"])
                            environment_import = gr.Button("导入", variant="primary")
                        with gr.Row():
                            environment_name = gr.Textbox(
                                label="变量名",
                                placeholder="如 OPENAI_API_KEY",
                            )
                            environment_check = gr.Button("校验变量")
                            environment_delete = gr.Button("删除变量", variant="stop")
                        environment_refresh.click(
                            _safe(service.environment_variables),
                            outputs=environment_table,
                            queue=False,
                        )
                        environment_import.click(
                            _safe(service.import_environment),
                            inputs=[environment_file, environment_overwrite],
                            outputs=[environment_status, environment_table],
                        )
                        environment_check.click(
                            _safe(service.check_environment_variable),
                            inputs=environment_name,
                            outputs=[environment_status, environment_table],
                            queue=False,
                        )
                        environment_delete.click(
                            _safe(service.delete_environment_variable),
                            inputs=environment_name,
                            outputs=[environment_status, environment_table],
                        )

                    with gr.Tab("模型管理"):
                        model_status = gr.Code(language="json", label="操作结果")
                        model_table = _table("模型配置", 340)
                        model_stat_plot = _plot(
                            label="模型分布",
                            elem_classes=["chart-panel"],
                        )
                        with gr.Row():
                            model_refresh = gr.Button("刷新", elem_classes=["page-refresh-btn"])
                            model_id = gr.Number(label="模型 ID", precision=0)
                            model_load = gr.Button("载入配置")
                            model_level_action = gr.Radio(["fast", "deep"], value="fast", label="默认层级")
                            model_test = gr.Button("测试")
                            model_default = gr.Button("设为默认")
                            model_enable = gr.Button("启用")
                            model_disable = gr.Button("停用")
                            model_delete = gr.Button("删除", variant="stop")
                        with gr.Accordion("新建模型", open=True):
                            with gr.Row():
                                model_name = gr.Textbox(label="配置名称")
                                model_base_url = gr.Textbox(value="https://api.openai.com/v1", label="Base URL")
                                model_model_name = gr.Textbox(label="模型名称")
                            with gr.Row():
                                model_api_key_env = gr.Textbox(label="API Key 环境变量", placeholder="OPENAI_API_KEY")
                                model_api_key = gr.Textbox(label="API Key（安全写入 .llm_env）", type="password")
                                model_level = gr.Radio(["fast", "deep"], value="fast", label="层级")
                                model_purpose = gr.Textbox(label="用途")
                            with gr.Row():
                                model_temperature = gr.Slider(0, 2, value=0.2, step=0.05, label="Temperature")
                                model_max_tokens = gr.Number(value=1200, precision=0, label="Max Tokens")
                                model_timeout = gr.Slider(3, 300, value=60, step=1, label="超时（秒）")
                            model_system_prompt = gr.Textbox(label="系统提示词", lines=4)
                            with gr.Row():
                                model_create = gr.Button("新建模型", variant="primary")
                                model_update = gr.Button("更新所选模型")
                        model_refresh.click(_safe(service.models_with_stats), outputs=[model_table, model_stat_plot])
                        model_inputs = [
                            model_name,
                            model_base_url,
                            model_api_key,
                            model_api_key_env,
                            model_model_name,
                            model_level,
                            model_purpose,
                            model_temperature,
                            model_max_tokens,
                            model_timeout,
                            model_system_prompt,
                        ]
                        model_create.click(
                            _safe(service.create_model),
                            inputs=model_inputs,
                            outputs=[model_status, model_table],
                        )
                        model_load.click(
                            _safe(service.model_form),
                            inputs=model_id,
                            outputs=model_inputs,
                            queue=False,
                        )
                        model_update.click(
                            _safe(service.update_model),
                            inputs=[model_id, *model_inputs],
                            outputs=[model_status, model_table],
                        )
                        for button, action in (
                            (model_test, "test"),
                            (model_default, "default"),
                            (model_enable, "enable"),
                            (model_disable, "disable"),
                            (model_delete, "delete"),
                        ):
                            button.click(
                                _safe(
                                    lambda value, level, selected=action: service.model_action(value, selected, level)
                                ),
                                inputs=[model_id, model_level_action],
                                outputs=[model_status, model_table],
                            )

                    with gr.Tab("MCP 服务"):
                        mcp_status = gr.Code(language="json", label="操作结果")
                        mcp_table = _table("MCP 服务", 340)
                        with gr.Row():
                            mcp_refresh = gr.Button("刷新", elem_classes=["page-refresh-btn"])
                            mcp_id = gr.Number(label="服务 ID", precision=0)
                            mcp_test = gr.Button("测试")
                            mcp_enable = gr.Button("启用")
                            mcp_disable = gr.Button("停用")
                            mcp_delete = gr.Button("删除", variant="stop")
                        with gr.Accordion("新建 MCP 服务", open=True):
                            with gr.Row():
                                mcp_name = gr.Textbox(label="名称")
                                mcp_type = gr.Textbox(value="自定义", label="服务类型")
                                mcp_transport = gr.Dropdown(["stdio", "http", "sse"], value="stdio", label="传输方式")
                                mcp_enabled = gr.Checkbox(value=True, label="启用")
                            mcp_config = gr.Code(value="{}", language="json", label="连接参数")
                            mcp_create = gr.Button("保存 MCP", variant="primary")
                        with gr.Accordion("调用 MCP 工具", open=False):
                            with gr.Row():
                                mcp_tool_name = gr.Textbox(label="工具名")
                                mcp_tool_args = gr.Code(
                                    value="{}",
                                    language="json",
                                    label="工具参数",
                                )
                                mcp_call_tool = gr.Button("调用工具", variant="primary")
                        mcp_refresh.click(_safe(service.mcp_servers), outputs=mcp_table)
                        mcp_create.click(
                            _safe(service.create_mcp),
                            inputs=[mcp_name, mcp_type, mcp_transport, mcp_config, mcp_enabled],
                            outputs=[mcp_status, mcp_table],
                        )
                        mcp_call_tool.click(
                            _safe(service.mcp_call),
                            inputs=[mcp_id, mcp_tool_name, mcp_tool_args],
                            outputs=[mcp_status, mcp_table],
                        )
                        for button, action in (
                            (mcp_test, "test"),
                            (mcp_enable, "enable"),
                            (mcp_disable, "disable"),
                            (mcp_delete, "delete"),
                        ):
                            button.click(
                                _safe(lambda value, selected=action: service.mcp_action(value, selected)),
                                inputs=mcp_id,
                                outputs=[mcp_status, mcp_table],
                            )

                    with gr.Tab("Skill 配置"):
                        with gr.Accordion("登记Skill", open=False):
                            with gr.Row():
                                skill_name = gr.Textbox(label="Skill 名称")
                                skill_source = gr.Textbox(label="来源")
                            skill_description = gr.Textbox(label="说明", lines=2)
                            skill_schema = gr.Code(value="{}", language="json", label="参数schema")
                            skill_defaults = gr.Code(value="{}", language="json", label="默认参数")
                            skill_create = gr.Button("登记Skill", variant="primary")
                        skill_status = gr.Code(language="json", label="操作结果")
                        skill_table = _table("Skill 列表", 380)
                        with gr.Row():
                            skill_refresh = gr.Button("刷新", elem_classes=["page-refresh-btn"])
                            skill_id = gr.Number(label="Skill ID", precision=0)
                            skill_enable = gr.Button("启用")
                            skill_disable = gr.Button("停用")
                            skill_run = gr.Button("运行", variant="primary")
                        skill_params = gr.Code(value="{}", language="json", label="Skill 参数")
                        skill_save_params = gr.Button("保存参数", variant="primary")
                        skill_refresh.click(_safe(service.skills), outputs=skill_table)
                        skill_create.click(
                            _safe(service.create_skill),
                            inputs=[skill_name, skill_description, skill_source, skill_schema, skill_defaults],
                            outputs=[skill_status, skill_table],
                        )
                        skill_enable.click(
                            _safe(lambda value, params: service.skill_action(value, "enable", params)),
                            inputs=[skill_id, skill_params],
                            outputs=[skill_status, skill_table],
                        )
                        skill_disable.click(
                            _safe(lambda value, params: service.skill_action(value, "disable", params)),
                            inputs=[skill_id, skill_params],
                            outputs=[skill_status, skill_table],
                        )
                        skill_run.click(
                            _safe(lambda value, params: service.skill_action(value, "run", params)),
                            inputs=[skill_id, skill_params],
                            outputs=[skill_status, skill_table],
                        )
                        skill_save_params.click(
                            _safe(lambda value, params: service.skill_action(value, "params", params)),
                            inputs=[skill_id, skill_params],
                            outputs=[skill_status, skill_table],
                        )
