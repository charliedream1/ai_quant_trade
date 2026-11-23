"""Explicit Skill graph actions; read/filter/export never regenerate a result."""

from datetime import date
from html import escape
from time import monotonic, sleep
from uuid import uuid4

import gradio as gr

from src.agent.cli_catalog import catalog_config
from src.agent.composer_config import cli_choices
from src.core.diagnostics_config import diagnostics_config
from src.core.page_work import check as check_page
from src.data import current_market
from src.engine.market.model_graph.config import config
from src.engine.market.model_graph.generation import availability
from src.engine.market.model_graph.service import GraphResearchService
from src.frontend.common.callbacks import safe
from src.frontend.common.composer_catalog import bind_cli_catalog
from src.frontend.service.model_relation_visuals import model_relation_figure


def describe_status(row):
    message = "<p>" + escape(row["status"]) + "</p>"
    if row.get("error_message"):
        message += "<pre>" + escape(row["error_message"]) + "</pre>"
    return message


def render_result(identifier, include_inferences):
    service = GraphResearchService()
    row = service.detail(identifier)
    if row["status"] not in {"completed", "partial"}:
        return f"{identifier}: {row['status']}", {}, None, ""
    graph = service.result(identifier, include_inferences)
    figure = model_relation_figure(graph, row["request"]["symbol"])
    return (
        f"{row['request']['symbol']} · {row['request']['market']} · {row['request']['as_of']} · "
        f"{identifier}: {row['status']} · {len(graph['edges'])} visible edges",
        graph,
        figure,
        evidence_markup(graph),
    )


def evidence_markup(graph):
    parts = []
    sources = {row["id"]: row for row in graph.get("evidence", [])}
    for edge in graph.get("edges", []):
        header = escape(f"{edge['source']} → {edge['target']} · {edge['relation_type']} · {edge['classification']}")
        parts.append("<details><summary>" + header + "</summary><p>" + escape(edge["description"]) + "</p>")
        parts.append("<p>" + escape(edge.get("review_reason", "")) + "</p>")
        parts.append("<p>" + escape(edge.get("temporal_status", "")) + "</p>")
        for original in edge["evidence_items"]:
            parts.append("<blockquote>" + escape(original["quote"]) + "</blockquote>")
            parts.append("<p>" + escape(str(original["published_at"] or "Undated original; observed now")) + "</p>")
            if original["url"]:
                parts.append(
                    '<a target="_blank" rel="noopener noreferrer" href="'
                    + escape(original["url"], quote=True)
                    + '">'
                    + escape(original["title"])
                    + "</a>"
                )
            else:
                parts.append("<p>" + escape(original["title"]) + " · " + escape(original["source_id"]) + "</p>")
            source = sources.get(original["source_id"])
            if source:
                parts.append(
                    "<details><summary>Frozen original context</summary><pre>"
                    + escape(source["text"])
                    + "</pre></details>"
                )
        parts.append("</details>")
    return "".join(parts) or "<p>No supported edges in the current filter.</p>"


