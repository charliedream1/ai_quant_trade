"""News listing and keyword analysis."""

import hashlib
import json
from typing import Any

from src.core.repository import Repository, make_where
from src.data import MARKET_US, DataSourceManager

from .news_policy import initialize
from .news_topics import policy, ranked_keywords, source_time, time_range


class NewsAggregator:
    def __init__(self, repo: Repository | None = None, data: DataSourceManager | None = None) -> None:
        self.repo = repo or Repository()
        self.data = data or DataSourceManager()

    def _mock_source_label(self) -> str:
        return "Mock Wire" if self.data.market == MARKET_US else "本地模拟源"

    def seed_if_empty(self, force_refresh: bool = False) -> None:
        if self.data.market == "HK":
            return
        has_items = bool(
            self.repo.db.scalar(
                "SELECT COUNT(*) AS cnt FROM news_items WHERE source = ?"
                if self.data.is_mock
                else "SELECT COUNT(*) AS cnt FROM news_items",
                (self._mock_source_label(),) if self.data.is_mock else (),
            )
        )
        if has_items and not force_refresh:
            return
        for item in self.data.list_news():
            dedup_hash = hashlib.sha1((item["title"] + item["url"]).encode("utf-8"), usedforsecurity=False).hexdigest()
            # The unique key arbitrates concurrent page loads without replacing existing rows.
            self.repo.db.execute(
                "INSERT INTO news_items (source, category, title, summary, url, published_at, fetched_at, "
                "keywords, dedup_hash, sentiment) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(dedup_hash) DO NOTHING",
                (
                    item["source"],
                    item["category"],
                    item["title"],
                    item["summary"],
                    item["url"],
                    item["published_at"],
                    item["fetched_at"],
                    json.dumps(item["keywords"], ensure_ascii=False),
                    dedup_hash,
                    0.3 if item["sentiment"] == "positive" else 0.0,
                ),
            )

    def list_news(
        self,
        category: str | None,
        keyword: str | None,
        source: str | None,
        page: int,
        page_size: int,
        refresh: bool = False,
        region: str = "all",
        topic: str = "all",
        market_relevant: bool = True,
        start_time: str | None = None,
        end_time: str | None = None,
        balanced_groups: bool = False,
    ) -> dict[str, Any]:
        if self.data.market == "HK":
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "availability": "Hong Kong news provider not configured",
            }
        self.seed_if_empty(force_refresh=refresh)
        initialize(self.repo.db)
        parts: list[tuple[str, Any]] = []
        start, end = source_time(start_time), source_time(end_time)
        if (start_time and start is None) or (end_time and end is None):
            raise ValueError("News date boundaries need an explicit time zone")
        if start and end and start > end:
            raise ValueError("News start time must precede its end time")
        if start:
            parts.append(("julianday(published_at) >= julianday(?)", start.isoformat()))
        if end:
            parts.append(("julianday(published_at) <= julianday(?)", end.isoformat()))
        if market_relevant:
            parts.append(("id IN (SELECT news_id FROM news_classification WHERE market_relevant=?)", 1))
        if region != "all":
            if region not in {"domestic", "overseas", "cross_border", "unknown"}:
                raise ValueError("Unknown news geography")
            parts.append(("id IN (SELECT news_id FROM news_classification WHERE region=?)", region))
        if topic != "all":
            if topic not in {"finance", "policy"}:
                raise ValueError("Unknown news subject")
            parts.append(("id IN (SELECT news_id FROM news_classification WHERE topics LIKE ?)", '%"' + topic + '"%'))
        if category:
            parts.append(("category = ?", category))
        if keyword:
            pattern = f"%{keyword}%"
            parts.append(("(title LIKE ? OR summary LIKE ?)", (pattern, pattern)))
        if source:
            parts.append(("source = ?", source))
        elif self.data.is_mock:
            parts.append(("source = ?", self._mock_source_label()))
        if not self.data.is_mock:
            parts.append(
                ("source NOT IN (?,?) AND url NOT LIKE ?", ("本地模拟源", "Mock Wire", "https://example.local/%"))
            )
        where, params = make_where(parts)
        if balanced_groups:
            items = self.repo.db.query(
                "SELECT * FROM (SELECT n.*, c.metadata AS classification, "
                "ROW_NUMBER() OVER (PARTITION BY c.region, c.topics LIKE '%\"policy\"%' "
                "ORDER BY julianday(n.published_at) DESC, n.id DESC) AS group_rank "
                "FROM news_items n LEFT JOIN news_classification c ON c.news_id = n.id "
                f"WHERE {where or '1=1'}) ORDER BY group_rank, julianday(published_at) DESC, id DESC LIMIT ?",
                (*params, page_size),
            )
            result: dict[str, Any] = {"items": items, "page": 1, "page_size": page_size, "total": len(items)}
        else:
            result = self.repo.page("news_items", page, page_size, where, params, order_by="published_at DESC")
        for item in result["items"]:
            if balanced_groups:
                metadata = item.pop("classification")
                item.pop("group_rank")
            else:
                record = self.repo.db.query_one(
                    "SELECT metadata FROM news_classification WHERE news_id=?", (item["id"],)
                )
                metadata = record["metadata"] if record else None
            if metadata:
                item.update(json.loads(metadata))
            item["keywords"] = json.loads(item["keywords"] or "[]")
            score = item.pop("sentiment", None)
            item["sentiment"] = "positive" if score and score > 0.1 else "neutral"
            item["symbols"] = []
        return result

    def keyword_cloud(
        self, scope: str, category: str | None, top_n: int, region="all", topic="all", keyword=None, source=None
    ) -> Any:
        if self.data.market == "HK":
            return []
        start, end = (None, None) if scope == "all" else time_range(scope)
        rows = self.list_news(
            category,
            keyword,
            source,
            1,
            policy()["limits"]["sample"],
            region=region,
            topic=topic,
            start_time=start,
            end_time=end,
        )["items"]
        return ranked_keywords(rows, top_n)
