"""Controlled, self-contained report HTML; model output is always escaped."""

import json
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape
from plotly.subplots import make_subplots


def charts(evidence: dict[str, Any], config: dict[str, Any]) -> list[str]:
    figures: list[str] = []
    colors = config["defaults"]
    for source in evidence["sources"]:
        kind, rows = source["kind"], source["data"]
        if kind in {"indices", "sectors"}:
            valid = [row for row in rows if isinstance(row.get("change_pct"), (float, int))]
            if not valid:
                continue
            figure = go.Figure(
                go.Bar(
                    x=[row.get("name") or row.get("code") for row in valid],
                    y=[row["change_pct"] for row in valid],
                    marker_color=[
                        colors["positive_color"] if row["change_pct"] >= 0 else colors["negative_color"]
                        for row in valid
                    ],
                )
            )
            figure.update_layout(title=config["ui"]["chart_" + kind])
        elif kind == "price_history":
            valid = [
                row
                for row in rows
                if all(isinstance(row.get(key), (float, int)) for key in ("open", "high", "low", "close"))
            ]
            if not valid:
                continue
            x = [row["date"] for row in valid]
            figure = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25])
            figure.add_trace(
                go.Candlestick(
                    x=x,
                    open=[r["open"] for r in valid],
                    high=[r["high"] for r in valid],
                    low=[r["low"] for r in valid],
                    close=[r["close"] for r in valid],
                    increasing_line_color=colors["positive_color"],
                    decreasing_line_color=colors["negative_color"],
                ),
                row=1,
                col=1,
            )
            figure.add_trace(go.Bar(x=x, y=[r.get("volume") for r in valid], name="volume"), row=2, col=1)
            figure.update_layout(title=config["ui"]["chart_price"], xaxis_rangeslider_visible=False)
            figure.update_xaxes(tickformat="%Y-%m")
        else:
            continue
        figure.update_layout(
            template="plotly_white",
            height=colors["chart_height"],
            margin={"l": 45, "r": 25, "t": 55, "b": 60},
            colorway=colors["chart_colors"],
            showlegend=False,
        )
        figures.append(
            figure.to_html(
                full_html=False,
                include_plotlyjs=True if not figures else False,
                config={"responsive": True, "displaylogo": False},
            )
        )
    return figures


def render_report(report: dict[str, Any], evidence: dict[str, Any], run: dict[str, Any], config: dict[str, Any]) -> str:
    directory = Path(__file__).with_name("templates")
    environment = Environment(loader=FileSystemLoader(directory), autoescape=select_autoescape(["html"]))
    sources = [
        {**row, "formatted": json.dumps(row["data"], ensure_ascii=False, indent=2)} for row in evidence["sources"]
    ]
    return environment.get_template("report.html").render(
        report=report,
        evidence=evidence,
        run=run,
        ui=config["ui"],
        sources=sources,
        charts=charts(evidence, config),
        css=(directory / "report.css").read_text(encoding="utf-8"),
    )
