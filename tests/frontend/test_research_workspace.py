"""News, dated inboxes, real-model guards and nonblocking lifecycle invariants."""

from datetime import datetime, timedelta
from pathlib import Path
from threading import Event, Thread
from time import perf_counter
from uuid import uuid4

import pytest
import yaml

from src.core.exceptions import BusinessError
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso


@pytest.fixture
def news_rows():
    values = yaml.safe_load(Path(__file__).with_name("research_workspace_fixtures.yaml").read_text(encoding="utf-8"))
    return values["news"]


def test_explainable_news_geography_and_subject_are_independent(news_rows):
    from src.engine.market.news_policy import classify

    for row in news_rows:
        result = classify(row)
        assert result["region"] == row["region"]
        assert row["topic"] in result["topics"]
        assert result["market_relevant"] == row["relevant"]
        assert bool(result["relevance_reasons"]) == row["relevant"]


def test_news_listing_and_cloud_use_same_geography(client, news_rows):
    from types import SimpleNamespace

    from src.engine.market.news_aggregator import NewsAggregator

    rows = [
        {
            **row,
            "id": index,
            "summary": "",
            "source": "Declared fixture",
            "url": f"https://example.org/{index}",
            "published_at": utc_now_iso(),
            "fetched_at": utc_now_iso(),
            "keywords": [str(index)],
            "sentiment": "neutral",
        }
        for index, row in enumerate(news_rows)
    ]
    source = SimpleNamespace(market="CN", is_mock=False, list_news=lambda: rows)
    service = NewsAggregator(data=source)
    listed = service.list_news(None, None, None, 1, 100)
    assert len(listed["items"]) == sum(row["relevant"] for row in news_rows)
    overseas = service.list_news(None, None, None, 1, 100, region="overseas", topic="finance")
    assert len(overseas["items"]) == 1
    cloud = service.keyword_cloud("day", None, 30, region="overseas", topic="finance")
    assert cloud
    assert {row["headline"] for row in cloud} == {overseas["items"][0]["title"]}
    assert Repository().db.scalar("SELECT COUNT(*) FROM news_items") == len(news_rows)


def test_invalid_news_time_stays_unknown():
    from src.data.eastmoney import EastmoneyDataSource
    from src.engine.market.news_policy import classify

    assert EastmoneyDataSource._news_time("unverified") == ""
    assert classify({"title": "央行利率", "published_at": ""})["time_status"] == "unknown"


def test_news_center_includes_previous_day_in_table_and_keyword_chart(client, monkeypatch, news_rows):
    from types import SimpleNamespace

    from src.engine.market.news_aggregator import NewsAggregator
    from src.frontend.service import market

    timestamp = (datetime.fromisoformat(utc_now_iso()) - timedelta(days=1)).isoformat()
    sample = next(row for row in news_rows if row["region"] == "overseas" and row["topic"] == "finance")
    rows = [
        {
            **sample,
            "summary": "",
            "source": "Declared fixture",
            "url": "https://example.org/news",
            "published_at": timestamp,
            "fetched_at": timestamp,
            "keywords": [],
            "sentiment": "neutral",
        }
    ]
    source = SimpleNamespace(market="CN", is_mock=False, list_news=lambda: rows)
    monkeypatch.setattr(market, "NewsAggregator", lambda: NewsAggregator(data=source))
    table, chart, status = market.MarketServiceMixin().news("全部", "", "", region="overseas", topic="finance")
    assert len(table) == 1 and chart.data and "TF-IDF" in status


def test_inbox_uses_local_day_occurrence_and_retains_history(client):
    from src.notifications.dates import window
    from src.notifications.store import NotificationStore

    store = NotificationStore()
    start, end, selected = window()
    early = (datetime.fromisoformat(start) - timedelta(seconds=1)).isoformat()
    target = {"module": "market", "view": "news"}
    before = store.publish("fixture", "before", "warning", "Previous day", "Original event", target, early)
    current = store.publish("fixture", "current", "success", "Today", "Original event", target, start)
    critical = store.publish("fixture", "critical", "critical", "Earlier unresolved", "Original event", target, early)
    result = store.feed("window-a", initial=True)
    assert [row["id"] for row in result["items"]] == [current["id"]]
    assert result["selected_date"] == selected and result["events"] == []
    assert critical["id"] in [row["id"] for row in result["critical"]]
    store.read_all("window-a")
    assert store.feed("window-a")["unread"] == 0
    history = store.feed("window-a", history=True)
    assert {row["id"] for row in history["items"]} >= {before["id"], current["id"], critical["id"]}
    assert not next(row for row in history["items"] if row["id"] == before["id"])["read_at"]
    assert datetime.fromisoformat(end) - datetime.fromisoformat(start) == timedelta(days=1)


def test_no_mock_profile_or_fallback_in_assistant(client, monkeypatch):
    from src.agent.llm_client import LLMClient
    from src.agent.real_models import real_profile, require_real_model
    from src.frontend.service_dispatch import CallbackServices

    assert not real_profile({"model_name": "mock-llm", "base_url": "http://localhost:1234"})
    assert not real_profile({"model_name": "fixture", "base_url": "mock://generated"})
    assert real_profile({"model_name": "hy3", "base_url": "http://localhost:1234/v1"})
    assert CallbackServices().floating_models() == []
    with pytest.raises(BusinessError):
        with require_real_model():
            LLMClient().complete("This must not become a simulated answer")


def test_pool_warmup_does_not_wait_for_capacity_in_caller():
    from src.frontend import page_reads

    held, release = Event(), Event()

    def hold():
        with page_reads.CAPACITY:
            held.set()
            release.wait(5)

    worker = Thread(target=hold)
    worker.start()
    assert held.wait(2)
    try:
        started = perf_counter()
        page_reads.start(warm=True)
        assert perf_counter() - started < 0.1
    finally:
        release.set()
        worker.join(timeout=3)


def test_legacy_financial_link_resolves_to_shared_company():
    from src.frontend.common.navigation import resolve_destination
    from src.frontend.registry import get_module

    assert resolve_destination("market", "fundamentals") == {
        "module": "market",
        "view": "stock",
        "tab": "Financial analysis",
    }
    assert "fundamentals" not in dict(get_module("market").views)


def test_operation_logs_exclude_action_payload(client):
    from loguru import logger

    from src.frontend.common.callbacks import safe

    messages = []
    sink = logger.add(lambda entry: messages.append(str(entry)), level="INFO")
    try:
        assert safe(lambda value: True)("private-body-" + uuid4().hex)
    finally:
        logger.remove(sink)
    assert any("处理页面操作 · 开始" in message for message in messages)
    assert any("处理页面操作 · 完成" in message for message in messages)
    assert all("private-body" not in message for message in messages)
