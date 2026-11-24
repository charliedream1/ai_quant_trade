"""Shared Plotly presentation without importing domain adapters."""

import plotly.graph_objects as go

FONT_FAMILY = "Microsoft YaHei, Segoe UI, Arial, sans-serif"
COLORS = {
    "ink": "#111a20",
    "muted": "#60727b",
    "grid": "#d8e7eb",
    "positive": "#d94c62",
    "negative": "#0b9f8f",
    "strategy": "#0b8f86",
    "benchmark": "#c2892d",
    "blue": "#2f74d0",
    "violet": "#805ad5",
}


def _style_figure(figure: go.Figure, title: str, height: int = 380) -> go.Figure:
    figure.update_layout(
        title={"text": f"<b>{title}</b>", "x": 0.02, "xanchor": "left", "font": {"size": 16, "color": COLORS["ink"]}},
        height=height,
        autosize=True,
        margin={"l": 58, "r": 28, "t": 72, "b": 48},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"family": FONT_FAMILY, "size": 12, "color": COLORS["ink"]},
        hovermode="x unified",
        hoverlabel={
            "bgcolor": "#18221f",
            "bordercolor": "#18221f",
            "font": {"family": FONT_FAMILY, "color": "#ffffff"},
        },
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1, "font": {"size": 11}},
        transition={"duration": 220},
    )
    figure.update_xaxes(
        gridcolor=COLORS["grid"],
        zerolinecolor="#bcc6c1",
        linecolor="#cfd6d3",
        tickfont={"color": COLORS["muted"]},
        fixedrange=False,
    )
    figure.update_yaxes(
        gridcolor=COLORS["grid"],
        zerolinecolor="#bcc6c1",
        linecolor="#cfd6d3",
        tickfont={"color": COLORS["muted"]},
        fixedrange=False,
    )
    return figure


def _base_figure(title: str, height: int = 380) -> go.Figure:
    return _style_figure(go.Figure(), title, height)


def empty_figure(title: str, message: str, height: int = 360) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        title={
            "text": f"<b>{title}</b>",
            "x": 0.02,
            "xanchor": "left",
            "font": {"size": 15, "color": COLORS["ink"]},
        },
        height=height,
        autosize=True,
        margin={"l": 24, "r": 24, "t": 58, "b": 24},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"family": FONT_FAMILY, "size": 12, "color": COLORS["ink"]},
    )
    figure.add_annotation(
        text=f"<b>{message}</b>",
        x=0.5,
        y=0.52,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"family": FONT_FAMILY, "size": 14, "color": COLORS["muted"]},
        bgcolor="#f5f7f6",
        bordercolor="#dce3df",
        borderpad=12,
    )
    figure.update_xaxes(visible=False, fixedrange=True)
    figure.update_yaxes(visible=False, fixedrange=True)
    return figure
