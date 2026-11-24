"""Progressive index and sector views with lightweight worker dependencies."""

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextvars import copy_context
from typing import Any

import plotly.graph_objects as go

from src.core.page_work import policy
from src.core.panel_updates import panel_ready
from src.core.work_progress import progress
from src.engine.market.quote_service import QuoteService

from .figure_styles import COLORS, _base_figure, empty_figure
from .home_tables import home_styled_frame
from .shared_observations import shared_observation
from .view_primitives import INDEX_COLUMNS, to_frame

SECTOR_COLUMNS = [
    "code",
    "name",
    "change_pct",
    "leader",
    "amount",
    "up_count",
    "down_count",
    "board",
    "data_source",
    "updated_at",
]


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


class MarketQuotesMixin:
    def market_overview(self, board: str, limit: Any, selection="balanced") -> tuple[Any, Any, go.Figure]:
        quotes = QuoteService()
        limit_value = max(1, min(int(limit or 20), 100))
        max_age = policy()["market_refresh_cache_seconds"]
        progress("Fetching market data")
        with ThreadPoolExecutor(max_workers=2) as pool:
            index_future = pool.submit(
                copy_context().run,
                shared_observation,
                "market_indices",
                lambda: quotes.indices(refresh=True),
                max_age_seconds=max_age,
            )
            sector_future = pool.submit(
                copy_context().run,
                shared_observation,
                ["market_rankings", board, limit_value, selection],
                lambda: quotes.sector_rankings(
                    board=board or "industry", limit=limit_value, selection=selection, refresh=True
                ),
                max_age_seconds=max_age,
            )
            observations = {}
            tables = {}
            failures = []
            for future in as_completed((index_future, sector_future)):
                index = int(future is sector_future)
                try:
                    observations[index] = future.result()
                except Exception as exc:
                    failures.append(exc)
                    continue
                columns = ["ranking", *SECTOR_COLUMNS] if index else INDEX_COLUMNS
                tables[index] = home_styled_frame(to_frame(observations[index], columns))
                panel_ready(index, tables[index])
        if failures:
            raise failures[0]
        progress("Building charts")
        chart = market_bar_figure(observations[1])
        panel_ready(2, chart)
        return tables[0], tables[1], chart
