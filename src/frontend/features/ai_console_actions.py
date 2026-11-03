"""A focused section of the existing Gradio AI workspace."""

from __future__ import annotations

from typing import Any

import pandas as pd

import gradio as gr


class ConsoleActions:
    def __init__(self, service):
        self.service = service

    def _ai_console_page_updates(self, page: str, status: str) -> tuple[str, Any, Any, Any, Any, Any]:
        return (
            status,
            gr.update(visible=page == "chat"),
            gr.update(visible=page == "jobs"),
            gr.update(visible=page == "mcp"),
            gr.update(visible=page == "skill"),
            gr.update(visible=page == "knowledge"),
        )

    def _ai_console_new_from_sidebar(self) -> tuple[str, Any, Any, Any, Any, Any, int, pd.DataFrame, list]:
        status, session_id, sessions, history = self.service.ai_console_new_session("新的投研会话", "")
        return (*self._ai_console_page_updates("chat", status), session_id, sessions, history)

    def _ai_console_open_jobs(self) -> tuple[str, Any, Any, Any, Any, Any, pd.DataFrame]:
        return (
            *self._ai_console_page_updates("jobs", "已打开定时任务工作区，可刷新任务、触发任务或查看执行历史。"),
            self.service.jobs(),
        )

    def _ai_console_open_mcp(self) -> tuple[str, Any, Any, Any, Any, Any, pd.DataFrame]:
        return (
            *self._ai_console_page_updates("mcp", "已打开 MCP 工作区，可测试服务、启停连接或调用工具。"),
            self.service.mcp_servers(),
        )

    def _ai_console_open_skill(self) -> tuple[str, Any, Any, Any, Any, Any, pd.DataFrame]:
        return (
            *self._ai_console_page_updates("skill", "已打开 Skill 工作区，可启停、运行或查看参数。"),
            self.service.skills(),
        )

    def _ai_console_open_knowledge(self) -> tuple[str, Any, Any, Any, Any, Any, pd.DataFrame, pd.DataFrame]:
        return (
            *self._ai_console_page_updates("knowledge", "已打开知识库工作区，可登记分类、保存笔记或上传文档。"),
            self.service.kb_categories(),
            self.service.kb_search("", None, "all"),
        )

    def _ai_project_choices(self, frame: pd.DataFrame) -> list[tuple[str, str]]:
        if frame.empty:
            return []
        choices: list[tuple[str, str]] = []
        for row in frame.to_dict("records"):
            path = str(row.get("路径") or "").strip()
            if not path:
                continue
            label = f"{row.get('类型', '-')}: {path}"
            choices.append((label, path))
        return choices

    def _ai_console_refresh_project_dir(self, relative_dir: str) -> tuple[str, Any, str]:
        status, frame, directory = self.service.ai_console_project_tree(relative_dir)
        return (status, gr.update(choices=self._ai_project_choices(frame), value=None), directory)

    def _ai_console_select_session(self, session_id: str) -> tuple:
        status, history = self.service.ai_console_load_session(session_id)
        return (*self._ai_console_page_updates("chat", status), int(session_id), history)
