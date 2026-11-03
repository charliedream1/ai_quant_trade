"""Shared frontend visuals."""

from __future__ import annotations

from html import escape

from src.data.relation_evidence import graph_config

from .execution_costs import cost_markdown
from .foundation import (
    BACKTEST_ATTRIBUTION_COLUMNS,
    BACKTEST_METRIC_EXPLANATIONS,
    COLORS,
    FONT_FAMILY,
    METRIC_LABELS,
    RELATION_ANALYSIS_COLUMNS,
    RELATION_TYPE_COLORS,
    RELATION_TYPE_LABELS,
    SHANGHAI_TZ,
    Any,
    Sequence,
    _local_now,
    _optional_id,
    _safe_float,
    datetime,
    go,
    make_subplots,
    pd,
    re,
    timedelta,
    timezone,
    to_frame,
)
from .relation_layout import bounds as graph_bounds
from .relation_layout import positions as graph_positions


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


def market_bar_figure(sectors: Sequence[dict[str, Any]]) -> go.Figure:
    if not sectors:
        return empty_figure("板块强弱排名", "暂无板块行情")
    ranked = sorted(sectors, key=lambda item: float(item.get("change_pct") or 0))
    names = [str(item.get("name") or item.get("code") or "-") for item in ranked]
    values = [float(item.get("change_pct") or 0) for item in ranked]
    colors = [COLORS["positive"] if value >= 0 else COLORS["negative"] for value in values]
    custom = [
        [
            item.get("leader") or "-",
            float(item.get("amount") or 0) / 100000000,
            item.get("up_count") or 0,
            item.get("down_count") or 0,
        ]
        for item in ranked
    ]
    figure = _base_figure("板块强弱排名", max(340, min(540, 150 + len(ranked) * 38)))
    figure.add_bar(
        x=values,
        y=names,
        orientation="h",
        marker={"color": colors, "line": {"color": "rgba(255,255,255,.7)", "width": 1}},
        text=[f"{value:+.2f}%" for value in values],
        textposition="outside",
        cliponaxis=False,
        customdata=custom,
        hovertemplate=(
            "<b>%{y}</b><br>涨跌幅 %{x:+.2f}%<br>领涨股 %{customdata[0]}"
            "<br>成交额 %{customdata[1]:,.1f} 亿<br>上涨 / 下跌 %{customdata[2]} / %{customdata[3]}<extra></extra>"
        ),
    )
    padding = max(max(abs(value) for value in values) * 0.28, 0.5)
    figure.update_xaxes(
        title="涨跌幅 (%)", range=[min(values + [0]) - padding, max(values + [0]) + padding], ticksuffix="%"
    )
    figure.update_yaxes(title=None, showgrid=False, automargin=True)
    figure.update_layout(showlegend=False, bargap=0.34)
    return figure


def keyword_figure(items: Sequence[dict[str, Any]]) -> go.Figure:
    if not items:
        return empty_figure("新闻关键词强度", "暂无关键词数据", 330)
    ranked = sorted(items, key=lambda item: float(item.get("weight") or item.get("count") or 0))[-12:]
    words = [str(item.get("keyword") or item.get("word") or "-") for item in ranked]
    weights = [float(item.get("weight") or item.get("count") or 0) for item in ranked]
    counts = [int(item.get("count") or 0) for item in ranked]
    figure = _base_figure("新闻关键词强度", 330)
    figure.add_bar(
        x=weights,
        y=words,
        orientation="h",
        marker={"color": weights, "colorscale": [[0, "#d9e9e3"], [1, COLORS["strategy"]]], "showscale": False},
        customdata=counts,
        hovertemplate="<b>%{y}</b><br>权重 %{x:.3f}<br>出现次数 %{customdata}<extra></extra>",
    )
    figure.update_xaxes(title="权重", showgrid=True)
    figure.update_yaxes(showgrid=False)
    figure.update_layout(showlegend=False, bargap=0.3)
    return figure


def _column_counts(frame: Any, column: str, limit: int = 8) -> list[tuple[str, int]]:
    """Count non-empty values of a DataFrame column, sorted by frequency."""

    if not isinstance(frame, pd.DataFrame) or column not in frame.columns or frame.empty:
        return []
    series = frame[column].dropna().astype(str).str.strip()
    series = series[series != ""]
    counts = series.value_counts().head(limit)
    return [(str(key), int(value)) for key, value in counts.items()]


def _distribution_figure(
    title: str,
    left_column: str,
    right_column: str,
    frame: Any,
    height: int = 320,
    left_label: str | None = None,
    right_label: str | None = None,
) -> go.Figure:
    """Two-panel categorical distribution (bar + donut) used by list pages."""

    left_counts = _column_counts(frame, left_column)
    right_counts = _column_counts(frame, right_column)
    if not left_counts and not right_counts:
        return empty_figure(title, "暂无统计数据", height)
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(left_label or left_column, right_label or right_column),
        specs=[[{"type": "xy"}, {"type": "domain"}]],
        horizontal_spacing=0.16,
    )
    if left_counts:
        names = [item[0] for item in left_counts][::-1]
        values = [item[1] for item in left_counts][::-1]
        figure.add_bar(
            x=values,
            y=names,
            orientation="h",
            marker={"color": values, "colorscale": [[0, "#d9e9e3"], [1, COLORS["strategy"]]], "showscale": False},
            hovertemplate="<b>%{y}</b><br>数量 %{x}<extra></extra>",
            row=1,
            col=1,
        )
    if right_counts:
        labels = [item[0] for item in right_counts]
        values = [item[1] for item in right_counts]
        palette = [COLORS["strategy"], COLORS["benchmark"], COLORS["positive"], COLORS["muted"], COLORS["ink"]]
        figure.add_pie(
            labels=labels,
            values=values,
            hole=0.52,
            marker={"colors": [palette[index % len(palette)] for index in range(len(labels))]},
            texttemplate="%{label}<br>%{value}",
            textposition="outside",
            hovertemplate="<b>%{label}</b><br>数量 %{value}<extra></extra>",
            row=1,
            col=2,
        )
        figure.update_traces(textposition="outside", textinfo="label+value", row=1, col=2)
    _style_figure(figure, title, height)
    figure.update_layout(showlegend=False, annotations=[])
    figure.update_xaxes(title=None)
    return figure


def paper_distribution_figure(frame: Any) -> go.Figure:
    data = frame
    if isinstance(frame, pd.DataFrame) and "year" not in frame.columns and "published_at" in frame.columns:
        data = frame.copy()
        data["year"] = data["published_at"].astype(str).str.slice(0, 4)
    return _distribution_figure("论文分布", "year", "source", data, 320, "年份", "来源")


def report_rating_figure(frame: Any) -> go.Figure:
    return _distribution_figure("研报分布", "rating", "org", frame, 320, "评级", "机构")


def strategy_stat_figure(frame: Any) -> go.Figure:
    return _distribution_figure("策略分布", "status", "interface_type", frame, 320, "状态", "接口类型")


def model_stat_figure(frame: Any) -> go.Figure:
    data = frame
    if isinstance(frame, pd.DataFrame) and "purpose" in frame.columns:
        data = frame.copy()
        data["purpose"] = data["purpose"].map(lambda value: ", ".join(value) if isinstance(value, list) else value)
    return _distribution_figure("模型分布", "level", "purpose", data, 320, "层级", "用途")


