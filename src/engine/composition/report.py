"""Controlled offline HTML and interactive figures generated from actual execution."""

import json
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.strategy.composition.config import config

from .factor_report import factor_figures


def figures(result: dict[str, Any]) -> dict[str, go.Figure]:
    curve = result.get("curve") or {}
    equity = go.Figure()
    if curve.get("dates"):
        equity.add_trace(go.Scatter(x=curve["dates"], y=curve["equity"], name="组合净值金额"))
        equity.add_trace(go.Scatter(x=curve["dates"], y=curve["benchmark"], name="固定池价格基准"))
    target = result.get("targets") or {}
    weights = go.Figure(go.Bar(x=list(target), y=list(target.values()), name="目标权重"))
    weights.update_yaxes(tickformat=".0%")
    drawdown = go.Figure()
    if curve.get("dates"):
        drawdown.add_trace(go.Scatter(x=curve["dates"], y=curve["drawdown"], fill="tozeroy", name="回撤"))
        drawdown.update_yaxes(tickformat=".0%")
    stages = (result.get("diagnostics") or {}).get("stages") or []
    funnel = go.Figure(
        go.Bar(x=[row["node"] for row in stages], y=[row["passed"] for row in stages], name="末次通过数量")
    )
    charts = {"净值与基准": equity, "目标权重": weights, "回撤": drawdown, "末次阶段数量": funnel}
    charts.update(factor_figures(result))
    for title, figure in charts.items():
        figure.update_layout(
            template="plotly_white",
            title=title,
            height=320,
            margin={"l": 45, "r": 20, "t": 45, "b": 45},
            colorway=["#277fba", "#19a493", "#9271d7"],
        )
    return charts


def render(run: dict[str, Any], result: dict[str, Any]) -> str:
    directory = Path(__file__).with_name("templates")
    env = Environment(loader=FileSystemLoader(directory), autoescape=select_autoescape(["html"]))
    plots: list[str] = []
    for figure in figures(result).values():
        plots.append(
            figure.to_html(
                full_html=False,
                include_plotlyjs=True if not plots else False,
                config={"responsive": True, "displaylogo": False},
            )
        )
    display = {
        key: value
        for key, value in result.items()
        if key not in {"ledger", "orders", "trades", "internal_transfers", "curve"}
    }
    ui = config()["ui"]
    metric_rows = []
    for key, value in (result.get("metrics") or {}).items():
        if key not in ui["metrics"]:
            continue
        label, kind, hint = ui["metrics"][key]
        formatted = (
            "—"
            if value is None
            else (f"{value:.2%}" if kind == "percent" else f"{value:,.0f}" if kind == "integer" else f"{value:,.2f}")
        )
        metric_rows.append({"label": label, "value": formatted, "hint": hint})
    return env.get_template("report.html").render(
        run=run,
        result=result,
        plots=plots,
        ui=ui,
        metric_rows=metric_rows,
        details=json.dumps(display, ensure_ascii=False, indent=2),
        css=(directory / "report.css").read_text(encoding="utf-8"),
    )
