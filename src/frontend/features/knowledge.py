"""Gradio UI for the knowledge domain."""

from __future__ import annotations

from typing import Any

import gradio as gr

from ..common.callbacks import safe as _safe
from ..common.components import table as _table
from ..handlers import DomainHandler
from .knowledge_ingest import render_ingestion
from .rag_chat import render_rag_chat
from .report_library import render_report_library
from .research import render_paper_search, render_report_search


def render_knowledge(service: DomainHandler) -> None:
    with gr.Tab("知识与资料"):
        with gr.Tabs(elem_classes=["module-tabs"]):
            with gr.Tab("知识库问答"):
                render_rag_chat(service)
            with gr.Tab("知识库入库"):
                target_library, chunk_size = render_ingestion(service)

                with gr.Accordion("远程知识源（高级）", open=False):
                    remote_status = gr.Markdown(elem_classes=["status-strip"])
                    remote_sources = _table("远程知识源", 340)
                    with gr.Row():
                        remote_refresh = gr.Button("刷新", elem_classes=["page-refresh-btn"])
                        remote_id = gr.Number(label="知识源 ID", precision=0)
                        remote_test = gr.Button("测试连接")
                        remote_folder = gr.Textbox(label="远程目录")
                        remote_keyword = gr.Textbox(label="远程关键词")
                        remote_list_docs = gr.Button("列出文档")
                    with gr.Accordion("新建知识源", open=True):
                        with gr.Row():
                            remote_name = gr.Textbox(label="名称")
                            remote_type = gr.Dropdown(["feishu", "ima", "custom"], value="feishu", label="类型")
                        remote_config = gr.Code(value="{}", language="json", label="连接配置")
                        remote_create = gr.Button("保存知识源", variant="primary")
                    remote_docs = _table("远程文档", 320)
                    with gr.Row():
                        remote_doc_id = gr.Textbox(label="远程文档 ID")
                        remote_target_category = gr.Number(value=0, label="导入分类 ID", precision=0)
                        remote_sync_limit = gr.Number(value=20, label="批量上限", precision=0)
                        remote_pull = gr.Button("拉取入库", variant="primary")
                        remote_sync = gr.Button("批量同步入库")
                    remote_refresh.click(_safe(service.remote_sources), outputs=remote_sources)
                    remote_create.click(
                        _safe(service.create_remote_source),
                        inputs=[remote_name, remote_type, remote_config],
                        outputs=[remote_status, remote_sources],
                    )
                    remote_test.click(_safe(service.test_remote_source), inputs=remote_id, outputs=remote_status)
                    remote_list_docs.click(
                        _safe(service.remote_documents),
                        inputs=[remote_id, remote_folder, remote_keyword],
                        outputs=remote_docs,
                    )
                    remote_pull.click(
                        _safe(service.pull_remote_document),
                        inputs=[
                            remote_id,
                            remote_doc_id,
                            remote_target_category,
                            remote_folder,
                            target_library,
                            chunk_size,
                        ],
                        outputs=[remote_status, remote_docs],
                    )
                    remote_sync.click(
                        _safe(service.sync_remote_documents),
                        inputs=[
                            remote_id,
                            remote_folder,
                            remote_keyword,
                            remote_target_category,
                            remote_sync_limit,
                            target_library,
                            chunk_size,
                        ],
                        outputs=[remote_status, remote_docs],
                    )

            with gr.Tab("研报与论文"):
                with gr.Tabs():
                    with gr.Tab("研报检索"):
                        render_report_search(service)
                    with gr.Tab("论文检索"):
                        render_paper_search(service)
            with gr.Tab("报告库") as report_tab:
                render_report_library(service, report_tab)

            with gr.Tab("系统资料"):
                learning_tree = service.learning_tree()
                first_chapter_id = (
                    learning_tree[0]["chapters"][0][1] if learning_tree and learning_tree[0].get("chapters") else None
                )
                with gr.Row():
                    with gr.Column(scale=1, min_width=260, elem_classes=["learning-tree"]):
                        learning_refresh = gr.Button(
                            "刷新当前章节", variant="primary", elem_classes=["page-refresh-btn"]
                        )
                        learning_chapter_state = gr.State(first_chapter_id)
                        learning_radios: list[gr.Radio] = []
                        for group_index, group in enumerate(learning_tree):
                            with gr.Accordion(group["category"], open=(group_index == 0)):
                                chapter_radio = gr.Radio(
                                    choices=group["chapters"],
                                    value=None,
                                    label=" ",
                                    elem_classes=["learning-chapter-radio"],
                                )
                                learning_radios.append(chapter_radio)
                    with gr.Column(scale=2):
                        learning_detail = gr.Markdown(
                            value="选择左侧章节或点击“刷新当前章节”后查看正文。",
                            elem_classes=["learning-reader"],
                        )

                def _bind_chapter_select(current: gr.Radio):
                    def _select_learning_chapter(chapter_id: Any) -> tuple[Any, ...]:
                        content = service.learning_detail(chapter_id) if chapter_id else ""
                        updates: list[Any] = [chapter_id, content]
                        updates.extend(
                            gr.update() if radio is current else gr.update(value=None) for radio in learning_radios
                        )
                        return tuple(updates)

                    return _select_learning_chapter

                for learning_radio in learning_radios:
                    learning_radio.input(
                        _safe(_bind_chapter_select(learning_radio)),
                        inputs=learning_radio,
                        outputs=[learning_chapter_state, learning_detail, *learning_radios],
                        queue=False,
                    )
                learning_refresh.click(
                    _safe(lambda chapter_id: service.learning_detail(chapter_id, force_refresh=True)),
                    inputs=learning_chapter_state,
                    outputs=learning_detail,
                    queue=False,
                )