def score_figure(scores: dict[str, Any]) -> go.Figure:
    if not scores:
        return empty_figure("综合评分", "暂无评分数据", 300)
    labels = {
        "total": "综合",
        "trend": "趋势",
        "momentum": "动量",
        "volume": "量能",
        "valuation": "估值",
        "fundamental": "基本面",
        "sentiment": "舆情",
    }
    items = [(labels.get(key, key), float(value or 0)) for key, value in scores.items()]
    names = [item[0] for item in reversed(items)]
    values = [item[1] for item in reversed(items)]
    colors = [
        COLORS["strategy"] if value >= 75 else COLORS["benchmark"] if value >= 60 else COLORS["positive"]
        for value in values
    ]
    figure = _base_figure("综合评分", 300)
    figure.add_bar(
        x=values,
        y=names,
        orientation="h",
        marker_color=colors,
        text=[f"{value:.0f}" for value in values],
        textposition="inside",
        insidetextanchor="end",
        hovertemplate="%{y} %{x:.0f} 分<extra></extra>",
    )
    figure.update_xaxes(range=[0, 100], title="评分", dtick=20)
    figure.update_yaxes(showgrid=False)
    figure.update_layout(showlegend=False, bargap=0.38)
    return figure


def recommend_factor_figure(rows: Sequence[dict[str, Any]]) -> go.Figure:
    candidates = list(rows)[:8]
    if not candidates:
        return empty_figure("推荐候选因子对比", "请先生成推荐候选", 360)
    labels = [f"{item.get('symbol', '-')}\n{item.get('name', '-')}" for item in reversed(candidates)]
    figure = _base_figure("推荐候选因子对比", max(360, 220 + len(candidates) * 36))
    series = [
        ("综合评分", "score", COLORS["blue"]),
        ("动量", "momentum", COLORS["strategy"]),
        ("流动性", "liquidity", COLORS["benchmark"]),
        ("情绪", "sentiment", COLORS["positive"]),
        ("缠论", "chan", COLORS["violet"]),
    ]
    for name, key, color in series:
        values = [_safe_float(item.get(key)) for item in reversed(candidates)]
        if key == "chan" and not any(values):
            continue
        figure.add_bar(
            name=name,
            x=values,
            y=labels,
            orientation="h",
            marker={"color": color, "opacity": 0.82},
            hovertemplate=f"<b>%{{y}}</b><br>{name} %{{x:.2f}}<extra></extra>",
        )
    figure.update_xaxes(title="评分", range=[0, 105])
    figure.update_yaxes(title=None, showgrid=False, automargin=True)
    figure.update_layout(barmode="group", bargap=0.24, bargroupgap=0.08)
    return figure


def recommend_group_compare_figure(
    summary_rows: Sequence[dict[str, Any]],
    symbol_rows: Sequence[dict[str, Any]],
    score_matrix: dict[str, dict[str, float]],
) -> go.Figure:
    if not summary_rows:
        return empty_figure("多组候选参数对比", "请选择至少两个推荐方案", 420)
    plan_labels = [str(item.get("方案") or "-") for item in summary_rows]
    candidate_labels = [
        f"{item.get('代码', '-')}\n{item.get('名称', '-')}" for item in list(symbol_rows)[: min(len(symbol_rows), 12)]
    ]
    figure = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.36, 0.64],
        subplot_titles=("方案平均评分", "候选覆盖热力"),
    )
    figure.add_bar(
        x=plan_labels,
        y=[_safe_float(item.get("平均评分")) for item in summary_rows],
        marker={"color": [COLORS["blue"], COLORS["strategy"], COLORS["benchmark"], COLORS["positive"]] * 2},
        text=[f"{_safe_float(item.get('平均评分')):.1f}" for item in summary_rows],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>平均评分 %{y:.2f}<extra></extra>",
        row=1,
        col=1,
    )
    if candidate_labels:
        z_values = [
            [score_matrix.get(label.split("\n", 1)[0], {}).get(plan) for plan in plan_labels]
            for label in candidate_labels
        ]
        figure.add_heatmap(
            x=plan_labels,
            y=candidate_labels,
            z=z_values,
            zmin=0,
            zmax=100,
            colorscale=[[0, "#eef4f8"], [0.5, COLORS["benchmark"]], [1, COLORS["positive"]]],
            colorbar={"title": "评分"},
            hovertemplate="<b>%{y}</b><br>%{x}<br>评分 %{z:.2f}<extra></extra>",
            row=1,
            col=2,
        )
    figure.update_yaxes(range=[0, 105], title="平均评分", row=1, col=1)
    figure.update_xaxes(tickangle=-15, row=1, col=1)
    figure.update_yaxes(title=None, automargin=True, row=1, col=2)
    figure.update_layout(
        height=max(420, 280 + len(candidate_labels) * 24),
        showlegend=False,
        margin={"l": 64, "r": 36, "t": 72, "b": 70},
    )
    return figure


def kline_figure(items: Sequence[dict[str, Any]], symbol: str) -> go.Figure:
    if not items:
        return empty_figure(f"{symbol} 价格走势", "暂无 K 线数据", 520)
    dates = [item.get("date") for item in items]
    opens = [float(item.get("open") or 0) for item in items]
    highs = [float(item.get("high") or 0) for item in items]
    lows = [float(item.get("low") or 0) for item in items]
    closes = [float(item.get("close") or 0) for item in items]
    volumes = [float(item.get("volume") or 0) for item in items]
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.045, row_heights=[0.75, 0.25])
    figure.add_trace(
        go.Candlestick(
            x=dates,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            increasing={"line": {"color": COLORS["positive"], "width": 1}, "fillcolor": COLORS["positive"]},
            decreasing={"line": {"color": COLORS["negative"], "width": 1}, "fillcolor": COLORS["negative"]},
            name="K 线",
            hovertext=[f"成交量 {volume:,.0f}" for volume in volumes],
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    close_series = pd.Series(closes)
    for window, color in ((5, COLORS["benchmark"]), (10, COLORS["blue"]), (20, COLORS["violet"])):
        figure.add_scatter(
            x=dates,
            y=close_series.rolling(window, min_periods=1).mean().tolist(),
            mode="lines",
            name=f"MA{window}",
            line={"color": color, "width": 1.4},
            hovertemplate=f"MA{window} %{{y:.2f}}<extra></extra>",
            row=1,
            col=1,
        )
    figure.add_bar(
        x=dates,
        y=volumes,
        name="成交量",
        marker_color=[
            COLORS["positive"] if close >= open_ else COLORS["negative"]
            for open_, close in zip(opens, closes, strict=True)
        ],
        opacity=0.72,
        hovertemplate="成交量 %{y:,.0f}<extra></extra>",
        showlegend=False,
        row=2,
        col=1,
    )
    _style_figure(figure, f"{symbol} 价格走势", 520)
    figure.update_layout(xaxis_rangeslider_visible=False, hovermode="x", bargap=0.18)
    figure.update_yaxes(title="价格", tickformat=",.2f", row=1, col=1)
    figure.update_yaxes(title="成交量", tickformat="~s", row=2, col=1)
    figure.update_xaxes(showspikes=True, spikemode="across", spikesnap="cursor", spikedash="dot", row=2, col=1)
    return figure


def equity_figure(curve: dict[str, Any]) -> go.Figure:
    dates = curve.get("dates") or []
    equity = [float(value) for value in (curve.get("equity") or [])]
    benchmark = [float(value) for value in (curve.get("benchmark") or [])]
    if not dates or not equity:
        return empty_figure(
            "策略净值与回撤",
            str(curve.get("message") or "请选择已完成的回测任务"),
            460,
        )
    strategy_base = equity[0] or 1
    benchmark_base = benchmark[0] if benchmark else 1
    strategy_nav = [value / strategy_base for value in equity]
    benchmark_nav = [value / benchmark_base for value in benchmark]
    drawdown = [float(value) for value in (curve.get("drawdown") or [0] * len(dates))]
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.72, 0.28])
    figure.add_scatter(
        x=dates,
        y=strategy_nav,
        mode="lines",
        name="策略净值",
        line={"color": COLORS["strategy"], "width": 2.4},
        fill="none",
        hovertemplate="策略净值 %{y:.4f}<extra></extra>",
        row=1,
        col=1,
    )
    if benchmark_nav:
        figure.add_scatter(
            x=dates,
            y=benchmark_nav,
            mode="lines",
            name="基准净值",
            line={"color": COLORS["benchmark"], "width": 1.7, "dash": "dot"},
            hovertemplate="基准净值 %{y:.4f}<extra></extra>",
            row=1,
            col=1,
        )
    figure.add_scatter(
        x=dates,
        y=drawdown,
        mode="lines",
        name="回撤",
        line={"color": COLORS["positive"], "width": 1.4},
        fill="tozeroy",
        fillcolor="rgba(196,61,75,0.16)",
        hovertemplate="回撤 %{y:.2%}<extra></extra>",
        row=2,
        col=1,
    )
    _style_figure(figure, "策略净值与回撤", 460)
    figure.update_yaxes(title="累计净值", tickformat=".3f", row=1, col=1)
    figure.update_yaxes(title="回撤", tickformat=".1%", row=2, col=1)
    return figure


