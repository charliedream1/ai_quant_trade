"""A slow section must not hide an already completed section on the same page."""

import re
from time import monotonic

import pytest
from playwright.sync_api import expect, sync_playwright

from src.core.config import get_settings
from src.frontend import page_reads
from tests.frontend.section_worker_fixture import serve
from tests.frontend.test_page_lifetimes import wait_for
from tests.frontend.test_workspace_interaction_browser import compatible_model  # noqa: F401


def assert_readable(locator):
    opacity = locator.evaluate("""element => {
        let opacity = 1;
        for (let node = element; node; node = node.parentElement) {
            opacity *= Number(getComputedStyle(node).opacity);
        }
        return opacity;
    }""")
    assert opacity >= 0.95, "Completed content must not be dimmed by a whole-callback overlay"


@pytest.mark.parametrize("fail", [False, True])
def test_completed_indices_are_visible_while_sectors_are_blocked(cli_command, monkeypatch, tmp_path, fail):
    page_reads.shutdown()
    monkeypatch.setattr(page_reads, "serve", serve)
    page_reads.start()
    root = get_settings().data_dir
    if fail:
        (root / "fail-sector").write_text("fail", encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            page.goto(cli_command.base_url + "/app/?module=market&view=quotes", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            refresh = frame.locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]')
            expect(refresh).to_be_visible(timeout=90000)
            expect(frame.locator("#market-news-results, #stock-kline-chart")).to_have_count(0)
            refresh.click()
            wait_for((root / "sector-waiting").exists, 60)
            expect(
                frame.locator("#market-indices")
                .get_by_text("Visible before sector completion", exact=True)
                .filter(visible=True)
                .last
            ).to_be_visible(timeout=10000)
            assert page_reads.BUSY
            expect(frame.locator("#market-indices")).to_have_class(re.compile("section-ready"))
            assert_readable(
                frame.locator("#market-indices")
                .get_by_text("Visible before sector completion", exact=True)
                .filter(visible=True)
                .last
            )
            expect(frame.locator("#market-sectors")).to_have_class(re.compile("section-loading"))
            expect(frame.locator("#market-sectors-plot .js-plotly-plot")).to_have_count(0)
            page.screenshot(path=str(tmp_path / "indices-ready-sector-loading.png"))
            began = monotonic()
            (root / "release-sector").touch()
            if fail:
                expect(frame.locator("#market-sectors")).to_have_class(re.compile("section-failed"), timeout=15000)
                expect(
                    frame.locator("#market-indices")
                    .get_by_text("Visible before sector completion", exact=True)
                    .filter(visible=True)
                    .last
                ).to_be_visible()
                (root / "fail-sector").write_text("retry", encoding="utf-8")
                refresh.click()
            expect(frame.locator("#market-sectors-plot .js-plotly-plot")).to_be_visible(timeout=15000)
            wait_for(lambda: not page_reads.BUSY, 5)
            assert monotonic() - began < 15
            page.screenshot(path=str(tmp_path / "all-sections-ready.png"))
        finally:
            (root / "release-sector").touch()
            browser.close()


def test_citations_are_visible_before_model_answer(client, cli_command, compatible_model, tmp_path):  # noqa: F811
    from src.agent.model_catalog import create_model

    create_model(
        {
            "name": "Declared gated HTTP model",
            "model_name": "controlled-model",
            "base_url": str(compatible_model),
            "level": "fast",
        }
    )
    result = client.post(
        "/api/v1/kb/notes",
        json={"title": "Early reference evidence", "content": "# Policy\n\nThe declared policy rate is 4.25%."},
    ).json()
    assert result["code"] == 0
    compatible_model.release_answer.clear()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            page.goto(cli_command.base_url + "/app/?module=market&view=quotes", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]')).to_be_visible(timeout=90000)
            frame.locator('#ai-floating-button[data-drag-ready="1"]').click()
            panel = frame.locator("#ai-floating-panel")
            panel.get_by_role("tab", name="知识问答", exact=True).click()
            panel.locator("#floating-kb-question textarea").fill("What is the policy rate?")
            panel.locator("#floating-kb-ask").click()
            panel.get_by_role("tab", name="来源与完整引用", exact=True).click()
            expect(
                panel.locator("#floating-kb-sources")
                .get_by_text("Early reference evidence", exact=True)
                .filter(visible=True)
                .last
            ).to_be_visible(timeout=60000)
            assert compatible_model.answer_started.wait(5)
            assert_readable(
                panel.locator("#floating-kb-sources")
                .get_by_text("Early reference evidence", exact=True)
                .filter(visible=True)
                .last
            )
            expect(panel.locator("#floating-kb-answer")).to_have_class(re.compile("section-loading"))
            page.screenshot(path=str(tmp_path / "citations-before-model.png"))
            compatible_model.release_answer.set()
            panel.get_by_role("tab", name="回答", exact=True).click()
            expect(panel.locator("#floating-kb-answer")).to_contain_text("4.25%", timeout=30000)
        finally:
            compatible_model.release_answer.set()
            browser.close()
