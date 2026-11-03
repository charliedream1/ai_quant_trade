"""Review a frozen custom source before allowing its bounded worker to run."""

import gradio as gr
from src.strategy.strategy_store import StrategyStore


def render_source_review(identifier):
    with gr.Accordion("自定义源码运行复核", open=False):
        checksum = gr.Textbox(label="在上方策略信息核对source_sha256后填写")
        reviewer = gr.Textbox(label="复核者")
        approve = gr.Button("登记源码复核")
        output = gr.JSON(label="源码复核记录")
        approve.click(
            lambda value, digest, name: StrategyStore().review(int(value), digest, name),
            inputs=[identifier, checksum, reviewer],
            outputs=output,
        )
