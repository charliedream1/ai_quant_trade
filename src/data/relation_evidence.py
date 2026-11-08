"""Deterministic entity evidence and date-aligned return correlations."""

from __future__ import annotations

import math
import re
from functools import lru_cache
from statistics import StatisticsError, correlation
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def graph_config() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/data/relation_graph.yaml").read_text(encoding="utf-8"))


def news_evidence(
    item: dict[str, Any], symbol: str, name: str, aliases: list[str] | None = None
) -> dict[str, Any] | None:
    cfg = graph_config()
    terms = [symbol, name, *(aliases or [])]
    for field in ("title", "summary"):
        text = str(item.get(field) or "")
        for term in dict.fromkeys(terms):
            if not term or len(term) < cfg["name_min_chars"]:
                continue
            pattern = re.escape(term)
            if term.isascii():
                pattern = r"(?<![A-Za-z0-9])" + pattern + r"(?![A-Za-z0-9])"
            match = re.search(pattern, text)
            if match:
                start = max(match.start() - cfg["evidence_excerpt_chars"] // 2, 0)
                return _record(
                    item, symbol, term, field, text[start : start + cfg["evidence_excerpt_chars"]], "text_entity_match"
                )
    # Only provider-origin tags count; query-injected symbols/keywords do not.
    if symbol in (item.get("source_symbols") or []):
        return _record(
            item,
            symbol,
            symbol,
            "source_security_tags",
            str(item.get("summary") or item.get("title") or "")[: cfg["evidence_excerpt_chars"]],
            "provider_security_tag",
        )
    return None


def _record(item: dict[str, Any], symbol: str, term: str, field: str, excerpt: str, method: str) -> dict[str, Any]:
    return {
        "news_id": item.get("id"),
        "title": item.get("title") or "",
        "source": item.get("source") or "",
        "url": item.get("url") or "",
        "published_at": item.get("published_at") or "",
        "symbol": symbol,
        "matched_entity": term,
        "matched_field": field,
        "excerpt": excerpt,
        "method": method,
        "version": graph_config()["version"],
        "scope": "标题/摘要或来源证券标记，未分析全文",
        "relation_class": "direct_mention",
        "weight_kind": "规则关系权重，非概率",
    }


def dated_returns(rows: list[dict[str, Any]]) -> dict[str, float]:
    prices = {}
    for row in rows:
        day = str(row.get("date") or row.get("trade_date") or "")[:10]
        price = float(row.get("close") or 0)
        if day and price > 0 and math.isfinite(price):
            prices[day] = price
    days = sorted(prices)
    return {f"{left}/{right}": prices[right] / prices[left] - 1 for left, right in zip(days, days[1:], strict=False)}


def return_correlation(left: dict[str, float], right: dict[str, float]) -> tuple[float | None, dict[str, Any]]:
    # Matching interval endpoints prevents pairing a two-day suspension return with one day.
    intervals = sorted(left.keys() & right.keys())
    evidence = {
        "sample_size": len(intervals),
        "start": intervals[0].split("/")[0] if intervals else "",
        "end": intervals[-1].split("/")[-1] if intervals else "",
        "method": "对齐相同起止交易日的简单收益率Pearson相关",
    }
    try:
        coefficient = (
            correlation([left[day] for day in intervals], [right[day] for day in intervals])
            if len(intervals) >= graph_config()["minimum_correlation_samples"]
            else None
        )
    except StatisticsError:
        coefficient = None
    return coefficient, evidence
