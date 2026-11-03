"""Small Plotly figures with explicit units and honest empty states for the homepage."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from .home_config import color, home_config, label, limit
from .home_data import HomeAccount, number


def figure(title: str, *, market: bool = False) -> go.Figure:
    result = go.Figure()
    result.update_layout(
        title={"text": title, "x": 0.04, "font": {"size": 15}},
        height=limit("market_plot_height" if market else "plot_height"),
        margin={"l": 48, "r": 24, "t": 45, "b": 42},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Microsoft YaHei, Segoe UI, sans-serif", "size": 12, "color": "#526277"},
        legend={"orientation": "h", "y": -0.15},
    )
    result.update_xaxes(showgrid=False, zeroline=False)
    result.update_yaxes(gridcolor="rgba(140,155,175,.16)", zerolinecolor="rgba(140,155,175,.3)")
    return result


def empty(title: str, message: str) -> go.Figure:
    result = figure(title)
    result.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    result.update_xaxes(visible=False)
    result.update_yaxes(visible=False)
    return result


def account_trend(snapshot: HomeAccount) -> go.Figure:
    rows = [row for row in snapshot.history if number(row.get("net_value")) is not None and float(row["net_value"]) > 0]
    if not rows:
        return empty("账户净值 · 已保存快照", label("live_basis" if snapshot.mode == "live" else "empty_history"))
    result = figure("账户净值 · 已保存快照<br><sup>悬停查看每日单位净值；只使用已保存快照</sup>")
    result.add_scatter(
        x=[row["nav_date"] for row in rows],
        y=[float(row["net_value"]) for row in rows],
        mode="lines+markers",
        name="单位净值",
        line={"color": color("blue"), "width": 3},
        marker={"size": 5},
        hovertemplate="%{x}<br>净值 %{y:.4f}<extra></extra>",
    )
    result.update_yaxes(title="单位净值", autorange=True, rangemode="normal", tickformat=".3f")
    result.update_xaxes(tickformat="%m-%d", nticks=limit("date_ticks"))
    return result


def allocation(snapshot: HomeAccount) -> go.Figure:
    if snapshot.total_asset is None or snapshot.cash is None or snapshot.total_asset <= 0:
        return empty("资金配置", label("live_basis" if snapshot.mode == "live" else "empty_account"))
    rows = sorted(snapshot.holdings, key=lambda row: float(row["market_value"]), reverse=True)
    names = [str(row["name"]) for row in rows[: limit("contributions")]]
    values = [float(row["market_value"]) for row in rows[: limit("contributions")]]
    remainder = sum(float(row["market_value"]) for row in rows[limit("contributions") :])
    if remainder:
        names.append("其余持仓")
        values.append(remainder)
    names.append("现金")
    values.append(snapshot.cash)
    result = figure("资金配置 · 现金与持仓<br><sup>扇区越大表示金额越高；悬停查看占比</sup>")
    result.add_pie(
        labels=names,
        values=values,
        hole=0.72,
        sort=False,
        marker={"colors": home_config()["colors"]["palette"]},
        textinfo="percent",
        hovertemplate="%{label}<br>%{value:,.2f} 元 · %{percent}<extra></extra>",
    )
    result.update_layout(margin={"l": 18, "r": 18, "t": 45, "b": 38})
    result.add_annotation(text=f"{snapshot.total_asset / 10000:,.2f}<br>万元", x=0.5, y=0.5, showarrow=False)
    return result


def contribution(snapshot: HomeAccount) -> go.Figure:
    rows = [row for row in snapshot.holdings if number(row.get("float_pnl")) is not None]
    if not rows:
        return empty("持仓浮动盈亏", "暂无有效持仓估值；不代表今日盈亏为零。")
    rows = sorted(rows, key=lambda row: abs(float(row["float_pnl"])), reverse=True)[: limit("contributions")]
    rows.sort(key=lambda row: float(row["float_pnl"]))
    values = [float(row["float_pnl"]) for row in rows]
    result = figure(f"{label('floating_pnl')}<br><sup>红色为盈利、绿色为亏损；悬停查看金额</sup>", market=True)
    result.add_bar(
        y=[row["name"] for row in rows],
        x=values,
        orientation="h",
        marker_color=[color("gain") if value >= 0 else color("loss") for value in values],
        text=[f"{value:+,.0f}" for value in values],
        textposition="auto",
        hovertemplate="%{y}<br>浮动盈亏 %{x:+,.2f} 元<extra></extra>",
    )
    result.update_xaxes(title="元")
    return result


def sector_heatmap(sectors: list[dict[str, Any]]) -> go.Figure:
    rows = [row for row in sectors if number(row.get("change_pct")) is not None]
    if not rows:
        return empty("板块样本热力图", label("missing_market"))
    weighted = all((number(row.get("amount")) or 0) > 0 for row in rows)
    values = [float(row["amount"]) if weighted else 1.0 for row in rows]
    changes = [float(row["change_pct"]) for row in rows]
    bound = max(abs(value) for value in changes) or 1.0
    result = figure(f"板块样本 · {len(rows)} 个 · {'面积=成交额' if weighted else '等面积（规模缺失）'}", market=True)
    result.add_treemap(
        labels=[str(row.get("name") or row.get("code")) for row in rows],
        parents=[""] * len(rows),
        values=values,
        customdata=changes,
        texttemplate="%{label}<br>%{customdata:+.2f}%",
        marker={
            "colors": changes,
            "colorscale": [[0, color("heat_loss")], [0.5, color("neutral")], [1, color("heat_gain")]],
            "cmin": -bound,
            "cmax": bound,
            "colorbar": {"title": "%", "thickness": 10},
        },
        hovertemplate="%{label}<br>涨跌幅 %{customdata:+.2f}%<extra></extra>",
        textfont={"color": "#152536"},
        pathbar={"visible": False},
    )
    result.update_layout(margin={"l": 8, "r": 40, "t": 48, "b": 8})
    return result


def risk_radar(snapshot: HomeAccount) -> go.Figure:
    values = [
        snapshot.exposure * 100 if snapshot.exposure is not None else None,
        snapshot.concentration * 100 if snapshot.concentration is not None else None,
        abs(snapshot.drawdown) * 100 if snapshot.drawdown is not None else None,
    ]
    if snapshot.exposure is None and snapshot.concentration is None and snapshot.drawdown is None:
        return empty("风险雷达", "暂无账户风险数据")
    result = figure("风险雷达 · 观察值<br><sup>越靠外风险占用越高；参考线不触发交易</sup>")
    labels = ["仓位暴露", "单票集中度", "快照回撤"]
    result.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself" if all(value is not None for value in values) else "none",
            name="当前",
            line={"color": color("amber")},
            fillcolor="rgba(191,132,33,.18)",
        )
    )
    result.update_layout(
        polar={"radialaxis": {"range": [0, 100], "ticksuffix": "%"}},
        showlegend=False,
        margin={"l": 32, "r": 32, "t": 45, "b": 24},
    )
    return result


def sentiment_radar(indices: list[dict[str, Any]], sectors: list[dict[str, Any]]) -> go.Figure:
    index_changes = [value for row in indices if (value := number(row.get("change_pct"))) is not None]
    sector_changes = [value for row in sectors if (value := number(row.get("change_pct"))) is not None]
    if not index_changes and not sector_changes:
        return empty("市场情绪雷达", "暂无指数或板块数据")
    breadth = sum(1 for value in sector_changes if value > 0) / len(sector_changes) * 100 if sector_changes else None
    index_score = min(max(50 + sum(index_changes) / len(index_changes) * 20, 0), 100) if index_changes else None
    dispersion = min(max(100 - abs(max(sector_changes) - min(sector_changes)) * 10, 0), 100) if sector_changes else None
    result = figure("市场情绪雷达 · 代理指标<br><sup>综合指数动量、板块广度与一致性，不代表买卖信号</sup>")
    labels = ["指数动量", "板块广度", "板块一致性"]
    values = [index_score, breadth, dispersion]
    result.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself" if all(value is not None for value in values) else "none",
            name="代理情绪",
            line={"color": color("cyan")},
            fillcolor="rgba(24,168,186,.18)",
        )
    )
    result.update_layout(
        polar={"radialaxis": {"range": [0, 100], "ticksuffix": "分"}},
        showlegend=False,
        margin={"l": 32, "r": 32, "t": 45, "b": 24},
    )
    return result
