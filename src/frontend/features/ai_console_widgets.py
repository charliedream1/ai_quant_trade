"""A focused section of the existing Gradio AI workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

import gradio as gr
from src.agent.workspace import workspace_config

from ..common.ai_console import console_toolbar_html
from ..common.components import chatbot as _chatbot
from ..common.composer import render_composer
from .quick_tools import render_automation_quick, render_knowledge_quick, render_mcp_quick, render_skill_quick


@dataclass
class ConsoleWidgets:
    ai_console_attachments: Any
    ai_console_backend: Any
    ai_console_chat: Any
    ai_console_chat_page: Any
    ai_console_clear: Any
    ai_console_file_content: Any
    ai_console_file_open: Any
    ai_console_file_path: Any
    ai_console_file_reader: Any
    ai_console_input: Any
    ai_console_jobs_page: Any
    ai_console_knowledge_page: Any
    ai_console_load: Any
    ai_console_mcp_page: Any
    ai_console_model: Any
    ai_console_new: Any
    ai_console_project: Any
    ai_console_reasoning: Any
    ai_console_refresh: Any
    ai_console_send: Any
    ai_console_session_id: Any
    ai_console_session_list: Any
    ai_console_sessions: Any
    ai_console_shell_status: Any
    ai_console_skill_page: Any
    ai_console_source_open: Any
    ai_console_title: Any
    ai_jobs_table: Any
    ai_kb_categories: Any
    ai_kb_documents: Any
    ai_mcp_table: Any
    ai_project_choice: Any
    ai_project_dir: Any
    ai_project_refresh: Any
    ai_project_status: Any
    ai_project_use: Any
    ai_shell_jobs: Any
    ai_shell_knowledge: Any
    ai_shell_mcp: Any
    ai_shell_new_chat: Any
    ai_shell_skill: Any
    ai_skill_table: Any
    composer: Any


def build_console_widgets(service, actions):
    project_status_value = "点击“刷新目录”后按需读取项目文件。"
    project_tree_value = pd.DataFrame()
    project_dir_value = "."
    ai_model_choices = service.ai_console_model_choices()
    with gr.Row(elem_id="ai-console-shell", elem_classes=["ai-console-shell"]):
        with gr.Column(scale=1, min_width=220, elem_id="ai-console-sidebar", elem_classes=["ai-shell-sidebar"]):
            gr.HTML(
                "<section class='ai-shell-brand'><button id='ai-console-sidebar-close' type='button' aria-label='关闭工作栏'>×</button><span>AI Console</span><strong>工作台</strong><p>聊天、定时任务、MCP 和 Skill 的统一入口</p></section>"
            )
            with gr.Column(elem_classes=["ai-shell-nav"]):
                ai_shell_new_chat = gr.Button("＋ 新任务")
                ai_shell_jobs = gr.Button("⏱ 自动化")
                ai_shell_mcp = gr.Button("⌁ MCP 服务")
                ai_shell_skill = gr.Button("◇ Skill")
                ai_shell_knowledge = gr.Button("▤ 知识库")
            with gr.Accordion("项目文件浏览", open=False):
                ai_project_dir = gr.Textbox(value=project_dir_value, label="目录")
                ai_project_refresh = gr.Button("刷新目录")
                ai_project_status = gr.Markdown(project_status_value, elem_classes=["compact-note"])
                ai_project_choice = gr.Dropdown(
                    choices=actions._ai_project_choices(project_tree_value), label="目录项", interactive=True
                )
                ai_project_use = gr.Button("使用路径")
            with gr.Column(elem_classes=["ai-session-panel"]):
                gr.HTML("<div class='ai-session-heading'><strong>项目会话</strong></div>")
                ai_console_session_list = gr.Radio(
                    choices=[], label="会话列表", interactive=True, elem_id="ai-console-session-list"
                )
                with gr.Accordion("项目与会话设置", open=False, elem_classes=["ai-session-settings"]):
                    ai_console_project = gr.Textbox(value=str(workspace_config()["default_project"]), label="项目")
                    ai_console_title = gr.Textbox(value="新的投研会话", label="会话标题")
                    with gr.Row():
                        ai_console_new = gr.Button("新建会话", variant="primary", min_width=80)
                        ai_console_refresh = gr.Button("刷新会话", min_width=80)
                    ai_console_session_id = gr.Number(label="会话 ID", precision=0)
                    ai_console_load = gr.Button("载入会话", min_width=80)
                ai_console_sessions = gr.Dataframe(visible=False, label="会话数据")
        with gr.Column(scale=3, min_width=640, elem_classes=["ai-shell-main"]):
            ai_console_shell_status = gr.Markdown(
                "选择左侧入口开始工作。", elem_id="ai-console-status", elem_classes=["status-strip"]
            )
            with gr.Column(
                visible=True, elem_id="ai-console-chat-page", elem_classes=["ai-shell-page"]
            ) as ai_console_chat_page:
                with gr.Row(elem_id="ai-console-toolbar"):
                    gr.HTML(console_toolbar_html())
                    ai_console_clear = gr.Button("清空显示", min_width=80, scale=0)
                ai_console_chat = _chatbot("模型对话", 520, "ai-console-chat-history")
                composer = render_composer("ai-console", ai_model_choices, service.ai_console_model_choices)
                ai_console_input, ai_console_attachments = (composer.text, composer.attachments)
                ai_console_backend, ai_console_model = (composer.backend, composer.model)
                ai_console_reasoning, ai_console_send = (composer.reasoning, composer.send)
            with gr.Group(visible=False, elem_classes=["ai-shell-page"]) as ai_console_jobs_page:
                ai_jobs_table = render_automation_quick(service)
            with gr.Group(visible=False, elem_classes=["ai-shell-page"]) as ai_console_mcp_page:
                ai_mcp_table = render_mcp_quick(service)
            with gr.Group(visible=False, elem_classes=["ai-shell-page"]) as ai_console_skill_page:
                ai_skill_table = render_skill_quick(service)
            with gr.Group(visible=False, elem_classes=["ai-shell-page"]) as ai_console_knowledge_page:
                ai_kb_categories, ai_kb_documents = render_knowledge_quick(service)
        with gr.Column(scale=1, min_width=280, elem_id="ai-console-files", elem_classes=["ai-shell-context"]):
            gr.HTML(
                "<button id='ai-console-files-close' type='button' aria-label='关闭文件面板'>关闭文件面板 ×</button><section class='ai-console-file-head'><span>Project</span><strong>项目文件</strong><p>在会话旁预览源码、配置和文档，路径限定在当前项目内。</p></section>"
            )
            gr.HTML("<p class='ai-context-hint'>文件预览不会自动发送给模型。需要引用时，请将相关内容复制到任务中。</p>")
            ai_console_file_path = gr.Textbox(value="README.md", label="相对路径")
            ai_console_file_open = gr.Button("打开文件", variant="primary")
            ai_console_file_reader = gr.HTML(elem_id="ai-file-reader")
            with gr.Accordion("文本源码查看", open=False):
                ai_console_source_open = gr.Button("读取文本源码")
                ai_console_file_content = gr.Code(language="markdown", label="文件内容", interactive=False, lines=10)
    return ConsoleWidgets(
        ai_console_attachments=ai_console_attachments,
        ai_console_backend=ai_console_backend,
        ai_console_chat=ai_console_chat,
        ai_console_chat_page=ai_console_chat_page,
        ai_console_clear=ai_console_clear,
        ai_console_file_content=ai_console_file_content,
        ai_console_file_open=ai_console_file_open,
        ai_console_file_path=ai_console_file_path,
        ai_console_file_reader=ai_console_file_reader,
        ai_console_input=ai_console_input,
        ai_console_jobs_page=ai_console_jobs_page,
        ai_console_knowledge_page=ai_console_knowledge_page,
        ai_console_load=ai_console_load,
        ai_console_mcp_page=ai_console_mcp_page,
        ai_console_model=ai_console_model,
        ai_console_new=ai_console_new,
        ai_console_project=ai_console_project,
        ai_console_reasoning=ai_console_reasoning,
        ai_console_refresh=ai_console_refresh,
        ai_console_send=ai_console_send,
        ai_console_session_id=ai_console_session_id,
        ai_console_session_list=ai_console_session_list,
        ai_console_sessions=ai_console_sessions,
        ai_console_shell_status=ai_console_shell_status,
        ai_console_skill_page=ai_console_skill_page,
        ai_console_source_open=ai_console_source_open,
        ai_console_title=ai_console_title,
        ai_jobs_table=ai_jobs_table,
        ai_kb_categories=ai_kb_categories,
        ai_kb_documents=ai_kb_documents,
        ai_mcp_table=ai_mcp_table,
        ai_project_choice=ai_project_choice,
        ai_project_dir=ai_project_dir,
        ai_project_refresh=ai_project_refresh,
        ai_project_status=ai_project_status,
        ai_project_use=ai_project_use,
        ai_shell_jobs=ai_shell_jobs,
        ai_shell_knowledge=ai_shell_knowledge,
        ai_shell_mcp=ai_shell_mcp,
        ai_shell_new_chat=ai_shell_new_chat,
        ai_shell_skill=ai_shell_skill,
        ai_skill_table=ai_skill_table,
        composer=composer,
    )
