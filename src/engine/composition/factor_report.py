"""Factor-only research charts, emitted only when actual metrics are present."""

from typing import Any

import plotly.graph_objects as go

from src.strategy.factors.config import factor_config


def factor_figures(result: dict[str, Any]) -> dict[str, go.Figure]:
    cfg = factor_config()
    records = (result.get("diagnostics") or {}).get("factor_diagnostics") or {}
    charts = {}
    for node, detail in records.items():
        metrics = detail.get("research", {}).get("metrics", {})
        valid = {key: row for key, row in metrics.items() if row.get("rank_ic_mean") is not None}
        if valid:
            labels = [cfg["factors"].get(key, {}).get("label", key) for key in valid]
            figure = go.Figure(
                go.Bar(
                    x=labels,
                    y=[row["rank_ic_mean"] for row in valid.values()],
                    name="历史平均RankIC",
                    customdata=[[row["samples"], row["label_end"]] for row in valid.values()],
                    hovertemplate="%{x}<br>平均RankIC %{y:.3f}<br>有效日期 %{customdata[0]}<br>标签截止 %{customdata[1]}<extra></extra>",
                )
            )
            figure.update_yaxes(range=[-1, 1])
            charts[node + " · 因子有效性（研究相关性，非收益）"] = figure
        observations: dict[str, Any] = detail.get("observations") or {}
        first = next(iter(observations.values()), None)
        weights = (first.get("factor_weights") or {}) if first else {}
        if weights:
            figure = go.Figure(
                go.Bar(
                    x=[cfg["factors"].get(key, {}).get("label", key) for key in weights],
                    y=list(weights.values()),
                    name="合成评分权重",
                )
            )
            figure.update_yaxes(tickformat=".0%", range=[0, 1])
            charts[node + " · 因子权重（非资金权重）"] = figure
    return charts
