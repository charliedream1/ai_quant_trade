"""A focused section of the existing Gradio AI workspace."""

from __future__ import annotations

from ..common.ai_console import session_choice_update
from ..common.callbacks import safe as _safe
from .file_reader import project_reader


def wire_sidebar(service, widgets, actions, tab, on_load):
    widgets.ai_shell_new_chat.click(
        _safe(actions._ai_console_new_from_sidebar),
        outputs=[
            widgets.ai_console_shell_status,
            widgets.ai_console_chat_page,
            widgets.ai_console_jobs_page,
            widgets.ai_console_mcp_page,
            widgets.ai_console_skill_page,
            widgets.ai_console_knowledge_page,
            widgets.ai_console_session_id,
            widgets.ai_console_sessions,
            widgets.ai_console_chat,
        ],
        queue=False,
    )
    widgets.ai_shell_jobs.click(
        _safe(actions._ai_console_open_jobs),
        outputs=[
            widgets.ai_console_shell_status,
            widgets.ai_console_chat_page,
            widgets.ai_console_jobs_page,
            widgets.ai_console_mcp_page,
            widgets.ai_console_skill_page,
            widgets.ai_console_knowledge_page,
            widgets.ai_jobs_table,
        ],
        queue=False,
    )
    widgets.ai_shell_mcp.click(
        _safe(actions._ai_console_open_mcp),
        outputs=[
            widgets.ai_console_shell_status,
            widgets.ai_console_chat_page,
            widgets.ai_console_jobs_page,
            widgets.ai_console_mcp_page,
            widgets.ai_console_skill_page,
            widgets.ai_console_knowledge_page,
            widgets.ai_mcp_table,
        ],
        queue=False,
    )
    widgets.ai_shell_skill.click(
        _safe(actions._ai_console_open_skill),
        outputs=[
            widgets.ai_console_shell_status,
            widgets.ai_console_chat_page,
            widgets.ai_console_jobs_page,
            widgets.ai_console_mcp_page,
            widgets.ai_console_skill_page,
            widgets.ai_console_knowledge_page,
            widgets.ai_skill_table,
        ],
        queue=False,
    )
    widgets.ai_shell_knowledge.click(
        _safe(actions._ai_console_open_knowledge),
        outputs=[
            widgets.ai_console_shell_status,
            widgets.ai_console_chat_page,
            widgets.ai_console_jobs_page,
            widgets.ai_console_mcp_page,
            widgets.ai_console_skill_page,
            widgets.ai_console_knowledge_page,
            widgets.ai_kb_categories,
            widgets.ai_kb_documents,
        ],
        queue=False,
    )


def wire_chat(service, widgets, actions, tab, on_load):
    widgets.ai_console_new.click(
        _safe(service.ai_console_new_session),
        inputs=[widgets.ai_console_title, widgets.ai_console_project],
        outputs=[
            widgets.ai_console_shell_status,
            widgets.ai_console_session_id,
            widgets.ai_console_sessions,
            widgets.ai_console_chat,
        ],
        queue=False,
    )
    widgets.ai_console_load.click(
        _safe(service.ai_console_load_session),
        inputs=widgets.ai_console_session_id,
        outputs=[widgets.ai_console_shell_status, widgets.ai_console_chat],
        queue=False,
    )
    widgets.ai_console_send.click(
        _safe(service.ai_console_send_stream),
        inputs=[
            widgets.ai_console_session_id,
            widgets.ai_console_input,
            widgets.ai_console_chat,
            widgets.ai_console_backend,
            widgets.ai_console_attachments,
            widgets.ai_console_model,
            widgets.ai_console_reasoning,
            widgets.composer.permission,
        ],
        outputs=[
            widgets.ai_console_session_id,
            widgets.ai_console_chat,
            widgets.ai_console_input,
            widgets.ai_console_attachments,
            widgets.ai_console_shell_status,
            widgets.ai_console_sessions,
        ],
    )
    widgets.ai_console_input.submit(
        _safe(service.ai_console_send_stream),
        inputs=[
            widgets.ai_console_session_id,
            widgets.ai_console_input,
            widgets.ai_console_chat,
            widgets.ai_console_backend,
            widgets.ai_console_attachments,
            widgets.ai_console_model,
            widgets.ai_console_reasoning,
            widgets.composer.permission,
        ],
        outputs=[
            widgets.ai_console_session_id,
            widgets.ai_console_chat,
            widgets.ai_console_input,
            widgets.ai_console_attachments,
            widgets.ai_console_shell_status,
            widgets.ai_console_sessions,
        ],
    )
    widgets.ai_console_clear.click(
        lambda: ([], "已清空当前显示，数据库会话历史仍保留。"),
        outputs=[widgets.ai_console_chat, widgets.ai_console_shell_status],
        queue=False,
    )
    widgets.ai_console_file_open.click(
        _safe(project_reader), inputs=widgets.ai_console_file_path, outputs=widgets.ai_console_file_reader, queue=False
    )
    widgets.ai_console_source_open.click(
        _safe(service.ai_console_file_preview),
        inputs=widgets.ai_console_file_path,
        outputs=widgets.ai_console_file_content,
        queue=False,
    )


def wire_files_sessions(service, widgets, actions, tab, on_load):
    widgets.ai_console_refresh.click(
        _safe(service.ai_console_sessions), outputs=widgets.ai_console_sessions, queue=False
    )
    session_loader = on_load if on_load is not None else tab.select
    session_loader(_safe(service.ai_console_sessions), outputs=widgets.ai_console_sessions, queue=False)
    widgets.ai_console_sessions.change(
        session_choice_update,
        inputs=[widgets.ai_console_sessions, widgets.ai_console_session_id],
        outputs=widgets.ai_console_session_list,
        queue=False,
    )
    widgets.ai_console_session_list.input(
        _safe(actions._ai_console_select_session),
        inputs=widgets.ai_console_session_list,
        outputs=[
            widgets.ai_console_shell_status,
            widgets.ai_console_chat_page,
            widgets.ai_console_jobs_page,
            widgets.ai_console_mcp_page,
            widgets.ai_console_skill_page,
            widgets.ai_console_knowledge_page,
            widgets.ai_console_session_id,
            widgets.ai_console_chat,
        ],
        queue=False,
    )
    widgets.ai_project_refresh.click(
        _safe(actions._ai_console_refresh_project_dir),
        inputs=widgets.ai_project_dir,
        outputs=[widgets.ai_project_status, widgets.ai_project_choice, widgets.ai_project_dir],
        queue=False,
    )
    widgets.ai_project_use.click(
        lambda path: path or "README.md",
        inputs=widgets.ai_project_choice,
        outputs=widgets.ai_console_file_path,
        queue=False,
    )
