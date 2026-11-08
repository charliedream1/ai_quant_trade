"""Render portable setup guidance without inspecting credentials or starting services."""

import gradio as gr
import yaml

from src.core.config import PROJECT_ROOT


def render_remote_access_help() -> None:
    policy = yaml.safe_load((PROJECT_ROOT / "egs/config/security/remote_access_help.yaml").read_text(encoding="utf-8"))
    with gr.Accordion(policy["title"], open=True, elem_id="remote-access-help"):
        gr.Markdown(policy["summary"])
        for section in policy["sections"]:
            gr.Markdown(
                "### "
                + section["title"]
                + "\n\n"
                + "\n".join(f"{index}. {text}" for index, text in enumerate(section["steps"], 1))
            )
        gr.Markdown(policy["more"])
