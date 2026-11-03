"""Small, lazy report panel within AI workspace insights."""

import gradio as gr
from src.engine.insights.config import insight_config
from src.frontend.common.callbacks import safe
from src.frontend.handlers import DomainHandler


def render_insights(service: DomainHandler) -> None:
    config = insight_config()
    ui, defaults = config["ui"], config["defaults"]
    gr.Markdown(f"### {ui['title']}\n\n{ui['intro']}")
    with gr.Row():
        with gr.Column(scale=1, min_width=250):
            backend = gr.Dropdown(
                [(row["label"], row["id"]) for row in config["backends"]],
                value=defaults["backend"],
                label=ui["backend"],
                interactive=True,
            )
            market_button = gr.Button(config["tasks"]["market_review"]["label"], variant="primary")
            symbol = gr.Textbox(label=ui["symbol"], placeholder=ui["symbol_placeholder"], interactive=True)
            stock_button = gr.Button(config["tasks"]["single_stock_analysis"]["label"], variant="primary")
            with gr.Accordion(ui["model_settings"], open=False):
                model_id = gr.Dropdown(
                    service.research_team_model_choices(), value=0, label=ui["api_model"], interactive=True
                )
                model_name = gr.Textbox(label=ui["cli_model"], interactive=True)
                effort = gr.Dropdown(
                    ui["effort_choices"], value=ui["effort_choices"][0], label=ui["effort"], interactive=True
                )
                timeframe = gr.Dropdown(
                    [(row["label"], row["id"]) for row in ui["timeframe_choices"]],
                    value=defaults["timeframe"],
                    label=ui["timeframe"],
                    interactive=True,
                )
                end_date = gr.Textbox(label=ui["end_date"], interactive=True)
            history = gr.Dropdown(label=ui["history"], choices=[], interactive=True)
            refresh = gr.Button(ui["refresh_history"])
            open_history = gr.Button(ui["load_history"])
        with gr.Column(scale=4, min_width=400):
            status = gr.Textbox(label=ui["status"], value=ui["ready"], interactive=False)
            with gr.Accordion(ui["progress"], open=True):
                process = gr.Textbox(
                    label=ui["progress"], value=ui["process_empty"], lines=9, max_lines=16, interactive=False
                )
            preview = gr.HTML()
            with gr.Row():
                download = gr.File(label=ui["download"], interactive=False)
                events_file = gr.File(label=ui["download_events"], interactive=False)
    inputs = [backend, symbol, model_id, model_name, effort, timeframe, end_date]
    outputs = [status, process, preview, download, events_file, history]

    def run_market(*args):
        yield from service.insight_run("market_review", *args)

    def run_stock(*args):
        yield from service.insight_run("single_stock_analysis", *args)

    for button, callback in ((market_button, run_market), (stock_button, run_stock)):
        button.click(
            safe(callback), inputs=inputs, outputs=outputs, concurrency_id="insight-reports", concurrency_limit=2
        )
    refresh.click(safe(service.insight_history), outputs=history, queue=False)
    open_history.click(safe(service.insight_open), inputs=history, outputs=outputs)
