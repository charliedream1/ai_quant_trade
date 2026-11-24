"""On-demand macroeconomic and financial views with optional model research."""

import gradio as gr

from src.data import current_market
from src.engine.economics.config import economics_config
from src.frontend.service.financial_views import financial_sections

from ..common.callbacks import safe
from ..common.components import plot, table
from .page_analysis import page_report_button


def render_economics(service, kind, shared_symbol=None, *, show_report=True):
    cfg = economics_config()
    ui = cfg["ui"]
    if show_report and shared_symbol is None:
        page_report_button()
    gr.Markdown(ui["intro"])
    kind_state = gr.State(kind)
    with gr.Row():
        series = gr.Dropdown(
            [(row["label"], key) for key, row in cfg["macro"].items()],
            value=list(cfg["macro"]),
            multiselect=True,
            label=ui["series"],
            elem_id=kind + "-series",
            visible=kind == "macro",
        )
        symbol = (
            shared_symbol
            if shared_symbol is not None
            else gr.Textbox(
                value=cfg["defaults"]["company_symbols"].get(current_market(), ""),
                label=ui["symbol"],
                visible=kind != "macro",
                elem_id=kind + "-symbol",
            )
        )
        period = gr.Textbox(label=ui["period"], visible=kind != "macro", elem_id=kind + "-period")
        peers = gr.Textbox(label=ui["peers"], visible=kind != "macro", elem_id=kind + "-peers")
    with gr.Row():
        refresh = gr.Checkbox(label=ui["refresh"], value=False)
        load = gr.Button(ui["load"], variant="primary", elem_id=kind + "-load")
    status = gr.Markdown(elem_id=kind + "-status")
    if kind != "macro":
        gr.Markdown("Company financial analysis: mainland statement coverage; load once to inspect all sections.")
        titles = [*ui["financial_sections"], ui.get("financial_history", "Financial history")]
        section = gr.Radio(
            [(title, index) for index, title in enumerate(titles)],
            value=0,
            label="财务明细",
            elem_id="financial-analysis-sections",
        )
        statement = table("财务明细", 360, elem_id="financial-statement-details")
        finance_note = gr.Markdown()
    overview = table(ui["overview"], 420, elem_id=kind + "-overview", elem_classes=["home-semantic-table"])
    chart = plot(label=ui["history"])
    with gr.Accordion(ui["raw"], open=False):
        raw = gr.JSON()
        snapshot = gr.Textbox(label=ui["snapshot"], interactive=False, elem_id=kind + "-snapshot")
    if kind != "macro":

        def show_statement(data, index):
            *sections, note = financial_sections(data)
            return sections[int(index or 0)], note

        for event in (raw.change, section.input):
            event(safe(show_statement), inputs=[raw, section], outputs=[statement, finance_note], queue=False)
    if shared_symbol is not None:
        shared_symbol.change(
            lambda: ("", [], None, {}, ""),
            outputs=[status, overview, chart, raw, snapshot],
            queue=False,
        )
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
