"""One opt-in analysis panel binds registered server observations to the active page."""

from html import escape

import gradio as gr

from src.core.config import get_settings
from src.core.page_analysis_snapshot import analysis_config
from src.engine.insights.page_analysis import cancel as cancel_analysis
from src.engine.insights.page_analysis import start
from src.engine.insights.page_generation import capability
from src.engine.insights.service import InsightReportService

from ..common.callbacks import safe
from ..common.composer import render_composer
from ..common.errors import ui_error_message
from ..service.insights import _view


def render_page_analysis(blocks, module):
    cfg = analysis_config()
    presets = {
        key: row for key, row in cfg["presets"].items() if row["module"] == module and row.get("show_panel", True)
    }
    if not presets:
        return
    ui = cfg["ui"]
    components = list(blocks.blocks.values())
    bound = {}
    for key, row in presets.items():
        for field, selector in row.get("bindings", {}).items():
            component = next(
                (
                    item
                    for item in components
                    if all(
                        getattr(item, "elem_id" if name == "id" else name, None) == value
                        for name, value in selector.items()
                    )
                ),
                None,
            )
            if component is not None:
                bound[(key, field)] = component
    inputs = list(dict.fromkeys(bound.values()))
    view = gr.Textbox(value="", elem_id="page-skill-view", elem_classes=["route-control"])
    with gr.Accordion(ui["title"], open=False, elem_id="page-skill-panel") as panel:
        gr.Markdown(ui["intro"])
        task = gr.Dropdown(
            [(row["label"], key) for key, row in presets.items()],
            value=next(iter(presets)),
            label=ui["task"],
            interactive=True,
            elem_id="page-skill-task",
        )
        composer = render_composer("page-skill", [], default_backend="codex", task_controls=True)
        with gr.Row():
            run = gr.Button(ui["run"], variant="primary", elem_id="page-skill-run")
            cancel = gr.Button(ui["cancel"], elem_id="page-skill-cancel")
        scope = gr.JSON(label=ui["scope"])
        status = gr.Markdown(ui["waiting"], elem_id="page-skill-status")
        progress = gr.Textbox(label=ui["progress"], lines=7, max_lines=14, elem_id="page-skill-progress")
        gr.Markdown(ui["scope_warning"])
        preview = gr.HTML(elem_id="page-skill-preview", elem_classes=["no-i18n"])
        download = gr.HTML(elem_id="page-skill-download")
        events = gr.File(visible=False)
        history = gr.Dropdown([], label=ui["history"], interactive=True, elem_id="page-skill-history")
        with gr.Row():
            refresh = gr.Button(ui["refresh"], elem_id="page-skill-history-refresh")
            open_report = gr.Button(ui["open"], elem_id="page-skill-history-open")
        identifier = gr.State({"run": ""})
    timer = gr.Timer(cfg["limits"]["poll_seconds"], active=False)
    panel.collapse(lambda: gr.update(active=False), outputs=timer, queue=False)

    def selected(page_view, tracker, current):
        values = [(row["label"], key) for key, row in presets.items() if page_view in row["views"]]
        if tracker.get("display_view") == page_view:
            return (gr.skip(), gr.skip(), gr.update(active=bool(tracker.get("run"))), gr.skip(), gr.skip(), gr.skip())
        tracker.update(run="", view=page_view, display_view=page_view)
        return (
            values[0][1] if values else None,
            gr.update(interactive=bool(values)),
            gr.update(active=False),
            "",
            ui["waiting"],
            "",
        )

    panel.expand(
        safe(selected),
        inputs=[view, identifier, task],
        outputs=[task, run, timer, preview, status, progress],
        queue=False,
    )

    def submit(key, backend, model, effort, tracker, *values):
        if key not in presets:
            return gr.skip(), gr.skip(), ui["invalid"], gr.skip()
        provider = {"backend": backend, "model_name": model or "", "reasoning_effort": effort or ""}
        context = {
            field: values[inputs.index(component)] for (preset, field), component in bound.items() if preset == key
        }
        try:
            # Discovery and normal chat eligibility do not establish strict research eligibility.
            capability(key, provider)
            row = start(key, provider, context)
        except ValueError as exc:
            return gr.skip(), gr.skip(), escape(ui_error_message(exc)), gr.skip()
        tracker["run"] = row["run_id"]
        return tracker, row["request"], row["run_id"], gr.update(active=True)

    run.click(
        safe(submit),
        inputs=[task, composer.backend, composer.model, composer.reasoning, identifier, *inputs],
        outputs=[identifier, scope, status, timer],
        queue=False,
    )

    def poll(tracker):
        key = tracker.get("run")
        if not key:
            return tuple(gr.skip() for _ in range(7))
        service = InsightReportService()
        row = service.detail(key)
        recorded = service.store.events(key)
        result = list(_view(service, row, recorded))
        if row["status"] == "running" and any(item["kind"] == "cancellation" for item in recorded):
            result[0] = ui["stopping"] + " · " + key
        result[3] = (
            f'<a href="{escape(get_settings().api_prefix)}/insights/runs/{escape(key)}/files/report.html" download="report.html">{escape(ui["download"])}</a>'
            if result[3]
            else ""
        )
        if tracker.get("run") != key:
            return tuple(gr.skip() for _ in range(7))
        return (*result, gr.update(active=row["status"] == "running"))

    outputs = [status, progress, preview, download, events, history, timer]
    timer.tick(safe(poll), inputs=identifier, outputs=outputs, queue=False)

    def cancel_run(tracker):
        if tracker.get("run"):
            return cancel_analysis(tracker["run"])
        return ui["waiting"]

    cancel.click(safe(cancel_run), inputs=identifier, outputs=status, queue=False)
    refresh.click(
        safe(
            lambda: gr.update(
                choices=[
                    (escape(row.get("title") or row["request"].get("page_task", "")), row["run_id"])
                    for row in InsightReportService().store.history(cfg["limits"]["history"])
                    if row["request"].get("kind") == "page_analysis"
                ]
            )
        ),
        outputs=history,
        queue=False,
    )

    def reopen(key, tracker):
        tracker["run"] = key
        return poll(tracker)

    open_report.click(safe(reopen), inputs=[history, identifier], outputs=outputs, queue=False)
