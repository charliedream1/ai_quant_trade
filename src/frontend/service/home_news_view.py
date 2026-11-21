"""Escaped homepage headlines without loading trading and chart adapters."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from html import escape
from typing import Any
from urllib.parse import urlsplit

from src.engine.market.news_topics import deduplicate, source_time

from .home_config import limit


def _group(item):
    region = item.get("region")
    regions = {"domestic": "国内", "overseas": "海外", "cross_border": "跨境"}
    topic = "时政政策" if "policy" in (item.get("topics") or []) else "财经经济"
    return regions.get(region, "待确认地区"), topic


def _selection(items, count, source_cap):
    queues: dict[tuple[str, str], deque] = defaultdict(deque)
    for item in deduplicate(items):
        queues[_group(item)].append(item)
    sources: Counter[str] = Counter()
    selected: dict[tuple[str, str], list] = defaultdict(list)
    spare = []
    remaining = count
    while remaining and any(queues.values()):
        for group, queue in queues.items():
            if not queue or not remaining:
                continue
            row = queue.popleft()
            source = str(row.get("source") or "")
            if sources[source] >= source_cap:
                spare.append((group, row))
                continue
            sources[source] += 1
            selected[group].append(row)
            remaining -= 1
    for group, row in spare[:remaining]:
        selected[group].append(row)
    return selected


def _safe_url(value):
    try:
        url = str(value or "").strip()
        parts = urlsplit(url)
        if parts.scheme in {"http", "https"} and parts.hostname and not parts.username and not parts.password:
            return url
    except ValueError:
        pass
    return ""


def _headline(item):
    title = escape(str(item.get("title") or "—"))
    url = _safe_url(item.get("url"))
    source = escape(str(item.get("source") or "—"))
    timestamp = item.get("published_at")
    published = (
        f"<time class='no-i18n'>{escape(str(timestamp))}</time>"
        if source_time(timestamp)
        else "<span>来源时间未知</span>"
    )
    title_html = (
        f"<a class='no-i18n' href='{escape(url)}' target='_blank' rel='noopener noreferrer'>{title}</a>"
        if url
        else f"<span class='no-i18n'>{title}</span>"
    )
    summary = escape(str(item.get("summary") or "")[: limit("news_summary_chars")])
    details = f"<details><summary>展开摘要</summary><p class='no-i18n'>{summary}</p></details>" if summary else ""
    return f"<li>{title_html}<small><span class='no-i18n'>{source}</span> · {published}</small>{details}</li>"


def _dashboard_news_html(feed: dict[str, Any]) -> str:
    groups = _selection(feed.get("items") or [], limit("news"), limit("news_per_source"))
    if not groups:
        message = "港股新闻源尚未配置" if feed.get("availability") else "本期暂无要点新闻"
        return f"<section class='dashboard-news-panel'><div class='ai-empty-state'>{message}</div></section>"
    panels = [
        f"<section class='home-news-group'><h3>{region} · {topic}</h3>"
        f"<ul>{''.join(_headline(row) for row in rows)}</ul></section>"
        for (region, topic), rows in groups.items()
    ]
    return (
        "<section class='dashboard-news-panel'><div class='dashboard-panel-head'>"
        "<strong>要点新闻</strong><a href='/app/?module=market&amp;view=news'>查看新闻中心</a></div>"
        "<div class='dashboard-news-grid'>" + "".join(panels) + "</div></section>"
    )
