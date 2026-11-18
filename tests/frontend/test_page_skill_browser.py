"""Actual page button, observed progress, HTML preview/history and rule-layout parity."""

import json
import re
from threading import Event
from urllib.parse import urljoin

import pytest
from playwright.sync_api import expect, sync_playwright


def test_sector_rule_capture_to_skill_report_without_automatic_generation(cli_command, monkeypatch, tmp_path):
    from src.engine.insights import execution
    from src.frontend.features import page_analysis

    calls = []
    entered, release = Event(), Event()
    monkeypatch.setattr(page_analysis, "capability", lambda *args: {})
    monkeypatch.setattr(execution, "validate_backend", lambda *args: {"model_name": "declared CLI"})

    def generate(prompt, payload, cfg, emit):
        calls.append(payload["page_task"])
        entered.set()
        assert release.wait(15)
        return json.dumps(
            {
                "title": "Declared sector report",
                "summary": "Observed rule evidence",
                "sections": [
                    {"heading": heading, "paragraphs": ["Declared interpretation"], "source_ids": ["E1"]}
                    for heading in cfg["tasks"]["page_analysis"]["sections"]
                ],
                "risks": [],
                "missing": [],
            }
        )

    monkeypatch.setattr(execution, "generate_text", generate)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        try:
            page.goto(cli_command.base_url + "/app/?module=market&view=quotes", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#market-quotes-refresh")).to_be_visible(timeout=90000)
            expect(frame.locator("#ai-floating-button")).to_have_attribute("data-drag-ready", "1", timeout=15000)
            assert calls == []
            frame.locator("#market-quotes-refresh").click()
            expect(frame.locator("#market-sectors-plot .js-plotly-plot")).to_be_visible(timeout=60000)
            frame.get_by_text("CLI + Skill analysis", exact=True).click()
            frame.locator("#page-skill-run").click()
            assert entered.wait(10)
            expect(frame.locator("#page-skill-progress textarea")).not_to_have_value("", timeout=10000)
            release.set()
            expect(frame.locator("#page-skill-preview iframe")).to_be_visible(timeout=30000)
            expect(
                frame.frame_locator("#page-skill-preview iframe").get_by_role("heading", name="Declared sector report")
            ).to_be_visible()
            assert calls == ["sectors"]
            saved = tmp_path / "downloaded-report.html"
            link = frame.locator("#page-skill-download a").first.get_attribute("href")
            assert link
            response = page.request.get(urljoin(page.url, link))
            assert response.ok
            saved.write_bytes(response.body())
            from src.engine.insights.store import InsightStore

            row = InsightStore().history(1)[0]
            assert saved.read_bytes() == InsightStore().artifact(row["run_id"], "report.html").read_bytes()
            frame.locator("#page-skill-history-refresh").click()
            frame.locator("#page-skill-history input").click()
            frame.get_by_role("option", name=re.compile("Declared sector report")).click()
            frame.locator("#page-skill-history-open").click()
            expect(
                frame.frame_locator("#page-skill-preview iframe").get_by_role("heading", name="Declared sector report")
            ).to_be_visible()
            assert calls == ["sectors"]
            expect(frame.locator("#market-sectors-plot .js-plotly-plot")).to_be_visible()
            page.locator('[data-workspace-view="news"]').click()
            expect(frame.locator("#page-skill-task input")).not_to_be_visible(timeout=10000)
            frame.get_by_text("CLI + Skill analysis", exact=True).click()
            expect(frame.locator("#page-skill-task input")).to_have_value("Market and policy news analysis")
            assert calls == ["sectors"]
            page.screenshot(path=str(tmp_path / "sector-skill-report.png"), full_page=True)
        except Exception:
            page.screenshot(path=str(tmp_path / "failed-page-skill.png"), full_page=True)
            (tmp_path / "panel-dom.txt").write_text(
                frame.locator("#page-skill-panel").evaluate(
                    "el => JSON.stringify({tag:el.tagName, children:[...el.children].map(c=>({tag:c.tagName,cls:c.className,role:c.getAttribute('role'),text:c.innerText.slice(0,80)})), buttons:[...el.querySelectorAll('button')].slice(0,3).map(c=>c.outerHTML.slice(0,500))})"
                ),
                encoding="utf-8",
            )
            raise
        finally:
            release.set()
            browser.close()


@pytest.mark.parametrize("action", ["cancel", "navigate"])
def test_pending_report_stops_without_blocking_rule_view(cli_command, monkeypatch, action):
    from time import sleep

    from src.engine.insights import execution
    from src.frontend.features import page_analysis

    entered, stopped = Event(), Event()
    monkeypatch.setattr(page_analysis, "capability", lambda *args: {})
    monkeypatch.setattr(execution, "validate_backend", lambda *args: {})

    def generate(prompt, payload, cfg, emit):
        entered.set()
        while not payload["_cancelled"]():
            sleep(0.02)
        stopped.set()
        raise InterruptedError("Declared pending CLI cancellation")

    monkeypatch.setattr(execution, "generate_text", generate)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        try:
            page.goto(cli_command.base_url + "/app/?module=market&view=quotes", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#ai-floating-button")).to_have_attribute("data-drag-ready", "1", timeout=90000)
            frame.locator("#market-quotes-refresh").click()
            expect(frame.locator("#market-sectors-plot .js-plotly-plot")).to_be_visible(timeout=60000)
            frame.get_by_text("CLI + Skill analysis", exact=True).click()
            frame.locator("#page-skill-run").click()
            assert entered.wait(10)
            if action == "cancel":
                frame.locator("#page-skill-cancel").click()
            else:
                page.locator('[data-workspace-view-module="market"][data-workspace-view="news"]').click()
            assert stopped.wait(8)
            if action == "navigate":
                expect(frame.locator("#page-skill-task input")).not_to_be_visible()
                page.locator('[data-workspace-view-module="market"][data-workspace-view="quotes"]').click()
            frame.locator("#market-quotes-refresh").click()
            expect(frame.locator("#market-sectors-plot .js-plotly-plot")).to_be_visible(timeout=15000)
        finally:
            browser.close()