def backtest_monthly_figure(curve: dict[str, Any]) -> go.Figure:
    dates, returns = _curve_returns(curve)
    if len(returns) < 2:
        return empty_figure("月度收益热力", "至少需要两个交易日才能计算月度收益", 340)
    monthly: dict[str, float] = {}
    for timestamp, daily_return in zip(dates[1:], returns, strict=True):
        month = timestamp.strftime("%Y-%m")
        monthly[month] = (1 + monthly.get(month, 0.0)) * (1 + daily_return) - 1
    periods = sorted(monthly)
    years = sorted({period[:4] for period in periods})
    months = [f"{index:02d}" for index in range(1, 13)]
    values = [[monthly.get(f"{year}-{month}", None) for month in months] for year in years]
    text = [["-" if value is None else f"{value:.1%}" for value in row] for row in values]
    figure = _base_figure("月度收益热力（颜色越深波动越大）", 340)
    figure.add_heatmap(
        z=values,
        x=[f"{month}月" for month in range(1, 13)],
        y=years,
        text=text,
        texttemplate="%{text}",
        textfont={"size": 11},
        colorscale=[
            [0.0, "#138a78"],
            [0.5, "#f7faf9"],
            [1.0, "#d94c62"],
        ],
        zmid=0,
        colorbar={"title": "收益"},
        hovertemplate="%{y}-%{x}<br>月度收益 %{z:.2%}<extra></extra>",
    )
    figure.update_xaxes(title="月份")
    figure.update_yaxes(title="年份", autorange="reversed")
    return figure


def backtest_rolling_figure(curve: dict[str, Any], window: int = 20) -> go.Figure:
    dates, returns = _curve_returns(curve)
    if len(returns) < 3:
        return empty_figure("滚动风险指标", "至少需要三个交易日才能计算滚动风险", 420)
    minimum = min(max(window // 4, 3), len(returns))
    series = pd.Series(returns, index=dates[1:])
    rolling_mean = series.rolling(window, min_periods=minimum).mean() * 252
    rolling_volatility = series.rolling(window, min_periods=minimum).std(ddof=0) * (252**0.5)
    rolling_sharpe = rolling_mean.div(rolling_volatility.where(rolling_volatility != 0)).fillna(0.0)
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.09,
        subplot_titles=("滚动年化波动率", "滚动夏普比率"),
    )
    figure.add_scatter(
        x=rolling_volatility.index,
        y=rolling_volatility.tolist(),
        name="年化波动率",
        line={"color": COLORS["benchmark"], "width": 1.8},
        hovertemplate="波动率 %{y:.2%}<extra></extra>",
        row=1,
        col=1,
    )
    figure.add_scatter(
        x=rolling_sharpe.index,
        y=rolling_sharpe.tolist(),
        name="夏普比率",
        line={"color": COLORS["blue"], "width": 1.8},
        hovertemplate="夏普 %{y:.2f}<extra></extra>",
        row=2,
        col=1,
    )
    _style_figure(figure, f"滚动风险指标（{window} 日窗口）", 420)
    figure.update_yaxes(title="波动率", tickformat=".1%", row=1, col=1)
    figure.update_yaxes(title="夏普", row=2, col=1)
    return figure


def backtest_trade_figure(trades: Sequence[dict[str, Any]]) -> go.Figure:
    rows = list(trades)
    if not rows:
        return empty_figure("交易盈亏分布", "暂无已平仓交易", 420)
    pnl = [_safe_float(item.get("pnl")) for item in rows]
    labels = [str(item.get("close_time") or item.get("symbol") or index + 1) for index, item in enumerate(rows)]
    colors = [COLORS["positive"] if value >= 0 else COLORS["negative"] for value in pnl]
    figure = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.62, 0.38],
        subplot_titles=("逐笔净收益", "收益分布"),
        horizontal_spacing=0.13,
    )
    figure.add_bar(
        x=labels,
        y=pnl,
        marker_color=colors,
        name="交易净收益",
        hovertemplate="%{x}<br>净收益 %{y:,.2f}<extra></extra>",
        row=1,
        col=1,
    )
    figure.add_histogram(
        x=pnl,
        nbinsx=max(5, min(12, len(pnl))),
        marker_color=COLORS["blue"],
        opacity=0.8,
        name="收益分布",
        hovertemplate="区间 %{x}<br>交易数 %{y}<extra></extra>",
        row=1,
        col=2,
    )
    _style_figure(figure, "交易盈亏分布（红色盈利 / 绿色亏损）", 420)
    figure.add_hline(y=0, line={"color": "#84949b", "width": 1}, row=1, col=1)
    figure.update_xaxes(title="平仓日期", tickangle=-35, row=1, col=1)
    figure.update_yaxes(title="净收益", tickformat=",.0f", row=1, col=1)
    figure.update_xaxes(title="单笔净收益", tickformat=",.0f", row=1, col=2)
    figure.update_yaxes(title="交易数", row=1, col=2)
    figure.update_layout(showlegend=False)
    return figure


