"""Presentation adapter for persisted, observable insight jobs."""

import json
from html import escape
from typing import Any

import gradio as gr
from src.data.manager import current_market
from src.engine.insights.service import InsightReportService


def _view(service: InsightReportService, run: dict[str, Any], events: list[dict[str, Any]]) -> tuple:
    ui = service.config["ui"]
    status = f"{ui.get(run['status'], run['status'])} · {run['run_id']}"
    if run.get("error"):
        status += " · " + run["error"]
    limit = service.config["defaults"]["max_event_chars"]
    lines = []
    for event in events:
        line = f"{event['time']} · {event['kind']} · {event['text']}"
        if event.get("data"):
            details = json.dumps(event["data"], ensure_ascii=False)
            excerpt_limit = service.config["defaults"]["event_data_excerpt_chars"]
            line += "\n" + details[:excerpt_limit] + (ui["excerpt"] if len(details) > excerpt_limit else "")
        lines.append(line)
    process = "\n\n".join(lines)[-limit:]
    html, report_path = "", None
    if run["status"] in {"completed", "partial"}:
        try:
            path = service.store.artifact(run["run_id"], "report.html")
            content = path.read_text(encoding="utf-8")
            report_path = str(path)
            html = (
                f'<iframe title="{escape(ui["report"])}" sandbox="allow-scripts" '
                f'style="width:100%;height:{service.config["defaults"]["preview_height"]}px;border:0;border-radius:16px" '
                f'srcdoc="{escape(content, quote=True)}"></iframe>'
            )
        except (OSError, ValueError):
            status += " · " + ui["missing_html"]
            html = f'<p role="status">{escape(ui["missing_html"])}</p>'
    try:
        event_path = str(service.store.artifact(run["run_id"], "events.jsonl"))
    except (OSError, ValueError):
        event_path = None
        process = process or ui["missing_events"]
    history = service.store.history(service.config["defaults"]["history_limit"])
    choices = [
        (
            f"{row.get('title') or row['request']['kind']} · {row['created_at']} · {ui.get(row['status'], row['status'])}",
            row["run_id"],
        )
        for row in history
    ]
    return (
        status,
        process,
        html,
        report_path,
        event_path,
        gr.update(choices=choices, value=run["run_id"]),
    )


class InsightsServiceMixin:
    def insight_history(self):
        service = InsightReportService()
        history = service.store.history(service.config["defaults"]["history_limit"])
        return gr.update(
            choices=[
                (f"{row.get('title') or row['request']['kind']} · {row['created_at']}", row["run_id"])
                for row in history
            ]
        )

    def insight_open(self, run_id: str):
        service = InsightReportService()
        return _view(service, service.detail(run_id), service.store.events(run_id))

    def insight_run(
        self,
        kind: str,
        backend: str,
        symbol: str,
        model_id: Any,
        model_name: str,
        effort: str,
        timeframe: str,
        end_date: str,
    ):
        service = InsightReportService()
        try:
            run = service.start(
                {
                    "kind": kind,
                    "backend": backend,
                    "symbol": symbol,
                    "market": current_market(),
                    "model_id": int(model_id) if model_id else None,
                    "model_name": model_name,
                    "reasoning_effort": effort if effort != service.config["ui"]["effort_choices"][0] else "",
                    "timeframe": timeframe,
                    "end_date": end_date,
                }
            )
            events: list[dict[str, Any]] = []
            for update in service.follow(run["run_id"]):
                events.extend(update["events"])
                yield _view(service, update["run"], events)
        except Exception as exc:
            yield str(exc), "", "", None, None, gr.update()
