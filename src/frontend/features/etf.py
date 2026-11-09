"""ETF data and research tools within strategy management."""

import gradio as gr

from ..common.callbacks import safe as _safe
from ..common.components import table as _table


def render_etf_strategy(service, etf_tab):
    with gr.Column(elem_classes=["ai-workbench-panel"]):
        with gr.Row():
            etf_universe = gr.Dropdown(
                choices=service.etf_universe_choices(),
                value=(service.etf_universe_choices() or [("A股核心宽基 ETF", "cn_core")])[0][1],
                label="ETF池",
                scale=3,
            )
            etf_refresh = gr.Button("刷新 ETF 数据", variant="primary")
        etf_status = gr.Markdown(elem_classes=["status-strip"])
        etf_table = _table("ETF 元数据与数据源快照", 360)
    etf_refresh.click(
        _safe(service.etf_universe_snapshot),
        inputs=etf_universe,
        outputs=[etf_status, etf_table],
        queue=False,
    )
    etf_tab.select(
        _safe(service.etf_universe_snapshot),
        inputs=etf_universe,
        outputs=[etf_status, etf_table],
        queue=False,
    )