def backtest_exposure_figure(curve: dict[str, Any]) -> go.Figure:
    dates = list(curve.get("dates") or [])
    exposure = [_safe_float(value) for value in (curve.get("exposure") or [])]
    position_count = [_safe_float(value) for value in (curve.get("position_count") or [])]
    if not dates or not exposure:
        return empty_figure("持仓暴露与组合规模", "当前回测未返回持仓暴露序列", 420)
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.09,
        subplot_titles=("持仓暴露", "持仓数量"),
    )
    figure.add_scatter(
        x=dates,
        y=exposure,
        name="持仓暴露",
        line={"color": COLORS["violet"], "width": 1.8},
        fill="tozeroy",
        fillcolor="rgba(128,90,213,.10)",
        hovertemplate="持仓暴露 %{y:.2%}<extra></extra>",
        row=1,
        col=1,
    )
    if position_count:
        figure.add_scatter(
            x=dates,
            y=position_count,
            name="持仓数量",
            line={"color": COLORS["blue"], "width": 1.8},
            hovertemplate="持仓数量 %{y:.0f}<extra></extra>",
            row=2,
            col=1,
        )
    _style_figure(figure, "持仓暴露与组合规模", 420)
    figure.update_yaxes(title="暴露", tickformat=".0%", row=1, col=1)
    figure.update_yaxes(title="数量", dtick=1, row=2, col=1)
    return figure


def backtest_explanation(metrics: dict[str, Any], curve: dict[str, Any]) -> str:
    scope = str(metrics.get("result_scope") or "完整事件回测结果")
    source = str(metrics.get("data_source") or "未知")
    trade_count = int(_safe_float(metrics.get("trade_count")))
    curve_available = bool(metrics.get("curve_available", bool(curve.get("equity"))))
    notes = [
        f"**结果范围**：{scope}；**数据源**：{source}；**已平仓交易**：{trade_count} 笔。",
        "净值、回撤和滚动指标基于逐日资金曲线；交易统计只计算已平仓交易。",
    ]
    if not curve_available:
        notes.append("当前引擎只返回指标摘要，未提供逐日曲线，因此不绘制净值和滚动图。")
    if source.startswith("mock"):
        notes.append("当前使用 mock 行情，仅用于验证策略端口和回测链路，不代表真实绩效。")
    if trade_count < 5:
        notes.append("交易样本较少，胜率、盈亏比和分布图的统计稳定性有限。")
    if metrics.get("benchmark_label"):
        notes.append(f"**比较基准**：{metrics['benchmark_label']}。")
    model_report = metrics.get("model_diagnostics") or {}
    if isinstance(model_report, dict) and model_report:
        notes.append(
            f"**模型训练**：{model_report.get('title', '-')}；拟合 {model_report.get('fit_count', 0)} 次；"
            f"样本外预测 {model_report.get('prediction_count', 0)} 条；"
            f"已到期评价 {model_report.get('evaluated_prediction_count', 0)} 条；"
            f"训练耗时 {float(model_report.get('fit_duration_ms') or 0) / 1000:.2f} 秒。"
        )
        notes.append("模型只使用已到期标签；上一交易日收盘特征生成排名，下一交易日开盘执行。")
    return "\n\n".join(f"- {item}" for item in notes) + cost_markdown(metrics)


def _curve_returns(curve: dict[str, Any]) -> tuple[list[datetime], list[float]]:
    raw_dates = list(curve.get("dates") or [])
    equity = [_safe_float(value) for value in (curve.get("equity") or [])]
    if len(raw_dates) != len(equity) or len(equity) < 2:
        return [], []
    dates = [pd.Timestamp(value).to_pydatetime() for value in raw_dates]
    returns = [equity[index] / equity[index - 1] - 1 for index in range(1, len(equity)) if equity[index - 1]]
    if len(returns) != len(dates) - 1:
        return [], []
    return dates, returns


def backtest_attribution_figure(payload: dict[str, Any]) -> go.Figure:
    rows = payload.get("by_symbol") or []
    if not rows:
        return empty_figure("回测归因摘要", "暂无交易归因，请先运行回测", 360)
    names = [str(item.get("name") or "-") for item in rows]
    pnl_values = [float(item.get("pnl") or 0.0) for item in rows]
    colors = [COLORS["positive"] if value >= 0 else COLORS["negative"] for value in pnl_values]
    figure = _base_figure("回测归因摘要", 360)
    figure.add_bar(
        x=names,
        y=pnl_values,
        marker_color=colors,
        text=[f"{value:+.0f}" for value in pnl_values],
        textposition="outside",
        name="标的盈亏贡献",
        hovertemplate="%{x}<br>盈亏 %{y:,.2f}<extra></extra>",
    )
    _style_figure(figure, "回测归因摘要", 360)
    figure.update_yaxes(title="盈亏金额", tickformat=",.0f")
    figure.update_xaxes(title="标的")
    return figure


