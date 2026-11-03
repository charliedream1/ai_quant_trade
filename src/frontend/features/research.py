"""Gradio UI for the research domain."""

from __future__ import annotations

import gradio as gr
from src.knowledge.config import knowledge_config
from src.knowledge.files import KnowledgeFiles

from ..common.callbacks import safe as _safe
from ..common.components import plot as _plot
from ..common.components import table as _table
from ..handlers import DomainHandler


def render_research(service: DomainHandler) -> None:
    """Compatibility renderer uses the same library components as the canonical page."""
    with gr.Tab("研报论文"):
        with gr.Tabs(elem_classes=["module-tabs"]):
            with gr.Tab("研报与模型分析"):
                with gr.Tabs():
                    with gr.Tab("研报检索"):
                        render_report_search(service)
                    with gr.Tab("模型报告"):
                        render_model_reports(service)
            with gr.Tab("论文检索"):
                render_paper_search(service)


def render_report_search(service: DomainHandler) -> None:
    with gr.Row():
        report_keyword = gr.Textbox(label="关键词")
        report_symbol = gr.Textbox(label="股票代码/名称")
        report_search = gr.Button("检索", variant="primary", elem_classes=["page-refresh-btn"])
    report_table = _table(
        "研报",
        480,
        elem_classes=["wide-summary-table"],
        datatype=[
            "number",
            "str",
            "str",
            "str",
            "str",
            "str",
            "str",
            "str",
            "markdown",
        ],
    )
    with gr.Row():
        report_detail_id = gr.Number(label="研报 ID", precision=0)
        report_detail_btn = gr.Button("查看详情")
        report_save = gr.Button("保存研报")
        report_library = gr.Dropdown(
            KnowledgeFiles().libraries(),
            value=knowledge_config()["default_library"],
            label="研报目标知识库",
            allow_custom_value=True,
        )
        report_import = gr.Button("下载研报并入库", variant="primary")
    report_status = gr.Markdown(elem_classes=["status-strip"])
    report_import.click(
        _safe(lambda identifier, library: service.download_research_to_kb("report", identifier, library)),
        inputs=[report_detail_id, report_library],
        outputs=report_status,
    )
    report_dist_plot = _plot(
        label="研报分布",
        elem_classes=["chart-panel"],
    )
    report_detail = gr.Markdown(label="研报详情")
    report_search.click(
        _safe(lambda keyword, symbol: service.research_reports_page(keyword, symbol, force_refresh=True)),
        inputs=[report_keyword, report_symbol],
        outputs=[report_status, report_table, report_dist_plot],
        queue=False,
    )
    report_detail_btn.click(
        _safe(service.research_report_detail),
        inputs=report_detail_id,
        outputs=report_detail,
    )
    report_save.click(
        _safe(service.save_research_report),
        inputs=report_detail_id,
        outputs=report_status,
    )


def render_model_reports(service: DomainHandler) -> None:
    with gr.Row():
        model_report_type = gr.Dropdown(["daily", "weekly", "topic"], value="daily", label="报告类型")
        model_report_topic = gr.Textbox(value="市场综述", label="主题")
        model_report_llm = gr.Checkbox(value=True, label="使用 LLM")
        model_report_create = gr.Button("生成报告", variant="primary")
        model_report_refresh = gr.Button("刷新列表", elem_classes=["page-refresh-btn"])
    model_report_status = gr.Markdown(elem_classes=["status-strip"])
    model_report_table = _table("报告列表", 320)
    model_report_content = gr.Markdown(label="报告内容")
    with gr.Row():
        model_report_id = gr.Number(label="报告 ID", precision=0)
        model_report_detail_btn = gr.Button("查看报告")
    model_report_create.click(
        _safe(service.model_reports),
        inputs=[model_report_type, model_report_topic, model_report_llm],
        outputs=[model_report_status, model_report_table, model_report_content],
    )
    model_report_refresh.click(_safe(service.list_model_reports), outputs=model_report_table)
    model_report_detail_btn.click(
        _safe(service.model_report_detail),
        inputs=model_report_id,
        outputs=model_report_content,
    )


def render_paper_search(service: DomainHandler) -> None:
    with gr.Row():
        paper_keyword = gr.Textbox(label="关键词")
        paper_source = gr.Textbox(label="来源")
        paper_year_from = gr.Number(label="起始年份", precision=0)
        paper_year_to = gr.Number(label="结束年份", precision=0)
        paper_search = gr.Button("检索", variant="primary", elem_classes=["page-refresh-btn"])
    paper_table = _table(
        "论文",
        430,
        elem_classes=["wide-summary-table"],
        datatype=["number", "str", "str", "str", "str", "str", "markdown", "bool", "str"],
    )
    with gr.Row():
        paper_id = gr.Number(label="论文 ID", precision=0)
        paper_note = gr.Textbox(label="收藏备注")
        paper_detail_btn = gr.Button("查看详情")
        paper_favorite = gr.Button("收藏")
        paper_unfavorite = gr.Button("取消收藏")
        paper_import = gr.Button("导入知识库")
        paper_library = gr.Dropdown(
            KnowledgeFiles().libraries(),
            value=knowledge_config()["default_library"],
            label="论文目标知识库",
            allow_custom_value=True,
        )
        paper_download = gr.Button("下载论文并入库", variant="primary")
    paper_status = gr.Markdown(elem_classes=["status-strip"])
    paper_download.click(
        _safe(lambda identifier, library: service.download_research_to_kb("paper", identifier, library)),
        inputs=[paper_id, paper_library],
        outputs=paper_status,
    )
    paper_dist_plot = _plot(
        label="论文分布",
        elem_classes=["chart-panel"],
    )
    paper_detail = gr.Markdown(label="论文详情")
    paper_search.click(
        _safe(
            lambda keyword, source, year_from, year_to: service.paper_search_page(
                keyword, source, year_from, year_to, refresh=True
            )
        ),
        inputs=[paper_keyword, paper_source, paper_year_from, paper_year_to],
        outputs=[paper_status, paper_table, paper_dist_plot],
    )
    paper_detail_btn.click(_safe(service.paper_detail), inputs=paper_id, outputs=paper_detail)
    paper_favorite.click(
        _safe(lambda pid, note: service.paper_favorite(pid, note, True)),
        inputs=[paper_id, paper_note],
        outputs=paper_status,
    )
    paper_unfavorite.click(
        _safe(lambda pid, note: service.paper_favorite(pid, note, False)),
        inputs=[paper_id, paper_note],
        outputs=paper_status,
    )
    paper_import.click(
        _safe(service.import_paper_to_kb),
        inputs=paper_id,
        outputs=paper_status,
    )
