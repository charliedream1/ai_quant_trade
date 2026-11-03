"""One report browser; generation remains in the explicit task workspaces."""

import gradio as gr

from ..common.callbacks import safe
from ..common.navigation import navigation_config, workspace_link
from .research import render_model_reports


def render_report_library(service, tab=None):
    gr.Markdown("### 报告库\n\n统一浏览历史模板与Skill报告，来源、状态和实际过程分别保留。")
    gr.HTML(workspace_link("生成市场复盘 / 个股Skill报告", "ai", "insights"))
    config = navigation_config()["report_library"]
    loaded = gr.State(False)
    with gr.Row():
        source = gr.Dropdown(config["sources"], value="all", label="报告来源", elem_id="report-source")
        state = gr.Dropdown(config["statuses"], value="all", label="执行状态", elem_id="report-status")
        keyword = gr.Textbox(label="标题或任务关键词", elem_id="report-keyword")
        refresh = gr.Button("刷新报告库", variant="primary")
    catalog = gr.Dataframe(
        label="报告目录",
        max_height=config["catalog_height"],
        interactive=False,
        wrap=True,
        elem_classes=["data-table"],
        buttons=["fullscreen", "copy"],
    )
    selected = gr.Dropdown([], label="选择报告", interactive=True, elem_id="report-selected")
    open_report = gr.Button("打开报告")
    status = gr.Markdown(elem_classes=["status-strip"])
    process = gr.Textbox(label="实际过程或来源说明", lines=5, interactive=False)
    preview = gr.HTML()
    download = gr.File(label="下载HTML报告", interactive=False)
    inputs = [selected, source, state, keyword]

    def reload_catalog(*values):
        return *service.report_library_list(*values), True

    def first_visit(already_loaded, *values):
        return (gr.skip(), gr.skip(), True) if already_loaded else reload_catalog(*values)

    refresh.click(safe(reload_catalog), inputs=inputs, outputs=[catalog, selected, loaded], queue=False)
    for control in (source, state, keyword):
        control.change(safe(reload_catalog), inputs=inputs, outputs=[catalog, selected, loaded], queue=False)
    if tab is not None:
        tab.select(safe(first_visit), inputs=[loaded, *inputs], outputs=[catalog, selected, loaded], queue=False)
    open_report.click(safe(service.report_library_open), inputs=selected, outputs=[status, process, preview, download])
    with gr.Accordion("旧版模板报告（演示兼容）", open=False):
        render_model_reports(service)
