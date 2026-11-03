"""News listing and keyword analysis."""

import hashlib
import json
from collections import Counter
from typing import Any

from src.core.repository import Repository, make_where
from src.data import MARKET_US, DataSourceManager


class NewsAggregator:
    def __init__(self, repo: Repository | None = None, data: DataSourceManager | None = None) -> None:
        self.repo = repo or Repository()
        self.data = data or DataSourceManager()

    def _mock_source_label(self) -> str:
        return "Mock Wire" if self.data.market == MARKET_US else "本地模拟源"

    def seed_if_empty(self, force_refresh: bool = False) -> None:
        if not self.data.is_mock:
            self.repo.db.execute(
                "DELETE FROM news_items WHERE source IN (?, ?) OR url LIKE ?",
                ("本地模拟源", "Mock Wire", "https://example.local/%"),
            )
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
    ) -> dict[str, Any]:
        self.seed_if_empty(force_refresh=refresh)
        parts: list[tuple[str, Any]] = []
        if category:
            parts.append(("category = ?", category))
        if keyword:
            pattern = f"%{keyword}%"
            parts.append(("(title LIKE ? OR summary LIKE ?)", (pattern, pattern)))
        if source:
            parts.append(("source = ?", source))
        elif self.data.is_mock:
            parts.append(("source = ?", self._mock_source_label()))
        where, params = make_where(parts)
        result = self.repo.page("news_items", page, page_size, where, params, order_by="published_at DESC")
        for item in result["items"]:
            item["keywords"] = json.loads(item["keywords"] or "[]")
            score = item.pop("sentiment", None)
            item["sentiment"] = "positive" if score and score > 0.1 else "neutral"
            item["symbols"] = []
        return result

    def keyword_cloud(self, scope: str, category: str | None, top_n: int) -> Any:
        self.seed_if_empty()
        rows = self.repo.list(
            "news_items",
            where="category = ?" if category else "",
            params=(category,) if category else (),
            order_by="published_at DESC",
            limit=500,
        )
        counts: Counter[str] = Counter()
        for item in rows:
            try:
                counts.update(json.loads(item.get("keywords") or "[]"))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        total = max(sum(counts.values()), 1)
        return [
            {
                "keyword": keyword,
                "count": count,
                "weight": round(count / total, 4),
                "sentiment": "neutral",
            }
            for keyword, count in counts.most_common(top_n)
        ]
