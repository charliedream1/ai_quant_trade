"""Escaped homepage headlines without loading trading and chart adapters."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape
from typing import Any


def _format_display_time(value):
    return str(value or "Unknown source time")


def _dashboard_news_html(items: Sequence[dict[str, Any]]) -> str:
    cards = []
    for item in list(items)[:5]:
        title = escape(str(item.get("title") or "-"))
        url = str(item.get("url") or "").strip()
        source = escape(str(item.get("source") or "-"))
        published = escape(_format_display_time(item.get("published_at")))
        summary = escape(str(item.get("summary") or "")[:160])
        keywords = item.get("keywords") or []
        keyword_text = (
            " · ".join(str(keyword) for keyword in keywords[:4]) if isinstance(keywords, list) else str(keywords)
        )
        title_html = f"<a href='{escape(url)}'>{title}</a>" if url else title
        cards.append(
            "<article class='dashboard-news-card'><div><small>"
            + source
            + " · "
            + published
            + "</small><strong>"
            + title_html
            + "</strong></div><p>"
            + summary
            + "</p><span>"
            + escape(keyword_text or "要点新闻")
            + "</span></article>"
        )
    if not cards:
        return "<section class='dashboard-news-panel'><div class='ai-empty-state'>暂无新闻快照。</div></section>"
    return (
        "<section class='dashboard-news-panel'><div class='dashboard-panel-head'>"
        "<span>要点新闻</span><strong>先看会影响情绪的事件</strong><em>点击标题打开来源</em></div>"
        "<div class='dashboard-news-grid'>" + "".join(cards) + "</div></section>"
    )
