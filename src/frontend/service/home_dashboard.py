"""Compose homepage presentations without changing existing callback contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextvars import copy_context
from html import escape
from typing import Any

from src.core.config import get_settings
from src.core.panel_updates import panel_ready
from src.core.repository import Repository
from src.core.work_progress import progress
from src.engine.market import NewsAggregator, QuoteService
from src.engine.market.news_topics import time_range

from . import home_charts, home_views
from .home_config import label, limit
from .home_data import HomeAccount, account_snapshot
from .home_news_view import _dashboard_news_html
from .home_tables import home_styled_frame
from .shared_observations import shared_observation
from .view_primitives import HOLDING_COLUMNS, INDEX_COLUMNS, WATCHLIST_COLUMNS, _daily_cached, to_frame


def account_status(snapshot: HomeAccount) -> str:
    account_name = snapshot.account.get("name") or "未创建"
    basis = "模拟账户" if snapshot.mode == "paper" else "实盘账户"
    warning = "；".join(snapshot.warnings)
    return (
        f"**{basis}** · {escape(str(account_name))} · {get_settings().data_mode} · 最后刷新 {snapshot.valued_at}\n\n{snapshot.basis}"
        + (f" · {warning}" if warning else "")
    )


def home_account(mode: str, force_refresh: bool = False) -> tuple:
    def publish_local(snapshot):
        panel_ready(5, home_charts.account_trend(snapshot))

    snapshot = account_snapshot(mode, force_refresh, publish_local)
    builders = (
        lambda: account_status(snapshot),
        lambda: home_views.account_kpis(snapshot),
        lambda: home_views.risk_summary(snapshot),
        lambda: home_views.risk_alerts(snapshot),
        lambda: home_charts.risk_radar(snapshot),
        lambda: home_charts.account_trend(snapshot),
        lambda: home_charts.allocation(snapshot),
        lambda: home_charts.contribution(snapshot),
        lambda: home_styled_frame(to_frame(snapshot.holdings, HOLDING_COLUMNS)),
    )
    values = []
    for index, build in enumerate(builders):
        value = build()
        values.append(value)
        panel_ready(index, value)
    return tuple(values)


def _news_items(force_refresh):
    def load():
        progress("Reading headlines")
        start, end = time_range("week")
        return NewsAggregator().list_news(
            None,
            None,
            None,
            1,
            limit("news_candidates"),
            refresh=force_refresh,
            start_time=start,
            end_time=end,
            balanced_groups=True,
        )

    return shared_observation("home_news_scope_v2", load, force_refresh)


def home_themes(force_refresh=False, keyword_mode="lexical"):
    def load():
        items = _news_items(force_refresh).get("items", [])
        progress("Extracting keywords")
        return home_views.theme_summary(items, keyword_mode)

    return shared_observation(["home_news_themes_v3", keyword_mode], load, force_refresh)


def _market_payload(force_refresh: bool) -> dict[str, Any]:
    # Provider gates continue to bound source traffic; independent reads need not serialize here.
    from src.core.page_work import policy

    progress("Fetching market data")
    with ThreadPoolExecutor(max_workers=policy()["home_source_workers"], thread_name_prefix="home-sources") as pool:
        methods = {
            "indices": lambda: shared_observation(
                "market_indices",
                lambda: QuoteService().indices(refresh=force_refresh),
                max_age_seconds=policy()["market_refresh_cache_seconds"],
            ),
            "sectors": lambda: QuoteService().sector_snapshot(limit("sentiment_sectors"), refresh=force_refresh),
            "watchlist": lambda: QuoteService().watchlist_quotes(None),
        }
        futures = {key: pool.submit(copy_context().run, method) for key, method in methods.items()}
        result: dict[str, Any] = {"errors": [], "presentations": {}}

        def present(index, value):
            result["presentations"][index] = value
            panel_ready(index, value)

        for future in as_completed(futures.values()):
            key = next(name for name, pending in futures.items() if pending is future)
            try:
                if key == "sectors":
                    rankings, result["sentiment_sectors"] = future.result()
                    result[key] = home_views.balanced_sector_rows(rankings, limit("sectors"))
                else:
                    result[key] = future.result()
            except Exception:
                result[key] = []
                result["errors"].append(
                    {
                        "indices": "指数加载失败",
                        "sectors": label("missing_market"),
                        "watchlist": "自选行情加载失败",
                    }[key]
                )
            if key == "indices":
                present(3, home_styled_frame(to_frame(result[key], INDEX_COLUMNS)))
            elif key == "sectors":
                present(2, home_charts.sector_heatmap(result[key]))
            elif key == "watchlist":
                present(4, home_styled_frame(to_frame(result[key], WATCHLIST_COLUMNS)))
            if "indices" in result and "sectors" in result and 1 not in result["presentations"]:
                present(0, home_views.market_summary(result["indices"], result["sectors"]))
                present(1, home_charts.sentiment_radar(result["indices"], result.get("sentiment_sectors", [])))
        return result


def home_market_snapshot(mode: str, force_refresh: bool = False) -> tuple:
    payload, _, _ = _daily_cached(
        ("home_market_snapshot", mode), lambda: _market_payload(force_refresh), force_refresh=force_refresh
    )
    summary = home_views.market_summary(payload["indices"], payload["sectors"])
    if payload["errors"]:
        summary += f"<p class='home-muted'>{escape('；'.join(payload['errors']))}</p>"
    panel_ready(0, summary)
    values = payload["presentations"]
    return summary, values[1], values[2], values[3], values[4]


def home_market(mode: str, force_refresh: bool = False) -> tuple:
    summary, sentiment, sectors, indices, watchlist = home_market_snapshot(mode, force_refresh)
    return summary, sentiment, sectors, home_themes(force_refresh), indices, watchlist


def operation_counts(repo: Repository) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table, name, column in (
        ("backtest_tasks", "回测", "status"),
        ("live_runs", "运行", "status"),
        ("scheduled_jobs", "定时任务", "enabled"),
    ):
        counts = repo.db.query(f"SELECT {column} AS status, COUNT(*) AS count FROM {table} GROUP BY {column}")
        rows.extend(
            {
                "module": name,
                "status": ("启用" if row["status"] else "停用") if column == "enabled" else row["status"],
                "count": row["count"],
            }
            for row in counts
        )
    return rows or [{"module": "运行状态", "status": "暂无任务", "count": 0}]


def home_operations(actions: list[dict[str, Any]]) -> tuple[str, str, str]:
    return (
        home_views.action_summary(actions, alerts=True),
        home_views.action_summary(actions),
        home_views.operation_summary(operation_counts(Repository())),
    )


def home_news(mode: str, force_refresh: bool = False) -> str:
    def load() -> str:
        return _dashboard_news_html(_news_items(force_refresh))

    payload, _, _ = _daily_cached(("home_news", mode), load, force_refresh=force_refresh)
    return payload
