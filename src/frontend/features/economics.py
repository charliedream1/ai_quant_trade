"""On-demand macroeconomic and financial views with optional model research."""

import gradio as gr
from src.engine.economics.config import economics_config

from ..common.callbacks import safe
from ..common.components import plot, table


def render_economics(service, kind):
    cfg = economics_config()
    ui = cfg["ui"]
    gr.Markdown(ui["intro"])
    kind_state = gr.State(kind)
    with gr.Row():
        series = gr.Dropdown(
            [(row["label"], key) for key, row in cfg["macro"].items()],
            value=list(cfg["macro"]),
            multiselect=True,
            label=ui["series"],
            visible=kind == "macro",
        )
        symbol = gr.Textbox(label=ui["symbol"], visible=kind != "macro", elem_id=kind + "-symbol")
        period = gr.Textbox(label=ui["period"], visible=kind != "macro")
        peers = gr.Textbox(label=ui["peers"], visible=kind != "macro")
    with gr.Row():
        refresh = gr.Checkbox(label=ui["refresh"], value=False)
        load = gr.Button(ui["load"], variant="primary", elem_id=kind + "-load")
    status = gr.Markdown(elem_id=kind + "-status")
    overview = table(ui["overview"], 420)
    chart = plot(label=ui["history"])
    with gr.Accordion(ui["raw"], open=False):
        raw = gr.JSON()
        snapshot = gr.Textbox(label=ui["snapshot"], interactive=False, elem_id=kind + "-snapshot")
    with gr.Row():
        model = gr.Dropdown(service.economic_models(), value=0, label=ui["model"])
        generate = gr.Button(ui["report"], elem_id=kind + "-report")
    process = gr.Textbox(label=ui["report_status"], lines=5, max_lines=8, elem_id=kind + "-report-status")
    preview = gr.HTML(elem_id=kind + "-report-preview")
    download = gr.File(label=ui["download"])
    with gr.Row():
        previous = gr.Textbox(label=ui["previous"], elem_id=kind + "-run-id")
        reopen = gr.Button(ui["reopen"])
    load.click(
        safe(service.economic_load),
        inputs=[kind_state, series, symbol, period, peers, refresh],
        outputs=[status, overview, chart, raw, snapshot],
    )
    generate.click(
        safe(service.economic_report),
        inputs=[kind_state, snapshot, model],
        outputs=[process, preview, download, previous],
    )
    reopen.click(safe(service.economic_open), inputs=previous, outputs=[process, preview, download, previous])
