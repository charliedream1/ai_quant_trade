"""Real pointer interaction and dated inbox behavior in the embedded workspace."""

import json
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace

import pytest
import yaml
from playwright.sync_api import expect, sync_playwright

from src.notifications.dates import window
from src.notifications.store import NotificationStore
from tests.frontend.test_page_lifetimes import wait_for


def test_news_geography_and_topic_clicks(cli_command, tmp_path):
    from src.core.timeutil import utc_now_iso
    from src.engine.market.news_aggregator import NewsAggregator

    fixtures = yaml.safe_load(Path(__file__).with_name("research_workspace_fixtures.yaml").read_text(encoding="utf-8"))[
        "news"
    ]
    rows = [
        {
            **row,
            "summary": "Declared browser fixture",
            "source": "本地模拟源",
            "url": f"https://example.org/browser/{index}",
            "published_at": utc_now_iso(),
            "fetched_at": utc_now_iso(),
            "keywords": [str(index)],
            "sentiment": "neutral",
        }
        for index, row in enumerate(fixtures)
    ]
    NewsAggregator(data=SimpleNamespace(market="CN", is_mock=True, list_news=lambda: rows)).seed_if_empty()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            page.goto(cli_command.base_url + "/app/?module=market&view=news", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#news-region")).to_be_visible(timeout=90000)
            frame.locator("#news-region input").click()
            frame.get_by_role("option", name="海外", exact=True).click()
            frame.locator("#news-topic input").click()
            frame.get_by_role("option", name="财经经济", exact=True).click()
            frame.get_by_role("button", name="查询", exact=True).click()
            expect(frame.get_by_text(fixtures[1]["title"], exact=True).filter(visible=True).last).to_be_visible(
                timeout=30000
            )
            expect(frame.get_by_text(fixtures[0]["title"], exact=True)).to_have_count(0)
            expect(frame.get_by_text(fixtures[4]["title"], exact=True)).to_have_count(0)
            expect(frame.get_by_text(rows[1]["published_at"], exact=True).filter(visible=True).last).to_be_visible()
            page.screenshot(path=str(tmp_path / "overseas-finance-filter.png"))
        finally:
            browser.close()


@pytest.fixture
def compatible_model():
    answer_started, release_answer = Event(), Event()
    release_answer.set()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            from src.knowledge.config import knowledge_config

            prompt = str(body["messages"][-1]["content"])
            prefix = knowledge_config()["search"]["planner_prompt"].splitlines()[0]
            if not prompt.startswith(prefix):
                answer_started.set()
                if not release_answer.wait(60):
                    raise TimeoutError("Controlled answer gate was not released")
            text = (
                json.dumps({"keywords": ["policy", "rate"], "sufficient": True})
                if prompt.startswith(prefix)
                else "The declared policy rate is 4.25% [1]."
            )
            result = {
                "model": "controlled-model",
                "choices": [{"message": {"role": "assistant", "content": text}}],
                "usage": {},
            }
            encoded = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()

    class Endpoint(str):
        answer_started: Event
        release_answer: Event

    endpoint = Endpoint(f"http://127.0.0.1:{server.server_port}/v1")
    endpoint.answer_started = answer_started
    endpoint.release_answer = release_answer
    try:
        yield endpoint
    finally:
        release_answer.set()
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_floating_qa_uses_configured_http_model_and_full_citation(client, cli_command, compatible_model, tmp_path):
    from src.agent.model_catalog import create_model

    create_model(
        {
            "name": "Controlled HTTP acceptance",
            "model_name": "controlled-model",
            "base_url": compatible_model,
            "level": "fast",
        }
    )
    result = client.post(
        "/api/v1/kb/notes",
        json={"title": "Declared rate evidence", "content": "# Policy\n\nThe declared policy rate is 4.25%."},
    ).json()
    assert result["code"] == 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            page.goto(cli_command.base_url + "/app/?module=market&view=quotes", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#market-quotes-refresh")).to_be_visible(timeout=90000)
            frame.locator('#ai-floating-button[data-drag-ready="1"]').click()
            panel = frame.locator("#ai-floating-panel")
            panel.get_by_role("tab", name="知识问答", exact=True).click()
            panel.locator("#floating-kb-question textarea").fill("What is the policy rate?")
            panel.locator("#floating-kb-ask").click()
            expect(panel.locator("#floating-kb-answer")).to_contain_text("4.25%", timeout=60000)
            panel.get_by_role("tab", name="来源与完整引用", exact=True).click()
            page.screenshot(path=str(tmp_path / "before-citation.png"))
            (tmp_path / "citation-dom.html").write_text(panel.inner_html(), encoding="utf-8")
            panel.locator("#floating-kb-sources").get_by_text("Declared rate evidence", exact=True).filter(
                visible=True
            ).last.click()
            expect(panel.locator(".citation-full")).to_contain_text("4.25%", timeout=15000)
            page.screenshot(path=str(tmp_path / "complete-citation.png"))
            panel.locator("#rag-file-reader a").click()
            reader = frame.frame_locator(".file-reader-panel iframe")
            expect(reader.locator("#file-title")).to_contain_text("Declared rate evidence", timeout=15000)
            expect(reader.locator("#markdown-preview")).to_contain_text("4.25%")
            page.screenshot(path=str(tmp_path / "original-source.png"))
        finally:
            browser.close()


def test_assistant_resize_and_daily_inbox(cli_command, tmp_path):
    store = NotificationStore()
    start, _, _ = window()
    previous = (datetime.fromisoformat(start) - timedelta(hours=1)).isoformat()
    target = {"module": "market", "view": "news"}
    store.publish("fixture", "today", "info", "Current inbox fixture", "Today's observation", target, start)
    store.publish("fixture", "yesterday", "info", "Historical inbox fixture", "Earlier observation", target, previous)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            page.goto(cli_command.base_url + "/app/?module=market&view=quotes", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#market-quotes-refresh")).to_be_visible(timeout=90000)
            frame.locator('#ai-floating-button[data-drag-ready="1"]').click()
            panel = frame.locator("#ai-floating-panel")
            expect(panel).to_be_visible()
            panel.get_by_role("tab", name="知识问答", exact=True).click()
            handle = panel.locator(".assistant-resize-handle")
            handle.scroll_into_view_if_needed()
            before = panel.bounding_box()
            point = handle.bounding_box()
            assert before is not None and point is not None
            page.mouse.move(point["x"] + 12, point["y"] + 12)
            page.mouse.down()
            page.mouse.move(point["x"] + 110, point["y"] + 65, steps=8)
            page.mouse.up()
            after = panel.bounding_box()
            assert after is not None
            assert after["width"] > before["width"] + 50
            panel.get_by_role("tab", name="来源与完整引用", exact=True).click()
            expect(panel.locator("#floating-kb-sources")).to_be_visible()
            page.screenshot(path=str(tmp_path / "resized-assistant.png"))
            panel.locator("#ai-floating-close").click()
            page.locator("#workspace-notification-toggle").click()
            center = page.locator("#notification-center")
            expect(center.get_by_text("Current inbox fixture", exact=True)).to_be_visible(timeout=15000)
            expect(center.get_by_text("Historical inbox fixture", exact=True)).to_have_count(0)
            center.get_by_role("button", name="查看历史", exact=True).click()
            expect(center.get_by_text("Historical inbox fixture", exact=True)).to_be_visible(timeout=15000)
            page.screenshot(path=str(tmp_path / "dated-inbox.png"))
            page.set_viewport_size({"width": 420, "height": 900})
            center.get_by_role("button", name="关闭", exact=True).click()
            frame.locator('#ai-floating-button[data-drag-ready="1"]').click()
            mobile = panel.bounding_box()
            assert mobile is not None and mobile["width"] <= 420
            page.screenshot(path=str(tmp_path / "assistant-mobile.png"))
        finally:
            browser.close()


def test_financial_subview_cancels_without_blocking_graph(cli_command, monkeypatch, tmp_path):
    import re
    from time import monotonic

    from src.frontend import page_reads
    from tests.frontend.page_worker_fixture import serve

    page_reads.shutdown()
    monkeypatch.setattr(page_reads, "serve", serve)
    page_reads.start()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            page.goto(cli_command.base_url + "/app/?module=market&view=fundamentals", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#fundamentals-load")).to_be_visible(timeout=90000)
            frame.locator("#fundamentals-load").click()
            wait_for(lambda: bool(page_reads.BUSY), 10)
            began = monotonic()
            frame.get_by_role("tab", name=re.compile("Technical analysis|技术分析")).click()
            wait_for(lambda: not page_reads.BUSY, 8)
            page.locator('[data-workspace-view="relations"]').click()
            expect(frame.locator("#rule-graph-start")).to_be_visible(timeout=3000)
            (tmp_path / "subview-navigation.json").write_text(
                json.dumps({"cleanup_and_navigation_seconds": monotonic() - began}), encoding="utf-8"
            )
            page.screenshot(path=str(tmp_path / "responsive-graph.png"))
        finally:
            browser.close()


def test_stock_recommendation_and_factor_workspace_controls(cli_command):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 940})
            page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
            page.goto(cli_command.base_url + "/app/?module=market&view=stock", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            stock = frame.locator("#stock-research-tabs")
            expect(stock).to_be_visible(timeout=90000)
            stock.get_by_role("button", name="读取上市公司概况", exact=True).click()
            expect(stock.get_by_text("600519", exact=True).last).to_be_visible(timeout=30000)
            stock.get_by_role("tab", name="事件与风险", exact=True).click()
            stock.get_by_role("button", name="计算风险指标", exact=True).click()
            expect(stock.get_by_text("区间最大回撤（%）", exact=True)).to_be_visible(timeout=30000)
            expect(page.locator("#workspace-page-report")).to_have_text("AI 分析")

            page.locator('[data-workspace-view="recommendations"]').click()
            recommendations = frame.locator("#recommendation-workspace")
            recommendations.get_by_role("tab", name="候选对比", exact=True).click()
            expect(recommendations.get_by_role("button", name="多组参数对比", exact=True)).to_be_visible()
            recommendations.get_by_role("tab", name="回测", exact=True).click()
            expect(recommendations.get_by_role("button", name="用前 5 只候选创建回测", exact=True)).to_be_visible()

            page.locator('[data-workspace-module="strategy"]').click()
            page.locator('[data-workspace-view="factors"]').click()
            log = frame.locator(".block.factor-event-log")
            expect(log).to_be_visible(timeout=30000)
            assert log.evaluate(
                """element => {
                    for (let index = 0; index < 50; index += 1) {
                        const line = document.createElement("p");
                        line.textContent = "Progress " + index;
                        element.append(line);
                    }
                    return element.scrollHeight > element.clientHeight &&
                           getComputedStyle(element).overflowY === "auto";
                }"""
            )
        finally:
            browser.close()
