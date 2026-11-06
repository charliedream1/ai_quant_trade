"""Help rendering is available without credential resolution or network setup."""

import gradio as gr
from src.frontend.features.remote_access_help import render_remote_access_help


def test_remote_help_renders_both_connection_flows(monkeypatch):
    monkeypatch.setenv("GRADIO_ANALYTICS_ENABLED", "false")
    with gr.Blocks() as page:
        render_remote_access_help()
    text = "\n".join(
        str(component.get("props", {}).get("value", "")) for component in page.get_config_file()["components"]
    )
    assert "FEISHU_APP_ID" in text and "WECOM_BOT_ID" in text
    assert "ALL_IN_ONE_ACCESS_MODE=token" in text
    assert "/confirm" in text and "HTTPS" in text
    page.close()
