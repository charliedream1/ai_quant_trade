"""Gradio UI for the assistant domain."""

from __future__ import annotations

from typing import Any

import gradio as gr

from ..common.callbacks import safe as _safe
from ..common.components import supports_parameter as _supports_parameter
from ..common.components import table as _table
from ..common.composer import render_composer
from ..common.runtime_loader import runtime_loader_js
from ..handlers import DomainHandler
from ..service.foundation import CLI_TYPE_CHOICES


def render_floating_assistant(service: DomainHandler) -> None:
    gr.Button("AI", elem_id="ai-floating-button")
    with gr.Column(elem_id="ai-floating-panel"):
        gr.HTML(
            "<div class='ai-panel-header'><strong>AI 助手</strong>"
            "<button id='ai-floating-close' type='button' aria-label='关闭' title='关闭'>&times;</button></div>"
        )
        with gr.Tabs():
            with gr.Tab("模型问答"):
                chatbot_options: dict[str, Any] = {
                    "label": "会话",
                    "height": 340,
                    "elem_id": "ai-chat-history",
                }
                if _supports_parameter(gr.Chatbot, "type"):
                    chatbot_options["type"] = "messages"
                if _supports_parameter(gr.Chatbot, "show_copy_button"):
                    chatbot_options["show_copy_button"] = True
                elif _supports_parameter(gr.Chatbot, "buttons"):
                    chatbot_options["buttons"] = ["copy"]
                ai_chat_history = gr.Chatbot(**chatbot_options)
                ai_chat_status = gr.Markdown("使用系统默认模型", elem_id="ai-chat-status")
                composer = render_composer(
                    "ai-chat", service.ai_console_model_choices(), service.ai_console_model_choices
                )
                ai_chat_input, ai_chat_send = composer.text, composer.send
                ai_chat_session = gr.State(0)
                ai_chat_clear = gr.Button("新对话")

                def _send(session, message, history, backend, attachments, model, effort, access):
                    for result in service.ai_console_send_stream(
                        session, message, history, backend, attachments, model, effort, access
                    ):
                        yield result[0], result[1], result[2], result[3], result[4]

                for trigger in (ai_chat_input.submit, ai_chat_send.click):
                    trigger(
                        _safe(_send),
                        inputs=[
                            ai_chat_session,
                            ai_chat_input,
                            ai_chat_history,
                            composer.backend,
                            composer.attachments,
                            composer.model,
                            composer.reasoning,
                            composer.permission,
                        ],
                        outputs=[ai_chat_session, ai_chat_history, ai_chat_input, composer.attachments, ai_chat_status],
                    )
                ai_chat_clear.click(
                    lambda: (0, [], "", [], "新对话，尚未调用后台"),
                    outputs=[ai_chat_session, ai_chat_history, ai_chat_input, composer.attachments, ai_chat_status],
                    queue=False,
                )
            with gr.Tab("知识问答"):
                ai_kb_question = gr.Textbox(label="问题", lines=3, placeholder="输入知识库问题")
                with gr.Row():
                    ai_kb_category = gr.Number(label="分类 ID", precision=0)
                    ai_kb_top_k = gr.Slider(1, 10, value=5, step=1, label="引用数量")
                ai_kb_ask = gr.Button("提问", variant="primary")
                ai_kb_answer = gr.Markdown(label="回答")
                ai_kb_sources = _table("引用来源", 220)
                ai_kb_ask.click(
                    _safe(service.kb_qa),
                    inputs=[ai_kb_question, ai_kb_category, ai_kb_top_k],
                    outputs=[ai_kb_answer, ai_kb_sources],
                )
            with gr.Tab("CLI 助手"):
                ai_cli_type = gr.Dropdown([*CLI_TYPE_CHOICES, ("Qoder CLI", "qoder")], value="codex", label="CLI")
                ai_cli_history = gr.Chatbot(label="CLI 会话", height=300, elem_id="ai-cli-history")
                ai_cli_status = gr.Markdown(
                    "支持 Codex/Qoder CLI；需本机安装及认证。Trae/WorkBuddy尚未接入真实CLI。", elem_id="ai-cli-status"
                )
                ai_cli_requirement = gr.Textbox(label="消息", lines=2, elem_id="ai-cli-requirement")
                ai_cli_build = gr.Button("发送", variant="primary", elem_id="ai-cli-build")
                for trigger in (ai_cli_requirement.submit, ai_cli_build.click):
                    trigger(
                        _safe(service.floating_cli_chat_stream),
                        inputs=[ai_cli_requirement, ai_cli_history, ai_cli_type],
                        outputs=[ai_cli_history, ai_cli_requirement, ai_cli_status],
                    )
    if _supports_parameter(gr.HTML, "js_on_load"):
        gr.HTML("", js_on_load=runtime_loader_js(), elem_id="ai-runtime-init")