def backtest_attribution_frame(payload: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in payload.get("summary") or []:
        rows.append(
            {
                "section": "摘要",
                "item": item.get("item"),
                "value": item.get("value"),
                "note": item.get("note"),
            }
        )
    for item in payload.get("by_symbol") or []:
        rows.append(
            {
                "section": "标的贡献",
                "item": item.get("name"),
                "value": f"{float(item.get('pnl') or 0):+.2f}",
                "note": f"交易 {item.get('trade_count')} 笔 / 胜率 {float(item.get('win_rate') or 0) * 100:.1f}%",
            }
        )
    drawdown = payload.get("drawdown") or {}
    if drawdown:
        rows.append(
            {
                "section": "回撤",
                "item": "最大回撤段",
                "value": f"{drawdown.get('peak_date', '')} → {drawdown.get('trough_date', '')}",
                "note": f"{float(drawdown.get('max_drawdown') or 0) * 100:+.2f}%",
            }
        )
    for item in payload.get("risk_flags") or []:
        rows.append(
            {
                "section": "风险提示",
                "item": item.get("title"),
                "value": item.get("severity"),
                "note": item.get("message"),
            }
        )
    return to_frame(rows, BACKTEST_ATTRIBUTION_COLUMNS)


def nav_figure(history: dict[str, Any]) -> go.Figure:
    dates = history.get("dates") or []
    values = [float(value) for value in (history.get("net_values") or [])]
    if not dates or not values:
        return empty_figure("模拟账户净值", "创建或选择模拟账户后显示净值", 360)
    figure = _base_figure("模拟账户净值", 360)
    figure.add_scatter(
        x=dates,
        y=values,
        mode="lines+markers",
        name="净值",
        line={"color": COLORS["strategy"], "width": 2.4},
        marker={"size": 6, "color": "#ffffff", "line": {"color": COLORS["strategy"], "width": 2}},
        fill="tozeroy",
        fillcolor="rgba(23,107,85,0.09)",
        hovertemplate="净值 %{y:.4f}<extra></extra>",
    )
    figure.add_hline(y=1, line={"color": COLORS["benchmark"], "width": 1, "dash": "dot"}, annotation_text="初始净值")
    spread = max(max(values) - min(values), 0.01)
    figure.update_yaxes(
        title="单位净值",
        tickformat=".4f",
        range=[min(min(values), 1) - spread * 0.35, max(max(values), 1) + spread * 0.35],
    )
    return figure


def pnl_figure(history: dict[str, Any]) -> go.Figure:
    dates = history.get("dates") or []
    values = [float(value) for value in (history.get("net_values") or [])]
    if not dates or not values:
        return empty_figure("最近盈亏走势", "创建或选择模拟账户后显示盈亏曲线", 360)
    cumulative = [(value - 1) * 100 for value in values]
    daily = [float(value or 0) * 100 for value in (history.get("daily_returns") or [])]
    if len(daily) < len(dates):
        daily = [0.0] * (len(dates) - len(daily)) + daily
    figure = _base_figure("最近盈亏走势", 360)
    colors = [COLORS["positive"] if value >= 0 else COLORS["negative"] for value in daily[-len(dates) :]]
    figure.add_bar(
        x=dates,
        y=daily[-len(dates) :],
        name="单日盈亏",
        marker={"color": colors, "opacity": 0.46},
        hovertemplate="单日 %{y:+.2f}%<extra></extra>",
    )
    figure.add_scatter(
        x=dates,
        y=cumulative,
        mode="lines+markers",
        name="累计盈亏",
        line={"color": COLORS["blue"], "width": 2.4},
        marker={"size": 6, "color": "#ffffff", "line": {"color": COLORS["blue"], "width": 2}},
        hovertemplate="累计 %{y:+.2f}%<extra></extra>",
    )
    figure.add_hline(y=0, line={"color": COLORS["benchmark"], "width": 1, "dash": "dot"}, annotation_text="盈亏平衡")
    figure.update_yaxes(title="收益率", ticksuffix="%")
    return figure


def factor_ic_figure(rows: Sequence[dict[str, Any]]) -> go.Figure:
    if not rows:
        return empty_figure("因子RankIC走势", "历史截面样本不足，刷新后将继续积累", 420)
    figure = _base_figure("因子RankIC走势", 420)
    by_factor: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_factor.setdefault(str(row.get("factor_name") or row.get("factor_key")), []).append(dict(row))
    palette = [COLORS["blue"], COLORS["strategy"], COLORS["violet"], COLORS["benchmark"], COLORS["positive"]]
    for index, (factor_name, items) in enumerate(by_factor.items()):
        figure.add_scatter(
            x=[item.get("date") for item in items],
            y=[_safe_float(item.get("rank_ic")) for item in items],
            mode="lines+markers",
            name=factor_name,
            line={"color": palette[index % len(palette)], "width": 2.2},
            marker={"size": 6},
            hovertemplate=f"{factor_name}<br>RankIC %{{y:.3f}}<extra></extra>",
        )
    figure.add_hline(y=0, line={"color": "#87979d", "width": 1, "dash": "dot"})
    figure.update_yaxes(title="RankIC", tickformat=".2f")
    return figure


def factor_quantile_figure(rows: Sequence[dict[str, Any]]) -> go.Figure:
    if not rows:
        return empty_figure("因子分位收益", "当前样本不足以计算分位收益", 420)
    figure = _base_figure("因子分位收益", 420)
    by_factor: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_factor.setdefault(str(row.get("factor_name") or row.get("factor_key")), []).append(dict(row))
    palette = [COLORS["blue"], COLORS["strategy"], COLORS["violet"], COLORS["benchmark"], COLORS["positive"]]
    for index, (factor_name, items) in enumerate(by_factor.items()):
        ordered = sorted(items, key=lambda item: str(item.get("quantile")))
        figure.add_bar(
            x=[item.get("quantile") for item in ordered],
            y=[_safe_float(item.get("forward_return")) * 100 for item in ordered],
            name=factor_name,
            marker={"color": palette[index % len(palette)], "opacity": 0.78},
            hovertemplate=f"{factor_name}<br>%{{x}} 未来收益 %{{y:+.2f}}%<extra></extra>",
        )
    figure.add_hline(y=0, line={"color": "#87979d", "width": 1, "dash": "dot"})
    figure.update_yaxes(title="未来收益", ticksuffix="%")
    figure.update_layout(barmode="group")
    return figure


def factor_quantile_history_figure(rows: Sequence[dict[str, Any]]) -> go.Figure:
    if not rows:
        return empty_figure("分层收益时序", "当前样本不足以计算最高组减最低组的收益", 420)
    figure = _base_figure("分层收益时序：最高组 − 最低组", 420)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        factor_name = str(row.get("factor_name") or row.get("factor_key") or "-")
        date_label = str(row.get("date") or "")
        if date_label:
            grouped.setdefault((factor_name, date_label), []).append(dict(row))
    by_factor: dict[str, list[dict[str, Any]]] = {}
    for (factor_name, date_label), items in grouped.items():
        ordered = sorted(items, key=lambda item: _quantile_number(item.get("quantile")))
        if len(ordered) < 2:
            continue
        spread = _safe_float(ordered[-1].get("forward_return")) - _safe_float(ordered[0].get("forward_return"))
        by_factor.setdefault(factor_name, []).append({"date": date_label, "spread": spread})
    palette = [COLORS["blue"], COLORS["strategy"], COLORS["violet"], COLORS["benchmark"], COLORS["positive"]]
    for index, (factor_name, items) in enumerate(by_factor.items()):
        ordered = sorted(items, key=lambda item: str(item["date"]))
        figure.add_scatter(
            x=[item["date"] for item in ordered],
            y=[item["spread"] * 100 for item in ordered],
            mode="lines+markers",
            name=factor_name,
            line={"color": palette[index % len(palette)], "width": 2.1},
            marker={"size": 5},
            hovertemplate=f"{factor_name}<br>%{{x}} 最高组−最低组 %{{y:+.2f}}%<extra></extra>",
        )
    figure.add_hline(y=0, line={"color": "#87979d", "width": 1, "dash": "dot"})
    figure.update_yaxes(title="分层收益差", ticksuffix="%")
    return figure


def factor_style_exposure_figure(rows: Sequence[dict[str, Any]]) -> go.Figure:
    if not rows:
        return empty_figure("风格暴露诊断", "当前样本不足以计算风格代理暴露", 420)
    factors = list(dict.fromkeys(str(row.get("factor_name") or row.get("factor_key") or "-") for row in rows))
    styles = list(dict.fromkeys(str(row.get("style_factor") or "-") for row in rows))
    by_key = {
        (str(row.get("factor_name") or row.get("factor_key") or "-"), str(row.get("style_factor") or "-")): row.get(
            "exposure"
        )
        for row in rows
    }
    matrix = [[by_key.get((factor, style)) for style in styles] for factor in factors]
    figure = _base_figure("风格暴露诊断", 420)
    figure.add_heatmap(
        z=matrix,
        x=styles,
        y=factors,
        colorscale=[
            [0, "#0b9f8f"],
            [0.5, "#f5f9fa"],
            [1, "#d94c62"],
        ],
        zmin=-1,
        zmax=1,
        hovertemplate="%{y} × %{x}<br>暴露 %{z:.2f}<extra></extra>",
        colorbar={"title": "rho"},
    )
    figure.update_layout(margin={"l": 86, "r": 28, "t": 62, "b": 70})
    return figure


def factor_diagnostic_figure(
    ic_decay: Sequence[dict[str, Any]],
    metrics: Sequence[dict[str, Any]],
) -> go.Figure:
    if not ic_decay and not metrics:
        return empty_figure("因子诊断", "暂无足够样本生成诊断图", 460)
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("前瞻周期 IC 衰减", "信号稳定性与容量代理"),
        column_widths=[0.52, 0.48],
        horizontal_spacing=0.12,
    )
    palette = [COLORS["blue"], COLORS["strategy"], COLORS["violet"], COLORS["benchmark"], COLORS["positive"]]
    by_factor: dict[str, list[dict[str, Any]]] = {}
    for row in ic_decay:
        by_factor.setdefault(str(row.get("factor_name") or row.get("factor_key")), []).append(dict(row))
    for index, (factor_name, rows) in enumerate(by_factor.items()):
        ordered = sorted(rows, key=lambda item: int(item.get("horizon_days") or 0))
        figure.add_bar(
            x=[f"{item.get('horizon_days')}D" for item in ordered],
            y=[item.get("rank_ic") for item in ordered],
            name=factor_name,
            marker={"color": palette[index % len(palette)], "opacity": 0.78},
            hovertemplate=f"{factor_name}<br>%{{x}} 平均RankIC %{{y:.3f}}<extra></extra>",
            legendgroup=factor_name,
            row=1,
            col=1,
        )
    figure.add_hline(y=0, line={"color": "#87979d", "width": 1, "dash": "dot"}, row=1, col=1)
    for index, metric in enumerate(metrics):
        factor_name = str(metric.get("factor_name") or metric.get("factor_key") or "-")
        mean_ic = metric.get("rank_ic_mean")
        std_ic = metric.get("rank_ic_std")
        if mean_ic is None or std_ic is None:
            continue
        avg_turnover_rate = max(_safe_float(metric.get("avg_turnover_rate")), 0.0)
        capacity_hint = str(metric.get("capacity_hint") or "数据不足")
        figure.add_scatter(
            x=[_safe_float(mean_ic)],
            y=[_safe_float(std_ic)],
            mode="markers+text",
            text=[factor_name],
            textposition="top center",
            name=factor_name,
            marker={
                "size": max(14, min(34, 12 + avg_turnover_rate * 4)),
                "color": palette[index % len(palette)],
                "line": {"color": "#ffffff", "width": 1},
                "opacity": 0.86,
            },
            customdata=[[capacity_hint, avg_turnover_rate]],
            hovertemplate=(
                f"{factor_name}<br>平均RankIC %{{x:.3f}}<br>RankIC波动 %{{y:.3f}}"
                "<br>平均换手率 %{customdata[1]:.2f}%<br>容量代理 %{customdata[0]}<extra></extra>"
            ),
            legendgroup=factor_name,
            showlegend=False,
            row=1,
            col=2,
        )
    figure.add_vline(x=0, line={"color": "#87979d", "width": 1, "dash": "dot"}, row=1, col=2)
    _style_figure(figure, "因子诊断：IC 衰减与稳定性", 460)
    figure.update_layout(
        barmode="group",
        showlegend=True,
        margin={"l": 58, "r": 28, "t": 104, "b": 48},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.08, "xanchor": "right", "x": 1},
    )
    figure.update_xaxes(title="前瞻周期", row=1, col=1)
    figure.update_yaxes(title="平均 RankIC", tickformat=".2f", row=1, col=1)
    figure.update_xaxes(title="平均 RankIC", tickformat=".2f", row=1, col=2)
    figure.update_yaxes(title="RankIC 波动", tickformat=".2f", row=1, col=2)
    return figure


