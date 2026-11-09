"""Navigation consolidation and localized curriculum remain inspectable and offline."""

import re

from playwright.sync_api import expect, sync_playwright

from src.frontend.common.navigation import resolve_destination
from src.frontend.features.learning import curriculum, localized_chapter_values
from src.frontend.registry import get_module


def test_etf_old_destination_opens_strategy_management_tools():
    assert "etf" not in dict(get_module("strategy").views)
    assert resolve_destination("strategy", "etf") == {"module": "strategy", "view": "management", "tab": "ETF研究"}


def test_every_course_has_a_real_english_document():
    _, chapters = curriculum()
    for chapter in chapters:
        english = localized_chapter_values(chapter["id"])[-1]
        assert len(english) > 500
        assert not re.search(r"[\u3400-\u9fff]", english)
        assert "Exercise" in english or chapter["id"] == "guide"


def test_real_workspace_language_learning_and_width(cli_command):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        context.add_init_script(
            "localStorage.setItem('all-in-one-ui-lang','en');localStorage.setItem('all-in-one-ui-market','us');"
        )
        page = context.new_page()
        page.goto(cli_command.base_url + "/app/?module=learning&view=course", wait_until="domcontentloaded")
        frame = page.frame_locator("iframe.workspace-frame.active")
        reader = frame.locator("#quant-course-content-en")
        expect(reader).to_be_visible(timeout=90000)
        expect(reader).to_contain_text("Quantitative research course")
        expect(reader.get_by_role("heading", name="Quantitative research course", exact=True)).to_be_visible()
        for dismiss in page.locator("#notification-toasts .notification-card-top button").all():
            if dismiss.is_visible():
                dismiss.click()
        frame.get_by_role("button", name="Next Chapter", exact=True).click()
        expect(reader).to_contain_text("01 Research process and hypotheses")
        selected = frame.locator("#quant-course-chapters input:checked")
        expect(selected).to_have_value("research")
        page.locator("#app-language-toggle").click()
        expect(frame.locator("#quant-course-content")).to_be_visible()
        expect(frame.locator("#quant-course-content")).to_contain_text("研究流程与假设")
        expect(selected).to_have_value("research")
        page.locator("#app-language-toggle").click()
        expect(reader).to_be_visible()
        expect(selected).to_have_value("research")
        shell = page.locator("#quant-workspace-shell").bounding_box()
        assert shell and shell["x"] == 0 and shell["y"] == 0 and shell["width"] == 1920
        for width in (1366, 390):
            page.set_viewport_size({"width": width, "height": 900})
            frame.locator("#quant-course-chapters").scroll_into_view_if_needed()
            child = next(item for item in page.frames if "/app/learning/" in item.url)
            assert child.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
        page.set_viewport_size({"width": 1366, "height": 900})
        page.goto(cli_command.base_url + "/app/?module=strategy&view=etf", wait_until="domcontentloaded")
        frame = page.frame_locator("iframe.workspace-frame.active")
        refresh = frame.get_by_role("button", name="Refresh ETF Data", exact=True)
        expect(refresh).to_be_visible(timeout=90000)
        refresh.click()
        expect(frame.get_by_text("ETF Metadata and Source Snapshot", exact=True).first).to_be_visible()
        assert page.locator("[data-workspace-view='etf']").count() == 0
        browser.close()
