"""Direct, cited knowledge Q&A; delegates all retrieval to the existing service."""

from uuid import uuid4

import gradio as gr
from src.knowledge.config import knowledge_config

from ..common.callbacks import safe
from ..common.components import chatbot, table


def render_rag_chat(service) -> None:
    policy = knowledge_config()
    gr.Markdown(
        "### 知识库 AI 问答\n\n选择资料范围后提问；回答与原文引用一起显示。先在[知识库入库](/app/?module=knowledge&view=library)上传或保存资料。"
    )
    with gr.Row(elem_id="rag-chat-layout"):
        with gr.Column(scale=1, min_width=230, elem_id="rag-chat-controls"):
            library = gr.Dropdown(
                service.kb_libraries(), value=policy["default_library"], label="问答知识库", elem_id="rag-library"
            )
            library_refresh = gr.Button("刷新库名")
            rounds = gr.Slider(
                1,
                policy["search"]["max_rounds"],
                value=policy["search"]["default_rounds"],
                step=1,
                label="最多检索轮数",
            )
            model = gr.Dropdown(service.rag_models(), value="", label="问答模型")
            with gr.Accordion("会话与检索设置", open=False):
                scope = gr.Dropdown(
                    [("全部资料", "all"), ("本地资料", "local"), ("远程资料", "remote")], value="all", label="知识范围"
                )
                category = gr.Number(label="分类 ID（可选）", precision=0)
                top_k = gr.Slider(1, 20, value=5, step=1, label="引用数量")
                session = gr.Textbox(value=lambda: uuid4().hex, label="会话 ID")
                restore = gr.Button("恢复此会话")
                new = gr.Button("新会话")
                refresh = gr.Button("刷新索引与会话")
                index_status = gr.Markdown("上传入库后可在此刷新索引状态。")
                sessions = gr.Dropdown([], label="最近会话", interactive=True)
        with gr.Column(scale=3, elem_id="rag-chat-conversation"):
            history = chatbot("知识问答", 400, "rag-chat-history")
            status = gr.Markdown(elem_classes=["status-strip"])
            refs = table("引用片段（点击行查看原文）", 220, elem_id="rag-chat-references")
            original = gr.HTML(elem_id="rag-file-reader")
            question = gr.Textbox(label="问题", lines=2, placeholder="输入与资料有关的问题；Enter 发送")
            attachments = gr.File(
                label="问答附件（仅当前会话）",
                file_count="multiple",
                file_types=policy["extensions"],
                elem_id="rag-attachments",
                height=85,
            )
            send = gr.Button("提问", variant="primary")
    for event in (send.click, question.submit):
        event(
            safe(service.rag_chat),
            inputs=[question, category, top_k, session, scope, model, library, rounds, attachments],
            outputs=[status, history, refs, question, attachments],
        )
    restore.click(safe(service.rag_restore), inputs=[session, library], outputs=[history, refs], queue=False)
    library_refresh.click(safe(service.kb_library_choices), outputs=library, queue=False)
    library.change(safe(service.rag_restore), inputs=[session, library], outputs=[history, refs], queue=False)
    new.click(
        lambda: (uuid4().hex, [], None, "", "新会话，尚未调用模型"),
        outputs=[session, history, refs, question, status],
        queue=False,
    )
    refresh.click(safe(service.rag_index_status), outputs=[index_status, sessions], queue=False)

    def _source(frame, evt: gr.SelectData):
        return service.rag_source_preview(frame, evt.index[0])

    def _session(key, name):
        if not key:
            return gr.skip(), gr.skip(), gr.skip()
        messages, sources = service.rag_restore(key, name)
        return key, messages, sources

    refs.select(safe(_source), inputs=refs, outputs=original, queue=False)
    sessions.change(safe(_session), inputs=[sessions, library], outputs=[session, history, refs], queue=False)