def _quantile_number(value: Any) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def factor_correlation_figure(correlation: dict[str, Any]) -> go.Figure:
    factors = correlation.get("factors") or []
    matrix = correlation.get("matrix") or []
    if not factors or not matrix:
        return empty_figure("因子相关性热力图", "暂无足够截面数据", 420)
    figure = _base_figure("因子相关性热力图", 420)
    figure.add_heatmap(
        z=matrix,
        x=factors,
        y=factors,
        colorscale=[
            [0, "#0b9f8f"],
            [0.5, "#f5f9fa"],
            [1, "#d94c62"],
        ],
        zmin=-1,
        zmax=1,
        hovertemplate="%{x} × %{y}<br>相关 %{z:.2f}<extra></extra>",
        colorbar={"title": "corr"},
    )
    figure.update_layout(margin={"l": 88, "r": 28, "t": 62, "b": 72})
    return figure


def relation_figure(nodes: Sequence[dict[str, Any]], edges: Sequence[dict[str, Any]], center_id: str) -> go.Figure:
    if not nodes:
        return empty_figure("个股关联网络", "暂无关联数据", 430)
    node_ids = [str(node.get("id")) for node in nodes]
    center = center_id if center_id in node_ids else node_ids[0]
    positions = graph_positions(list(nodes), list(edges), center)
    x_range, y_range = graph_bounds(positions)

    figure = go.Figure()
    edge_groups: dict[str, dict[str, Any]] = {}
    for edge in edges:
        source = str(edge.get("source"))
        target = str(edge.get("target"))
        if source not in positions or target not in positions:
            continue
        sx, sy = positions[source]
        tx, ty = positions[target]
        relation_type = str(edge.get("relation_type") or "relation")
        group_key = relation_type + (
            "_negative" if relation_type == "correlation" and edge.get("coefficient", 0) < 0 else ""
        )
        relation_label = str(edge.get("relation_label") or RELATION_TYPE_LABELS.get(relation_type, relation_type))
        weight = _safe_float(edge.get("weight"), 1.0)
        description = escape(str(edge.get("description") or "-"))
        group = edge_groups.setdefault(
            group_key,
            {
                "label": relation_label + ("（反向）" if group_key.endswith("_negative") else ""),
                "x": [],
                "y": [],
                "hovertext": [],
                "max_width": 1.0,
            },
        )
        group["x"].extend([sx, tx, None])
        group["y"].extend([sy, ty, None])
        hover = f"{source} → {target}<br>{relation_label}<br>权重 {weight:.2f}<br>{description}"
        group["hovertext"].extend([hover, hover, None])
        group["max_width"] = max(float(group["max_width"]), min(5.0, 1.0 + weight * 2.2))
    for relation_type, group in edge_groups.items():
        figure.add_scatter(
            x=group["x"],
            y=group["y"],
            mode="lines",
            line={
                "color": "#8b5cf6"
                if relation_type == "correlation_negative"
                else RELATION_TYPE_COLORS.get(relation_type, "#9aa6a1"),
                "width": group["max_width"],
            },
            name=group["label"],
            legendgroup=relation_type,
            showlegend=True,
            hovertext=group["hovertext"],
            hoverinfo="text",
        )

    type_colors = {
        "stock": COLORS["positive"],
        "sector": COLORS["strategy"],
        "index": "#0ea5b7",
        "relation": COLORS["blue"],
        "institution": COLORS["violet"],
        "event": COLORS["benchmark"],
        "task": "#1d7fbe",
        "factor": "#7e8aa0",
        "analysis": "#536dfe",
    }
    nodes_by_type: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        nodes_by_type.setdefault(str(node.get("type") or "relation"), []).append(dict(node))
    for node_type, typed_nodes in nodes_by_type.items():
        xs = []
        ys = []
        labels = []
        sizes = []
        customdata = []
        for node in typed_nodes:
            node_id = str(node.get("id"))
            x, y = positions.get(node_id, (0.0, 0.0))
            xs.append(x)
            ys.append(y)
            full_label = str(node.get("name") or node_id)
            label_limit = graph_config()["layout"]["label_limit"]
            labels.append(escape(full_label[:label_limit] + ("…" if len(full_label) > label_limit else "")))
            sizes.append(_safe_float(node.get("node_size"), 26))
            customdata.append(
                [
                    node_id,
                    node_type,
                    str(node.get("group_label") or "-"),
                    int(node.get("layer") or 0),
                    _safe_float(node.get("change_pct")),
                    int(node.get("degree") or 0),
                    escape(full_label),
                ]
            )
        figure.add_scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            text=labels,
            textposition="bottom center",
            marker={
                "size": sizes,
                "color": type_colors.get(node_type, COLORS["blue"]),
                "line": {"color": "#ffffff", "width": 2},
            },
            customdata=customdata,
            hovertemplate=(
                "<b>%{customdata[6]}</b><br>代码 %{customdata[0]}<br>类型 %{customdata[1]}"
                "<br>分组 %{customdata[2]}<br>层级 %{customdata[3]}<br>涨跌 %{customdata[4]:+.2f}%"
                "<br>连接度 %{customdata[5]}<extra></extra>"
            ),
            name={
                "stock": "股票",
                "sector": "板块",
                "index": "指数",
                "institution": "机构",
                "event": "事件",
                "task": "任务",
                "factor": "因子",
                "analysis": "分析",
                "relation": "关系节点",
            }.get(node_type, node_type),
            showlegend=True,
        )
    _style_figure(figure, f"个股关联网络（{len(nodes)} 节点 / {len(edges)} 关系）", graph_config()["layout"]["height"])
    figure.update_xaxes(visible=False, range=x_range)
    figure.update_yaxes(visible=False, range=y_range, scaleanchor=None)
    figure.update_layout(
        hovermode="closest",
        meta={"relation_edges": list(edges), "relation_nodes": list(nodes)},
        margin={"l": 24, "r": 24, "t": 66, "b": 24},
        legend={"orientation": "h", "y": -0.08, "x": 0, "xanchor": "left", "yanchor": "top", "font": {"size": 11}},
    )
    return figure