def render_model_graph_panel():
    service = GraphResearchService()
    # Keep original citations and English workflow labels out of substring translation.
    with gr.Group(elem_id="model-relation-panel", elem_classes=["no-i18n"]) as panel:
        with gr.Column(elem_classes=["no-i18n"]):
            gr.Markdown(config()["ui"]["help"])
            with gr.Row():
                symbol = gr.Textbox(label="Target stock", value="")
                backend = gr.Dropdown(
                    cli_choices(config()["providers"]), value=config()["default_backend"], label="Graph CLI backend"
                )
                model = gr.Dropdown(
                    [(catalog_config()["labels"]["default"], "")],
                    value="",
                    allow_custom_value=True,
                    label="CLI model (blank uses provider default)",
                    elem_id="model-graph-cli-model",
                )
                reload_models = gr.Button("刷新模型", scale=0)
                effort = gr.Dropdown(["", "low", "medium", "high", "xhigh"], value="", label="Reasoning effort")
            catalog_note = gr.Markdown()
            bind_cli_catalog(backend, model, reload_models, catalog_note, config()["default_backend"])
            with gr.Row():
                as_of = gr.Textbox(value=date.today().isoformat(), label="Graph as-of date")
                lookback = gr.Number(
                    value=config()["limits"]["lookback_days"], precision=0, label="Source lookback days"
                )
                depth = gr.Slider(1, config()["limits"]["rounds"], value=1, step=1, label="Maximum research rounds")
            urls = gr.Textbox(label="Original public URLs (one per line)", lines=3)
            with gr.Accordion("Authorized knowledge evidence", open=False):
                library = gr.Textbox(label="Knowledge library (optional)")
                document_ids = gr.Textbox(label="Selected document IDs (comma separated, optional)")
                session = gr.Textbox(label="Attachment session (optional)")
            with gr.Row():
                generate = gr.Button("Generate Skill graph", variant="primary", elem_id="model-graph-generate")
                cancel = gr.Button("Cancel graph research", elem_id="model-graph-cancel")
                refresh = gr.Button("Refresh graph status")
                check = gr.Button("Check CLI availability")
            providers = gr.JSON(label="Actual provider availability")
            identifier = gr.Textbox(label="Graph run ID", elem_id="model-graph-run-id")
            polling = gr.Timer(value=1, active=False)
            history = gr.Dropdown([], label="Previous graph runs", interactive=True)
            history_refresh = gr.Button("Refresh graph history")
            include = gr.Checkbox(
                label="Include model inferences / expired candidates", value=False, elem_id="model-graph-include"
            )
            status = gr.Markdown(elem_id="model-graph-status")
            events = gr.JSON(label="Graph research progress")
            view = gr.Button("Open saved graph", elem_id="model-graph-open")
            plot = gr.Plot(label="Evidence-grounded stock relationships", elem_id="model-graph-plot")
            evidence = gr.HTML(elem_id="model-graph-evidence")
            result = gr.JSON(label="Saved graph result")
            export = gr.Button("Export this saved graph", elem_id="model-graph-export")
            artifact = gr.File(label="Graph JSON export")
            html_export = gr.Button("保存关系图谱 HTML", elem_id="model-graph-html-export")
            html_preview = gr.HTML(elem_id="model-graph-html-preview")
            html_file = gr.File(label="关系图谱 HTML")

            def start(target, provider, name, reasoning, end, days, rounds, public_urls, lib, ids, attachment):
                if provider == "workbuddy" and not name:
                    raise ValueError(config()["workbuddy"]["messages"]["model"])
                request = {
                    "symbol": target,
                    "market": current_market(),
                    "backend": provider,
                    "model_name": name,
                    "reasoning_effort": reasoning,
                    "as_of": end,
                    "lookback_days": int(days),
                    "depth": int(rounds),
                    "urls": [url.strip() for url in public_urls.splitlines() if url.strip()],
                    "library_name": lib,
                    "document_ids": [int(item.strip()) for item in ids.split(",") if item.strip()],
                    "session_id": attachment,
                }
                row = service.start(request)
                return row["run_id"], row["status"], gr.update(active=True)

            generate.click(
                safe(start),
                inputs=[symbol, backend, model, effort, as_of, lookback, depth, urls, library, document_ids, session],
                outputs=[identifier, status, polling],
            )

            def poll(key):
                if not key:
                    return "", [], gr.update(active=False)
                row = service.detail(key)
                return (
                    describe_status(row),
                    service.store.events(key),
                    gr.update(active=row["status"] in {"queued", "running"}),
                )

            polling.tick(safe(poll), inputs=identifier, outputs=[status, events, polling], queue=False)
            check.click(safe(availability), outputs=providers)

            def cancel_run(key):
                if not key:
                    return
                policy = diagnostics_config()["rules"]
                service.store.cancel(key)
                deadline = monotonic() + policy["shutdown_seconds"]
                yield "Cancellation requested"
                while monotonic() < deadline:
                    check_page()
                    row = service.detail(key)
                    if row["status"] not in {"queued", "running"}:
                        yield describe_status(row)
                        return
                    sleep(policy["poll_seconds"])

            cancel.click(safe(cancel_run), inputs=identifier, outputs=status, show_progress="hidden")
            refresh.click(
                safe(lambda key: (describe_status(service.detail(key)), service.store.events(key))),
                inputs=identifier,
                outputs=[status, events],
            )
            history_refresh.click(
                safe(
                    lambda: gr.update(
                        choices=[
                            (f"{row['request']['symbol']} · {row['status']} · {row['created_at']}", row["run_id"])
                            for row in service.store.history()
                        ]
                    )
                ),
                outputs=history,
            )
            history.change(lambda key: key, inputs=history, outputs=identifier)
            view.click(safe(render_result), inputs=[identifier, include], outputs=[status, result, plot, evidence])
            include.change(safe(render_result), inputs=[identifier, include], outputs=[status, result, plot, evidence])

            def export_saved(key):
                service.store.result(key)
                return str(service.store.directory(key) / "graph.json")

            export.click(safe(export_saved), inputs=identifier, outputs=artifact)

            def save_html(key, with_inferences):
                row = service.detail(key)
                graph = service.result(key, with_inferences)
                title = escape(f"{row['request']['symbol']} · {row['request']['as_of']} · Relationship report")
                document = (
                    '<!doctype html><html lang="en"><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    f"<title>{title}</title><main><h1>{title}</h1>{evidence_markup(graph)}</main></html>"
                )
                filename = "report-with-inferences.html" if with_inferences else "report.html"
                path = service.store.directory(key) / filename
                temporary = path.with_name(f"{uuid4().hex}.pending")
                temporary.write_text(document, encoding="utf-8")
                temporary.replace(path)
                return (
                    f'<iframe sandbox title="Relationship report" srcdoc="{escape(document)}" style="width:100%;height:440px;border:0"></iframe>',
                    str(path),
                )

            html_export.click(safe(save_html), inputs=[identifier, include], outputs=[html_preview, html_file])
    return panel
