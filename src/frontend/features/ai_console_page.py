"""A focused section of the existing Gradio AI workspace."""

from __future__ import annotations

import gradio as gr

from .ai_console_actions import ConsoleActions
from .ai_console_events import wire_chat, wire_files_sessions, wire_sidebar
from .ai_console_widgets import build_console_widgets


def render_console(service, on_load=None):
    with gr.Tab("主界面") as ai_console_tab:
        actions = ConsoleActions(service)
        widgets = build_console_widgets(service, actions)
        wire_sidebar(service, widgets, actions, ai_console_tab, on_load)
        wire_chat(service, widgets, actions, ai_console_tab, on_load)
        wire_files_sessions(service, widgets, actions, ai_console_tab, on_load)