def metrics_frame(metrics: dict[str, Any]) -> pd.DataFrame:
    if not metrics:
        return to_frame(
            [{"类别": "状态", "指标": "暂无回测结果", "数值": "-", "解释": "请先运行一项已完成的回测。"}],
            ["类别", "指标", "数值", "解释"],
        )
    rows = []
    percent_metrics = {
        "net_return",
        "gross_return_before_costs",
        "total_return",
        "annual_return",
        "max_drawdown",
        "annual_volatility",
        "daily_var_95",
        "win_rate",
        "excess_return",
        "turnover_ratio",
        "average_exposure",
        "max_exposure",
        "tracking_error",
        "max_position_weight",
    }
    groups = {
        "total_return": "收益",
        "annual_return": "收益",
        "excess_return": "收益",
        "max_drawdown": "风险",
        "annual_volatility": "风险",
        "daily_var_95": "风险",
        "calmar": "风险",
        "sharpe": "风险",
        "sortino": "风险",
        "max_drawdown_duration_days": "风险",
        "max_drawdown_recovery_days": "风险",
        "trade_count": "交易",
        "win_count": "交易",
        "loss_count": "交易",
        "win_rate": "交易",
        "profit_loss_ratio": "交易",
        "profit_factor": "交易",
        "average_win": "交易",
        "average_loss": "交易",
        "expectancy": "交易",
        "best_trade": "交易",
        "worst_trade": "交易",
        "average_holding_days": "交易",
        "commission_paid": "执行",
        "tax_paid": "执行",
        "transfer_fee_paid": "执行",
        "other_fee_paid": "执行",
        "slippage_cost": "执行",
        "total_execution_cost": "执行",
        "net_pnl": "收益",
        "gross_pnl_before_costs": "收益",
        "net_return": "收益",
        "gross_return_before_costs": "收益",
        "turnover_ratio": "执行",
        "average_exposure": "执行",
        "max_exposure": "执行",
        "tracking_error": "执行",
    }
    for key, value in metrics.items():
        if isinstance(value, dict | list) or key == "data_fingerprint":
            continue
        if value is None:
            display = "-"
        elif key in percent_metrics:
            display = f"{float(value):.2%}"
        elif isinstance(value, float):
            display = f"{value:.4f}"
        else:
            display = value
        rows.append(
            {
                "类别": groups.get(key, "执行"),
                "指标": METRIC_LABELS.get(key, key),
                "数值": display,
                "解释": BACKTEST_METRIC_EXPLANATIONS.get(key, "回测任务的执行与结果元数据。"),
            }
        )
    return to_frame(rows, ["类别", "指标", "数值", "解释"])


def backtest_compare_figure(rows: Sequence[dict[str, Any]]) -> go.Figure:
    if not rows:
        return empty_figure("回测参数对比", "请选择或生成回测任务", 360)
    labels = [f"任务{item.get('task_id')}" for item in rows]
    total_return = [_safe_float(item.get("total_return")) * 100 for item in rows]
    drawdown = [abs(_safe_float(item.get("max_drawdown"))) * 100 for item in rows]
    sharpe = [_safe_float(item.get("sharpe")) for item in rows]
    figure = _base_figure("回测参数对比", 360)
    figure.add_bar(
        name="总收益(%)",
        x=labels,
        y=total_return,
        marker_color=COLORS["strategy"],
        hovertemplate="%{x}<br>总收益 %{y:.2f}%<extra></extra>",
    )
    figure.add_bar(
        name="最大回撤绝对值(%)",
        x=labels,
        y=drawdown,
        marker_color=COLORS["positive"],
        hovertemplate="%{x}<br>最大回撤 %{y:.2f}%<extra></extra>",
    )
    figure.add_bar(
        name="夏普",
        x=labels,
        y=sharpe,
        marker_color=COLORS["blue"],
        hovertemplate="%{x}<br>夏普 %{y:.2f}<extra></extra>",
    )
    figure.update_xaxes(title="回测任务")
    figure.update_yaxes(title="指标值")
    figure.update_layout(barmode="group", bargap=0.28, bargroupgap=0.08)
    return figure


def _money(value: Any) -> str:
    amount = _safe_float(value)
    if abs(amount) >= 100000000:
        return f"{amount / 100000000:.2f} 亿"
    if abs(amount) >= 10000:
        return f"{amount / 10000:.2f} 万"
    return f"{amount:,.2f}"


def _signed_money(value: Any) -> str:
    amount = _safe_float(value)
    sign = "+" if amount > 0 else ""
    return f"{sign}{_money(amount)}"


def _percent(value: Any) -> str:
    return f"{_safe_float(value):.2%}"


def _pct_points(value: Any) -> str:
    number = _safe_float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}%"


def _backtest_execution_config(task: dict[str, Any]) -> dict[str, Any]:
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    raw = params.get("_backtest") if isinstance(params, dict) else {}
    config = raw if isinstance(raw, dict) else {}
    return {
        "order_type": config.get("order_type") or "market",
        "price_adjustment": config.get("price_adjustment") or "qfq",
        "max_position_count": config.get("max_position_count", "-"),
        "max_position_weight": config.get("max_position_weight", "-"),
        "lot_size": config.get("lot_size", "-"),
        "slippage_rate": config.get("slippage_rate", 0.0),
    }


