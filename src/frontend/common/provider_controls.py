"""Research provider metadata is lazy; never authenticate or generate on page load."""

import gradio as gr
from src.agent.providers import provider_catalog
from src.agent.providers.config import backend_choices


def provider_controls(prefix: str):
    with gr.Row():
        backend = gr.Dropdown(backend_choices(), value="api", label="Agent生成后端", elem_id=prefix + "-backend")
        model_name = gr.Textbox(label="CLI模型名称（留空使用宿主默认）", elem_id=prefix + "-cli-model")
    with gr.Accordion("CLI可用性与研究约束", open=False):
        gr.Markdown(
            "安装、登录、模型可用和严格研究是不同状态。没有通过工具/扩展禁用核验的版本会在研究生成前阻断；普通AI会话仍可使用。"
        )
        check = gr.Button("检查后端（不发起模型请求）", elem_id=prefix + "-provider-check")
        status = gr.JSON(label="实际后端能力")
        check.click(lambda: provider_catalog(probe=True), outputs=status)
    return backend, model_name
