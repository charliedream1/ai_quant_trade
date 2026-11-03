"""Presentation helpers for the compact AI conversation workspace."""

from typing import Any

import pandas as pd

import gradio as gr


def session_choice_update(frame: pd.DataFrame, session_id: Any) -> dict[str, Any]:
    """Keep sidebar choices in sync without fetching sessions during page construction."""
    choices = [
        (
            f"{row.get('title') or '未命名会话'} · {row.get('project_name') or '-'} · #{int(row['id'])}",
            str(int(row["id"])),
        )
        for row in frame.to_dict("records")
        if row.get("id") is not None and pd.notna(row["id"])
    ]
    selected = str(int(session_id or 0))
    return gr.update(choices=choices, value=selected if any(value == selected for _, value in choices) else None)


def console_toolbar_html() -> str:
    return (
        "<div class='ai-console-toolbar-content'>"
        "<button id='ai-console-sidebar-toggle' type='button' aria-label='收起工作栏' aria-expanded='true' "
        "aria-controls='ai-console-sidebar'><span aria-hidden='true'>☰</span><span>收起工作栏</span></button>"
        "<strong>AI 工作台</strong>"
        "<button id='ai-console-files-toggle' type='button' title='打开项目文件预览；不会自动发送文件内容' aria-expanded='false' "
        "aria-controls='ai-console-files'>打开文件面板</button></div>"
    )
