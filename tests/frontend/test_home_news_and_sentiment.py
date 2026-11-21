"""Regression coverage for grouped headlines, scope, sentiment and language switching."""

from datetime import datetime, timezone
from types import SimpleNamespace

from playwright.sync_api import expect, sync_playwright

from src.engine.market.news_aggregator import NewsAggregator
from src.engine.market.news_topics import grouped_topics, ranked_keywords, terms, time_range
from src.engine.market.quote_service import QuoteService
from src.frontend.service.home_charts import sentiment_radar
from src.frontend.service.home_news_view import _dashboard_news_html


def test_sentiment_zero_missing_and_complete_coverage():
    rows = [{"code": str(index), "change_pct": value, "universe_total": 4} for index, value in enumerate([-6, 0, 0, 5])]
    service = QuoteService.__new__(QuoteService)
    service.data = SimpleNamespace(is_mock=False, sectors=lambda **_: rows)
    _, valid = service.sector_snapshot(100)
    assert len(valid) == 4
    figure = sentiment_radar([{"change_pct": -3}], valid)
    assert tuple(figure.data[0].r) == (0, 25, 0, 0)
    assert "0.0 / 100" in figure.layout.polar.angularaxis.ticktext[0]
    assert "0.0 / 100" in figure.layout.polar.angularaxis.ticktext[2]
    service.data = SimpleNamespace(is_mock=False, sectors=lambda **_: rows[:2])
    _, unavailable = service.sector_snapshot(100)
    assert unavailable == []
    partial = sentiment_radar([{"change_pct": 0}], unavailable)
    assert tuple(partial.data[0].r) == (50, None, None, 50)
    assert "未提供" in partial.layout.polar.angularaxis.ticktext[1]


def test_phrase_boundaries_time_scope_and_syndicated_topic_counts(client):
    assert "城市更新" in terms("多地密集推进城市更新改造工程")
    assert "推进城市" not in terms("多地密集推进城市更新改造工程")
    assert {"半导体设备", "先进封装"}.issubset(terms("半导体设备订单增长推动先进封装产能建设"))
    assert "美联储" in terms("Federal Reserve signals lower rates")
    now = datetime(2026, 11, 20, 17, tzinfo=timezone.utc)
    start, end = time_range("day", now=now)
    assert start == "2026-11-21T00:00:00+08:00"
    assert end == "2026-11-21T01:00:00+08:00"
    headline = "半导体设备订单增长推动先进封装产能建设"
    rows = [{"title": headline, "source": source, "published_at": end} for source in ("A", "B")]
    ranking = {item["keyword"]: item for item in ranked_keywords(rows, 12, now=now)}
    assert ranking["先进封装"]["count"] == 1
    assert grouped_topics(rows)[0]["count"] == 1


def test_grouped_headlines_are_dense_balanced_and_escape_sources():
    rows = [
        {
            "title": f"{subject} {index:02d}",
            "source": "Source",
            "region": region,
            "topics": [topic],
            "url": "javascript:fixture",
            "summary": "<script>fixture</script>",
        }
        for subject, region, topic in (
            ("Domestic market announcement", "domestic", "finance"),
            ("International rate announcement", "overseas", "policy"),
        )
        for index in range(7)
    ]
    view = _dashboard_news_html({"items": rows})
    assert view.count("class='home-news-group'") == 2
    assert view.count("<li>") > 5
    assert "国内 · 财经经济" in view and "海外 · 时政政策" in view
    assert "javascript:" not in view and "<script>" not in view and "&lt;script&gt;" in view
    assert "港股新闻源尚未配置" in _dashboard_news_html({"items": [], "availability": "unavailable"})


def test_overview_candidates_reserve_space_for_rare_groups(client):
    stamp = datetime.now(timezone.utc).isoformat()
    titles = ["美国公司财报净利润上升", *[f"中国央行利率公告第 {index} 号" for index in range(8)]]
    rows = [
        {
            "title": title,
            "source": "Declared source",
            "category": "finance",
            "summary": "",
            "published_at": stamp,
            "fetched_at": stamp,
            "keywords": [],
            "sentiment": "neutral",
            "url": f"https://example.org/story/{index}",
        }
        for index, title in enumerate(titles)
    ]
    news = NewsAggregator(data=SimpleNamespace(market="CN", is_mock=False, list_news=lambda: rows))
    result = news.list_news(None, None, None, 1, 3, balanced_groups=True)
    assert len(result["items"]) == 3
    assert {row["region"] for row in result["items"]} == {"domestic", "overseas"}


def test_homepage_language_market_and_button_wrapping(cli_command, tmp_path):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(cli_command.base_url + "/app/?module=dashboard&view=overview", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            refresh = frame.locator("#home-refresh")
            expect(refresh).to_be_visible(timeout=90000)
            expect(frame.locator("#page-skill-panel")).to_have_count(0)
            expect(frame.locator("#home-news .dashboard-news-panel")).to_be_attached(timeout=90000)
            market = page.evaluate("localStorage.getItem('all-in-one-ui-market')")
            page.locator("#app-language-toggle").click()
            expect(refresh).to_have_text("Refresh Overview")
            assert page.evaluate("localStorage.getItem('all-in-one-ui-market')") == market
            expect(frame.locator("#home-sentiment")).to_contain_text("Intraday Index Momentum", timeout=90000)
            for width in (1440, 768, 390):
                page.set_viewport_size({"width": width, "height": 900})
                assert refresh.evaluate("el => el.scrollHeight <= el.clientHeight + 2")
                assert refresh.evaluate("el => el.scrollWidth <= el.clientWidth + 2")
            page.screenshot(path=str(tmp_path / "home-english-mobile.png"))
            page.locator("#app-language-toggle").click()
            expect(refresh).to_have_text("刷新总览")
            assert page.evaluate("localStorage.getItem('all-in-one-ui-market')") == market
        finally:
            browser.close()
