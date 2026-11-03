"""Compose homepage presentations without changing existing callback contracts."""

from __future__ import annotations

from html import escape
from typing import Any

from src.core.config import get_settings
from src.core.repository import Repository
from src.engine.market import NewsAggregator, QuoteService

from . import home_charts, home_views
from .dashboard_views import _dashboard_news_html
from .foundation import HOLDING_COLUMNS, INDEX_COLUMNS, WATCHLIST_COLUMNS, _daily_cached, to_frame
from .home_config import label, limit
from .home_data import HomeAccount, account_snapshot
from .home_tables import home_styled_frame


def account_status(snapshot: HomeAccount) -> str:
    account_name = snapshot.account.get("name") or "未创建"
    basis = "模拟账户" if snapshot.mode == "paper" else "实盘账户"
    warning = "；".join(snapshot.warnings)
    return (
        f"**{basis}** · {escape(str(account_name))} · {get_settings().data_mode} · 最后刷新 {snapshot.valued_at}\n\n{snapshot.basis}"
        + (f" · {warning}" if warning else "")
    )


def home_account(mode: str, force_refresh: bool = False) -> tuple:
    snapshot = account_snapshot(mode, force_refresh)
    return (
        account_status(snapshot),
        home_views.account_kpis(snapshot),
        home_views.risk_summary(snapshot),
        home_views.risk_alerts(snapshot),
        home_charts.risk_radar(snapshot),
        home_charts.account_trend(snapshot),
        home_charts.allocation(snapshot),
        home_charts.contribution(snapshot),
        home_styled_frame(to_frame(snapshot.holdings, HOLDING_COLUMNS)),
    )


def _market_payload(force_refresh: bool) -> dict[str, Any]:
    quotes = QuoteService()
    errors = []
    try:
        indices = quotes.indices(refresh=force_refresh)
    except Exception:
        indices = []
        errors.append("指数加载失败")
    try:
        sectors = quotes.sectors(limit=limit("sectors"))
    except Exception:
        sectors = []
        errors.append(label("missing_market"))
    try:
        watchlist = quotes.watchlist_quotes(None)
    except Exception:
        watchlist = []
        errors.append("自选行情加载失败")
    try:
        news_result = NewsAggregator().list_news(None, None, None, 1, limit("news"), refresh=force_refresh)
        news = (news_result.get("items") or [])[: limit("news")]
    except Exception:
        news = []
        errors.append("新闻加载失败")
    return {"indices": indices, "sectors": sectors, "watchlist": watchlist, "news": news, "errors": errors}


def home_market(mode: str, force_refresh: bool = False) -> tuple:
    payload, _, _ = _daily_cached(
        ("home_market", mode), lambda: _market_payload(force_refresh), force_refresh=force_refresh
    )
    summary = home_views.market_summary(payload["indices"], payload["sectors"])
    if payload["errors"]:
        summary += f"<p class='home-muted'>{escape('；'.join(payload['errors']))}</p>"
    return (
        summary,
        home_charts.sentiment_radar(payload["indices"], payload["sectors"]),
        home_charts.sector_heatmap(payload["sectors"]),
        home_views.theme_summary(payload["news"]),
        home_styled_frame(to_frame(payload["indices"], INDEX_COLUMNS)),
        home_styled_frame(to_frame(payload["watchlist"], WATCHLIST_COLUMNS)),
    )


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
        result = NewsAggregator().list_news(None, None, None, 1, limit("news"), refresh=force_refresh)
        items = (result.get("items") or [])[: limit("news")]
        return _dashboard_news_html(items)

    payload, _, _ = _daily_cached(("home_news", mode), load, force_refresh=force_refresh)
    return payload
