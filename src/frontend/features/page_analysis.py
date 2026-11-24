"""One opt-in analysis panel binds registered server observations to the active page."""

from html import escape

import gradio as gr

from src.agent.cli_catalog import catalog_config
from src.agent.composer_config import cli_choices, composer_config
from src.core.config import get_settings
from src.core.exceptions import BusinessError
from src.core.page_analysis_snapshot import analysis_config, evidence, preset_matches_view
from src.core.page_work import CURRENT_PAGE
from src.engine.insights.page_analysis import cancel as cancel_analysis
from src.engine.insights.page_analysis import start
from src.engine.insights.page_generation import capability
from src.engine.insights.service import InsightReportService

from ..common.callbacks import safe
from ..common.composer_catalog import CatalogSelection, model_options
from ..common.errors import ui_error_message
from ..service.insights import _view


def page_report_button(view=""):
    label = escape(analysis_config()["ui"]["sidebar"])
    return gr.HTML(
        f"<button type='button' class='page-report-action' data-report-view='{escape(view)}'>{label}</button>",
        elem_classes=["page-report-slot"],
    )


def render_page_analysis(blocks, module, service):
    cfg = analysis_config()
    presets = {
        key: row for key, row in cfg["presets"].items() if row["module"] == module and row.get("show_panel", True)
    }
    if not presets:
        return
    ui = cfg["ui"]
    cli = cfg["cli"]
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
    language = gr.Textbox(value="zh", elem_id="page-skill-language", elem_classes=["route-control"])
    open_drawer = gr.Button(ui["sidebar"], elem_id="page-skill-open", elem_classes=["route-control"])
    if module != "market":
        gr.HTML(
            f"<button type='button' id='page-skill-standalone'>{escape(ui['sidebar'])}</button>",
            elem_id="page-skill-standalone-slot",
        )
    with gr.Accordion(ui["title"], open=False, elem_id="page-skill-panel"):
        gr.Markdown(ui["drawer_description"])
        with gr.Row():
            backend = gr.Dropdown(
                cli_choices(),
                value=cli["default"],
                label=ui["backend"],
                elem_id="page-skill-backend",
            )
            model = gr.Dropdown(
                [(ui["model_default"], "")],
                value="",
                label=ui["model"],
                elem_id="page-skill-model",
                elem_classes=["no-i18n-values"],
            )
        with gr.Row():
            catalog_note = gr.Markdown(elem_id="page-skill-model-status")
            reload_models = gr.Button(ui["model_refresh"], scale=0, min_width=94, elem_id="page-skill-refresh-models")
        with gr.Row():
            run = gr.Button(ui["run"], variant="primary", interactive=False, elem_id="page-skill-run")
            cancel = gr.Button(ui["cancel"], visible=False, elem_id="page-skill-cancel")
        status = gr.Markdown(ui["waiting"], elem_id="page-skill-status")
        download = gr.HTML(elem_id="page-skill-download")
        preview = gr.HTML(elem_id="page-skill-preview", elem_classes=["no-i18n"])
        with gr.Accordion(ui["options"], open=False):
            task = gr.Dropdown([], label=ui["task"], interactive=True, elem_id="page-skill-task")
        with gr.Accordion(ui["progress_tools"], open=False):
            scope = gr.JSON(label=ui["scope"])
            progress = gr.Textbox(label=ui["progress"], lines=5, max_lines=12, elem_id="page-skill-progress")
        events = gr.File(visible=False)
        with gr.Accordion(ui["history_tools"], open=False):
            history = gr.Dropdown([], label=ui["history"], interactive=True, elem_id="page-skill-history")
            with gr.Row():
                refresh = gr.Button(ui["refresh"], elem_id="page-skill-history-refresh")
                open_report = gr.Button(ui["open"], elem_id="page-skill-history-open")
        identifier = gr.State({"run": ""})
        selection = gr.State({"backend": cli["default"], "revision": 0, "task_available": False, "catalog": {}})
    timer = gr.Timer(cfg["limits"]["poll_seconds"], active=False)
    catalog = CatalogSelection([])

    def available_tasks(page_view):
        scope = CURRENT_PAGE.get()
        actual_module, actual_view = scope.view_label if scope and scope.view_label else (module, page_view)
        if actual_view == "unknown" and actual_module == module:
            actual_view = page_view
        if actual_module != module:
            return []
        return [(row["label"], key) for key, row in presets.items() if preset_matches_view(row, actual_view)]

    def begin(provider, state):
        state.update(backend=provider, revision=state["revision"] + 1, catalog={}, reload=False)
        return (
            state,
            gr.update(choices=[], value=None, interactive=False),
            ui["model_loading"],
            gr.update(interactive=False),
        )

    def load_models(state, force=False):
        provider, revision = state["backend"], state["revision"]
        result = catalog.load_data(provider, force)
        if state["revision"] != revision or state["backend"] != provider:
            return (gr.skip(),) * 3
        note = ui.get("model_" + result["status"], ui["catalog_unknown"])
        if provider == "workbuddy":
            if result["status"] == "missing":
                note = ui["workbuddy_setup"]
            if not result["rows"]:
                result = {**result, "status": "missing"}
        choices = model_options(result, provider, ui["model_default"])
        state["catalog"] = result
        return (
            gr.update(
                choices=choices,
                value=None if provider == "workbuddy" else "",
                interactive=bool(choices),
                allow_custom_value=provider in catalog_config()["manual_backends"],
            ),
            f"{composer_config()['backends'][provider]['label']} · {note}",
            gr.update(interactive=state["task_available"] and result["status"] != "missing"),
        )

    def selected(page_view, tracker, current, state):
        values = available_tasks(page_view)
        scope = CURRENT_PAGE.get()
        identity = (scope.owner, scope.revision) if scope else page_view
        same = tracker.get("scope") == identity
        if not same:
            tracker.update(run="", scope=identity)
        state["task_available"] = bool(values)
        initialized = bool(state["catalog"])
        state["reload"] = not initialized and state["revision"] == 0
        if not initialized:
            model_update, note, enabled = gr.skip(), gr.skip(), gr.update(interactive=False)
        else:
            model_update, note = gr.skip(), gr.skip()
            enabled = gr.update(interactive=bool(values) and state["catalog"]["status"] != "missing")
        valid = {key for _, key in values}
        return (
            gr.update(choices=values, value=current if same and current in valid else values[0][1] if values else None),
            state,
            model_update,
            note,
            enabled,
            gr.update(active=bool(tracker["run"])),
            gr.skip() if same else "",
            gr.skip() if same else (ui["waiting"] if values else ui["invalid"]),
            gr.skip() if same else "",
            gr.skip() if same else "",
            gr.skip() if same else gr.update(visible=False),
        )

    model_outputs = [model, catalog_note, run]
    opening = open_drawer.click(
        safe(selected, cancel_outputs=11),
        inputs=[view, identifier, task, selection],
        outputs=[task, selection, model, catalog_note, run, timer, preview, status, progress, download, cancel],
        queue=True,
        show_progress="hidden",
        trigger_mode="multiple",
    )
    opening.then(
        safe(lambda state: load_models(state) if state.get("reload") else (gr.skip(),) * 3, cancel_outputs=3),
        inputs=selection,
        outputs=model_outputs,
        queue=True,
        concurrency_limit=None,
        show_progress="hidden",
        trigger_mode="multiple",
    )
    backend.input(
        safe(begin, cancel_outputs=4),
        inputs=[backend, selection],
        outputs=[selection, *model_outputs],
        queue=False,
        trigger_mode="multiple",
    ).then(
        safe(load_models, cancel_outputs=3),
        inputs=selection,
        outputs=model_outputs,
        queue=True,
        concurrency_limit=None,
        show_progress="hidden",
        trigger_mode="multiple",
    )
    reload_models.click(
        safe(begin, cancel_outputs=4), inputs=[backend, selection], outputs=[selection, *model_outputs], queue=False
    ).then(
        safe(lambda state: load_models(state, True), cancel_outputs=3),
        inputs=selection,
        outputs=model_outputs,
        queue=True,
        concurrency_limit=None,
        show_progress="hidden",
    )

    def submit(key, backend, model, page_view, locale, tracker, state, *values):
        if key not in {name for _, name in available_tasks(page_view)}:
            return gr.skip(), gr.skip(), ui["invalid"], gr.skip(), gr.skip()
        if state["backend"] != backend or not state["catalog"]:
            return gr.skip(), gr.skip(), ui["model_changed"], gr.skip(), gr.skip()
        if backend == "workbuddy" and model not in {row["id"] for row in state["catalog"]["rows"]}:
            return gr.skip(), gr.skip(), ui["workbuddy_pick_model"], gr.skip(), gr.skip()
        provider = {
            "backend": backend,
            "model_name": model or "",
            "reasoning_effort": "",
            "language": "en" if locale == "en" else "zh",
        }
        context = {
            field: values[inputs.index(component)] for (preset, field), component in bound.items() if preset == key
        }
        try:
            # Discovery and normal chat eligibility do not establish strict research eligibility.
            capability(key, provider)
            preset = presets[key]
            fallback = preset.get("on_demand")
            if fallback:
                try:
                    evidence(preset, context)
                except ValueError as exc:
                    if str(exc) not in {ui["missing"], ui["stale"]} or CURRENT_PAGE.get() is None:
                        raise
                    params = {**fallback["defaults"], **context}
                    getattr(service, fallback["method"])(**params)
            row = start(key, provider, context)
        except (ValueError, BusinessError) as exc:
            return gr.skip(), gr.skip(), escape(ui_error_message(exc)), gr.skip(), gr.skip()
        tracker["run"] = row["run_id"]
        return tracker, row["request"], ui["running"], gr.update(active=True), gr.update(visible=True)

    run.click(lambda: ui["preparing"], outputs=status, queue=False).then(
        safe(submit, cancel_outputs=5),
        inputs=[task, backend, model, view, language, identifier, selection, *inputs],
        outputs=[identifier, scope, status, timer, cancel],
        queue=False,
    )

    def poll(tracker):
        page = CURRENT_PAGE.get()
        if page and tracker.get("scope") != (page.owner, page.revision):
            return (*(gr.skip() for _ in range(6)), gr.update(active=False), gr.update(visible=False))
        key = tracker.get("run")
        if not key:
            return tuple(gr.skip() for _ in range(8))
        service = InsightReportService()
        row = service.detail(key)
        recorded = service.store.events(key)
        result = list(_view(service, row, recorded))
        terminal = row["status"] != "running"
        result[0] = ui[
            {
                "running": "running",
                "completed": "ready",
                "partial": "ready",
                "failed": "failed",
                "cancelled": "cancelled",
            }.get(row["status"], "failed")
        ]
        if not terminal:
            stages = [item["text"] for item in recorded if item["kind"] in {"stage", "skill", "model"}]
            if stages:
                result[0] += " · " + escape(stages[-1])
        if row.get("error"):
            result[0] += " · " + escape(ui_error_message(ValueError(row["error"])))
        if row["status"] == "running" and any(item["kind"] == "cancellation" for item in recorded):
            result[0] = ui["stopping"] + " · " + key
        result[3] = (
            f'<a href="{escape(get_settings().api_prefix)}/insights/runs/{escape(key)}/files/report.html" download="report.html">{escape(ui["download"])}</a>'
            if result[3]
            else ""
        )
        if tracker.get("run") != key:
            return tuple(gr.skip() for _ in range(8))
        return (*result, gr.update(active=not terminal), gr.update(visible=not terminal))

    outputs = [status, progress, preview, download, events, history, timer, cancel]
    timer.tick(safe(poll, cancel_outputs=8), inputs=identifier, outputs=outputs, queue=False)

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
        if not key:
            return (gr.skip(),) * 8
        tracker["run"] = key
        return poll(tracker)

    open_report.click(safe(reopen, cancel_outputs=8), inputs=[history, identifier], outputs=outputs, queue=False)
