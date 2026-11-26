"""Named library ingestion, shared by file upload and URL downloads."""

import gradio as gr
import pandas as pd

from src.knowledge.config import knowledge_config
from src.knowledge.research_classification import policy as research_policy
from src.knowledge.research_classification import topic_choices
from src.knowledge.research_metadata import documents as research_documents
from src.knowledge.research_metadata import facets, reclassify

from ..common.callbacks import safe
from ..common.components import table
from .file_reader import knowledge_reader


def render_ingestion(service):
    policy = knowledge_config()
    with gr.Row():
        library = gr.Dropdown(
            service.kb_libraries(),
            value=policy["default_library"],
            label="目标知识库",
            allow_custom_value=True,
            elem_id="kb-ingest-library",
        )
        create = gr.Button("创建知识库")
        refresh = gr.Button("刷新知识库")
    size = gr.Number(
        value=policy["chunk_chars"],
        minimum=policy["minimum_chunk_chars"],
        maximum=policy["maximum_chunk_chars"],
        precision=0,
        label="分块长度上限（字符，优先按Markdown标题）",
    )
    files = gr.File(label="添加文档", file_count="multiple", file_types=policy["extensions"], elem_id="kb-ingest-files")
    upload = gr.Button("文件入库", variant="primary")
    with gr.Row():
        url = gr.Textbox(label="网页或文档 URL", placeholder="https://…")
        download = gr.Button("下载并入库")
    status = gr.Markdown(elem_classes=["status-strip"], elem_id="kb-ingest-status")
    with gr.Row():
        year = gr.Dropdown([], label="发表年份")
        institution = gr.Dropdown([], label="机构")
        choices = [(group["label"][0], f"group:{key}") for key, group in research_policy()["categories"].items()]
        topic = gr.Dropdown(
            [*choices, *[(label, code or "review") for label, code in topic_choices()]], label="研究主题"
        )
        doc_type = gr.Dropdown(["研报", "论文"], label="文档类型")
        page = gr.Number(value=1, minimum=1, precision=0, label="页码")
        browse = gr.Button("筛选文档")
    documents = table("当前知识库文档", 350, elem_id="kb-research-documents")
    with gr.Row():
        doc_id = gr.Number(label="文档 ID", precision=0)
        read = gr.Button("预览原件")
        corrected = gr.Dropdown(topic_choices(), label="调整研究主题")
        apply_category = gr.Button("保存分类")
    reader = gr.HTML(elem_id="kb-file-reader")
    create.click(safe(service.kb_create_library), inputs=library, outputs=[status, library])
    refresh.click(safe(service.kb_library_choices), outputs=library)
    filters = [library, year, institution, topic, doc_type, page]

    def read_docs(name, published, org, category, kind, number):
        rows = research_documents(name, published, org, category, kind, number)
        return pd.DataFrame(
            rows,
            columns=[
                "doc_id",
                "title",
                "doc_type",
                "library_name",
                "published_year",
                "institutions",
                "category",
                "topic",
                "source",
                "updated_at",
            ],
        )

    def refresh_facets(name):
        years, institutions, _ = facets(name)
        return (
            gr.update(
                choices=[(str(row["year"]), str(row["year"])) for row in years] + [("未提供年份", "unknown")],
                value=None,
            ),
            gr.update(
                choices=[(row["name"], row["normalized"]) for row in institutions] + [("未提供机构", "unknown")],
                value=None,
            ),
            gr.update(value=None),
            gr.update(value=None),
            1,
            read_docs(name, None, None, None, None, 1),
        )

    for action in (refresh.click, library.change):
        action(safe(refresh_facets), inputs=library, outputs=[year, institution, topic, doc_type, page, documents])
    browse.click(safe(read_docs), inputs=filters, outputs=documents)

    def select_doc(frame, evt: gr.SelectData):
        return int(frame.iloc[int(evt.index[0])]["doc_id"])

    documents.select(select_doc, inputs=documents, outputs=doc_id)

    def change_category(name, identifier, value, *selected):
        reclassify(name, identifier, value or "")
        return "分类已更新", read_docs(name, *selected)

    apply_category.click(
        safe(change_category), inputs=[library, doc_id, corrected, *filters[1:]], outputs=[status, documents]
    )
    upload.click(safe(service.kb_ingest_files), inputs=[files, library, size], outputs=[status, documents])
    download.click(safe(service.kb_ingest_url), inputs=[url, library, size], outputs=[status, documents])
    read.click(safe(knowledge_reader), inputs=doc_id, outputs=reader)
    return library, size
