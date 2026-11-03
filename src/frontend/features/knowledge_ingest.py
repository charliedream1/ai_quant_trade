"""Named library ingestion, shared by file upload and URL downloads."""

import gradio as gr
from src.knowledge.config import knowledge_config

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
    documents = table("当前知识库文档", 350)
    with gr.Row():
        doc_id = gr.Number(label="文档 ID", precision=0)
        read = gr.Button("预览原件")
    reader = gr.HTML(elem_id="kb-file-reader")
    create.click(safe(service.kb_create_library), inputs=library, outputs=[status, library])
    refresh.click(safe(service.kb_library_choices), outputs=library)
    refresh.click(safe(service.kb_library_documents), inputs=library, outputs=documents)
    library.change(safe(service.kb_library_documents), inputs=library, outputs=documents)
    upload.click(safe(service.kb_ingest_files), inputs=[files, library, size], outputs=[status, documents])
    download.click(safe(service.kb_ingest_url), inputs=[url, library, size], outputs=[status, documents])
    read.click(safe(knowledge_reader), inputs=doc_id, outputs=reader)
    return library, size
