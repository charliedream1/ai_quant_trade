"""Translate economic snapshots into tables, independent axes and report previews."""

import calendar
import math
from datetime import date
from html import escape

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.agent.model_catalog import list_models
from src.core.exceptions import BusinessError, ErrorCode
from src.core.panel_updates import panel_ready
from src.core.redaction import redact_text
from src.data import current_market
from src.engine.economics.config import economics_config
from src.engine.economics.service import EconomicAnalysis
from src.engine.insights.service import InsightReportService

from .home_tables import home_styled_frame


def economic_figure(snapshot: dict):
    cfg = economics_config()
    if snapshot["kind"] == "macro":
        groups = snapshot["overview"]
        rows = max(1, math.ceil(len(groups) / 2))
        figure = make_subplots(
            rows=rows, cols=2, subplot_titles=[row["label"] + " (" + row["unit"] + ")" for row in groups]
        )
        for index, series in enumerate(groups):
            selected = [row for row in snapshot["observations"] if row["series"] == series["series"]]
            figure.add_trace(
                go.Scatter(
                    x=[r["observation_date"] for r in selected],
                    y=[r["value"] for r in selected],
                    mode="lines+markers",
                    name=series["label"],
                ),
                row=index // 2 + 1,
                col=index % 2 + 1,
            )
    else:
        rows = 2
        figure = make_subplots(
            rows=2, cols=1, subplot_titles=["累计营收与归母利润（CNY）", "报告期毛利率与加权ROE（%）"]
        )
        for key in ("revenue", "profit", "gross_margin", "roe"):
            definition = cfg["fields"][key]
            figure.add_trace(
                go.Scatter(
                    x=[r["report_period"] for r in snapshot["periods"]],
                    y=[r["metrics"][key] for r in snapshot["periods"]],
                    mode="lines+markers",
                    name=definition["label"],
                ),
                row=1 if definition["unit"] == "CNY" else 2,
                col=1,
            )
    figure.update_layout(
        template="plotly_white",
        height=cfg["defaults"]["chart_height"] * rows,
        margin={"t": 50, "b": 35},
        showlegend=snapshot["kind"] != "macro",
    )
    return figure


def economic_table(snapshot):
    if snapshot["kind"] == "macro":
        history: dict[str, dict[str, float | None]] = {}
        for observation in snapshot["observations"]:
            history.setdefault(observation["series"], {})[observation["observation_date"]] = observation["value"]
        return pd.DataFrame(
            [
                {
                    "指标": r["label"],
                    "观察期": r["observation_date"],
                    "数值": r["value"],
                    "单位": r["unit"],
                    "口径": r["basis"],
                    "过期": r["stale"],
                    "发布时间": r["published_at"],
                    "较上期": _previous_change(r, history),
                }
                for r in snapshot["overview"]
            ]
        )
    definitions = {**economics_config()["fields"], **economics_config()["derived"]}
    selected = snapshot["selected"]
    rows = []
    for key, value in selected["metrics"].items():
        definition = definitions[key]
        row = {
            "指标": definition["label"],
            "报告期": selected["report_period"],
            "单位": definition["unit"],
            snapshot["name"]: value,
            "状态": selected["statuses"].get(key, "missing" if value is None else "available"),
        }
        for peer in snapshot["peers"]:
            row[peer["symbol"]] = peer["metrics"].get(key)
        rows.append(row)
    return pd.DataFrame(rows)


def _previous_change(row, history):
    values = history.get(row["series"], {})
    earlier = [stamp for stamp in values if stamp < row["observation_date"]]
    if not earlier or row["value"] is None:
        return None
    previous = values[max(earlier)]
    return row["value"] - previous if previous is not None else None


def report_view(service, run):
    process = "\n".join(event["text"] for event in service.store.events(run["run_id"]) if event["kind"] != "message")
    status = run["run_id"] + " · " + run["status"]
    if run.get("error"):
        error = str(run["error"])
        if any(code in error.lower() for code in ("getaddrinfo", "name resolution", "name or service not known")):
            error = economics_config()["messages"]["report_dns"]
        status += " · " + redact_text(error)
    path, preview = None, ""
    if run["status"] in {"completed", "partial"}:
        report = service.store.artifact(run["run_id"], "report.html")
        path = str(report)
        preview = f'<iframe title="Economic analysis report" sandbox="allow-scripts" style="width:100%;height:{economics_config()["defaults"]["preview_height"]}px;border:0" srcdoc="{escape(report.read_text(encoding="utf-8"), quote=True)}"></iframe>'
    return status + "\n" + process, preview, path, run["run_id"]


class EconomicUIMixin:
    def economic_models(self):
        return [(economics_config()["ui"]["default_model"], 0)] + [
            (row["name"], row["id"]) for row in list_models() if row["enabled"]
        ]

    def economic_load(self, kind, series, symbol, period, peers, refresh):
        if current_market() != "CN":
            raise BusinessError(ErrorCode.INVALID_PARAM, economics_config()["messages"]["unsupported"])
        if kind != "macro":
            symbol = str(symbol or "").strip()
            if not symbol:
                raise BusinessError(
                    ErrorCode.MISSING_PARAM, "Enter an A-share code or company name before loading financials"
                )
            period = str(period or "").strip()
            if period:
                try:
                    value = date.fromisoformat(period)
                    if value.month not in (3, 6, 9, 12) or value.day != calendar.monthrange(value.year, value.month)[1]:
                        raise ValueError("Not a quarter end")
                except ValueError as exc:
                    raise BusinessError(ErrorCode.INVALID_PARAM, "Use a calendar-quarter endpoint YYYY-MM-DD") from exc
        service = EconomicAnalysis()
        snapshot = (
            service.macro(series, refresh=refresh, market=current_market())
            if kind == "macro"
            else service.fundamentals(
                symbol,
                period=period,
                peers=[p.strip() for p in peers.split(",") if p.strip()],
                refresh=refresh,
                market=current_market(),
            )
        )
        status = "快照 `" + snapshot["snapshot_id"] + "` · " + snapshot["scope"]
        if snapshot["gaps"]:
            status += "\n\n" + "；".join(snapshot["gaps"])
        panel_ready(0, status)
        overview = economic_table(snapshot)
        if kind == "macro" and isinstance(overview, pd.DataFrame):
            overview = home_styled_frame(overview, extra_signed_columns=("较上期",), scale_group="单位")
        panel_ready(1, overview)
        panel_ready(3, snapshot)
        panel_ready(4, snapshot["snapshot_id"])
        chart = economic_figure(snapshot)
        panel_ready(2, chart)
        return status, overview, chart, snapshot, snapshot["snapshot_id"]

    def economic_report(self, kind, identifier, model_id):
        data = EconomicAnalysis().store.read(identifier)
        service = InsightReportService()
        run = service.start(
            {
                "kind": "macro_analysis" if kind == "macro" else "fundamental_analysis",
                "market": current_market(),
                "symbol": data.get("symbol", ""),
                "research_snapshot": identifier,
                "model_id": int(model_id) if model_id else None,
                "backend": "api",
            }
        )
        for update in service.follow(run["run_id"]):
            yield report_view(service, update["run"])

    def economic_open(self, run_id):
        service = InsightReportService()
        return report_view(service, service.detail(run_id))
