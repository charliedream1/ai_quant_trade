"""Cold home-page loads must safely seed the same news concurrently."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from src.core.repository import Repository
from src.data import DataSourceManager
from src.engine.market.news_aggregator import NewsAggregator


def test_concurrent_cold_news_seed_deduplicates_atomically(client, monkeypatch):
    source = DataSourceManager(mode="mock", market="CN")
    original = source.list_news
    expected = original()
    barrier = Barrier(8)

    def load():
        barrier.wait(timeout=10)
        return original()

    monkeypatch.setattr(source, "list_news", load)

    def query(_):
        return NewsAggregator(data=source).list_news(None, None, None, 1, 20)["total"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        counts = list(pool.map(query, range(8)))
    assert all(count > 0 for count in counts)
    assert Repository().db.scalar("SELECT COUNT(*) FROM news_items") == len(expected)
    assert Repository().db.scalar("SELECT COUNT(DISTINCT dedup_hash) FROM news_items") == len(expected)


def test_other_market_news_does_not_prevent_seeding_current_market(client):
    for market in ("CN", "US"):
        result = NewsAggregator(data=DataSourceManager(mode="mock", market=market)).list_news(None, None, None, 1, 20)
        assert result["total"] > 0