def _backtest_constraint_text(config: dict[str, Any]) -> str:
    return (
        f"最多 {config.get('max_position_count')} 只 / "
        f"单票 {_percent(config.get('max_position_weight')) if config.get('max_position_weight') != '-' else '-'} / "
        f"手数 {config.get('lot_size')}"
    )


def _live_validation_config(backtest_id: Any, account_id: Any) -> dict[str, int]:
    payload: dict[str, int] = {}
    parsed_backtest_id = _optional_id(backtest_id)
    parsed_account_id = _optional_id(account_id)
    if parsed_backtest_id:
        payload["backtest_id"] = parsed_backtest_id
    if parsed_account_id:
        payload["paper_account_id"] = parsed_account_id
    return payload


def _format_display_time(value: Any) -> str:
    """Convert an UTC ISO timestamp (e.g. ``...Z``) to Beijing time ``YYYY-mm-dd HH:MM``."""
    text = str(value or "").strip()
    if not text:
        return "-"
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    local = parsed.astimezone(timezone(timedelta(hours=8)))
    return local.strftime("%Y-%m-%d %H:%M")


def _seconds_since(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(int((_local_now() - parsed.astimezone(SHANGHAI_TZ)).total_seconds()), 0)


def _duration_text(seconds: int | None) -> str:
    if seconds is None:
        return "-"
    if seconds < 60:
        return f"{seconds} 秒"
    if seconds < 3600:
        return f"{seconds // 60} 分钟"
    return f"{seconds // 3600} 小时 {seconds % 3600 // 60} 分钟"


def relation_summary_markdown(summary: dict[str, Any], relation_types: Sequence[str] | None) -> str:
    relation_counts = summary.get("relation_counts") or {}
    group_counts = summary.get("group_counts") or {}
    layer_counts = summary.get("layer_counts") or {}
    selected = [RELATION_TYPE_LABELS.get(str(item), str(item)) for item in relation_types or []]
    relation_text = "、".join(f"{key} {value}" for key, value in relation_counts.items()) or "暂无关系边"
    group_text = "、".join(f"{key} {value}" for key, value in group_counts.items()) or "暂无节点分组"
    layer_text = "、".join(f"{key} {value}" for key, value in layer_counts.items()) or "暂无层级展开"
    selected_text = "、".join(selected) if selected else "全部关系"
    edge_count = int(summary.get("edge_count") or 0)
    key_nodes = summary.get("key_nodes") or []
    key_node_text = (
        "、".join(f"{item.get('name') or item.get('id')}({item.get('degree', 0)})" for item in key_nodes[:5])
        or "暂无高连接节点"
    )
    chain_paths = summary.get("chain_paths") or []
    chain_text = "；".join(str(path) for path in chain_paths[:3]) or "暂无可解释链路"
    notes = summary.get("construction_notes") or []
    note_text = "；".join(str(item) for item in notes) or "已按关系层级、连接度和权重完成服务层分析。"
    risk_hint = "关系边用于解释和联动观察，不代表因果关系或买卖信号。"
    if edge_count == 0:
        risk_hint = "当前筛选条件下没有可展示关系，可放宽关系类型或切换中心标的。"
    return (
        f"**图谱摘要**：中心 `{summary.get('center', '-')}`，"
        f"节点 {int(summary.get('node_count') or 0)} 个，关系 {edge_count} 条，"
        f"主导关系 `{summary.get('dominant_relation', '-')}`，筛选 `{selected_text}`。\n\n"
        f"**关系分布**：{relation_text}。\n\n"
        f"**层级展开**：最大展开 L{int(summary.get('max_layer') or 0)}，{layer_text}。\n\n"
        f"**节点分组**：{group_text}。\n\n"
        f"**关键节点**：{key_node_text}。\n\n"
        f"**链路分析**：{chain_text}。\n\n"
        f"**构建说明**：{note_text}。\n\n"
        f"{risk_hint}"
    )


def relation_analysis_frame(summary: dict[str, Any]) -> pd.DataFrame:
    relation_counts = summary.get("relation_counts") or {}
    relation_groups = summary.get("relation_groups") or []
    layer_counts = summary.get("layer_counts") or {}
    layer_paths = summary.get("layer_paths") or []
    key_nodes = summary.get("key_nodes") or []
    chain_paths = summary.get("chain_paths") or []
    notes = summary.get("construction_notes") or []
    rows: list[dict[str, Any]] = [
        {
            "item": "关系密度",
            "conclusion": f"{int(summary.get('node_count') or 0)} 个节点 / {int(summary.get('edge_count') or 0)} 条关系",
            "evidence": "节点数和边数用于判断图谱是否足以支撑关联观察",
            "monitor": "节点过少时优先提高深度或打开“分析构建”关系类型",
        },
        {
            "item": "主导关系",
            "conclusion": str(summary.get("dominant_relation") or "-"),
            "evidence": "、".join(f"{name}:{count}" for name, count in relation_counts.items()) or "-",
            "monitor": "主导关系变化代表解释口径切换，不直接代表买卖方向",
        },
        {
            "item": "关系分组",
            "conclusion": "、".join(
                f"{item.get('label')} {int(item.get('count') or 0)} 个" for item in relation_groups[:6]
            )
            or "-",
            "evidence": "；".join(
                f"{item.get('label')}：{item.get('key_nodes') or '-'}" for item in relation_groups[:4]
            )
            or "按节点类型和边关系归并",
            "monitor": "优先复核关联行业、公司、任务、新闻和产业链是否都有可解释证据",
        },
        {
            "item": "层级展开",
            "conclusion": f"最大 L{int(summary.get('max_layer') or 0)}；"
            + ("、".join(f"{key}:{value}" for key, value in layer_counts.items()) or "-"),
            "evidence": str((layer_paths[0] or {}).get("path") or "-") if layer_paths else "-",
            "monitor": "重点看 L2 之后是否存在可解释路径，若只有 L1 说明当前关系类型或数据源过窄",
        },
        {
            "item": "关键节点",
            "conclusion": "、".join(f"{item.get('name') or item.get('id')}" for item in key_nodes[:5]) or "-",
            "evidence": "按连接度和层级排序",
            "monitor": "优先观察高连接节点的涨跌、新闻和板块变化",
        },
        {
            "item": "主题链路",
            "conclusion": chain_paths[0] if chain_paths else "-",
            "evidence": "从中心标的出发的高权重关系链",
            "monitor": "链路中的板块、事件、机构节点同步增强时，关系解释更稳定",
        },
        {
            "item": "构建方式",
            "conclusion": "服务层分析构建",
            "evidence": "；".join(str(item) for item in notes) or "数据源关系边充足，服务层做层级与关键节点分析",
            "monitor": "若出现补图说明，应结合节点表和边表核验来源",
        },
    ]
    return to_frame(rows, RELATION_ANALYSIS_COLUMNS)


def format_cli_logs(log_data: dict[str, Any]) -> str:
    rows = []
    for item in log_data.get("logs") or []:
        rows.append(
            "[{time}] {level:<7} #{line_no:03d} {content}".format(
                time=item.get("time", "-"),
                level=item.get("level", "INFO"),
                line_no=int(item.get("line_no") or 0),
                content=item.get("content", ""),
            )
        )
    if not rows:
        return "暂无 CLI 日志"
    footer = f"next_offset={log_data.get('next_offset', 0)} ended={bool(log_data.get('ended'))}"
    return "\n".join(rows + [footer])
