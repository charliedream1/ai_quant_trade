"""Shared launchers keep heavy readers outside the initial Gradio component tree."""

from pathlib import Path

import gradio as gr
from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode
from src.documents.access import bounded_read
from src.documents.config import preview_config
from src.documents.service import FilePreviewService
from src.documents.store import PreviewStore
from src.documents.view import launcher

from ..common.callbacks import safe


def project_reader(relative: str) -> str:
    return launcher(PreviewStore().register_project(relative))


def knowledge_reader(identifier) -> str:
    return launcher(FilePreviewService().knowledge(int(identifier)))


def uploaded_reader(value) -> str:
    if not value:
        raise BusinessError(ErrorCode.INVALID_PARAM, "请先选择一个文件")
    path = Path(str(value)).resolve()
    if not path.is_relative_to(PROJECT_ROOT.resolve()):
        raise BusinessError(ErrorCode.INVALID_PARAM, "上传缓存必须位于项目目录，请配置GRADIO_TEMP_DIR")
    return launcher(PreviewStore().upload(path.name, bounded_read(path)))


def render_upload_reader() -> None:
    with gr.Accordion("文件阅读与Markdown编辑", open=False):
        gr.Markdown("上传文件后在侧边阅读，Markdown可编辑保存；Office只读。此入口不自动加入知识库。")
        extensions = [suffix for group in preview_config()["formats"].values() for suffix in group]
        upload = gr.File(label="选择预览文件", file_types=extensions, elem_id="reader-upload")
        with gr.Row():
            button = gr.Button("打开阅读面板", elem_id="reader-upload-open", variant="primary", interactive=False)
            replace = gr.Button("更换文件", elem_id="reader-upload-replace")
        result = gr.HTML(elem_id="reader-upload-result")
        button.click(safe(uploaded_reader), inputs=upload, outputs=result)
        upload.upload(lambda value: gr.update(interactive=bool(value)), inputs=upload, outputs=button, queue=False)
        upload.clear(lambda: gr.update(interactive=False), outputs=button, queue=False)
        replace.click(lambda: (None, "", gr.update(interactive=False)), outputs=[upload, result, button], queue=False)
