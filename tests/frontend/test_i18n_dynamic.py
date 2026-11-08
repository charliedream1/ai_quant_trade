"""Language switching retains live control text and original Chinese labels."""

import re
from pathlib import Path

import yaml
from playwright.sync_api import expect, sync_playwright

from src.frontend.i18n import TRANSLATIONS, translate
from src.frontend.registry import MODULES


def test_modular_navigation_has_english_titles():
    for module in MODULES:
        assert not re.search(r"[\u3400-\u9fff]", translate(module.title)), module.key
    path = Path("egs/config/ui/ui_translations.yaml")
    additions = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert all(isinstance(key, str) and isinstance(value, str) for key, value in additions.items())
    assert all(TRANSLATIONS[key] == value for key, value in additions.items())


def test_dynamic_graph_buttons_and_language_round_trip(cli_command):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.add_init_script(
            "localStorage.setItem('all-in-one-ui-lang','en');localStorage.setItem('all-in-one-ui-market','us');"
        )
        page = context.new_page()
        page.goto(cli_command.base_url + "/app/?module=strategy&view=workshop", wait_until="domcontentloaded")
        graph = page.frame_locator("iframe.workspace-frame.active")
        enter = graph.get_by_role("button", name="Fullscreen Canvas", exact=True)
        expect(enter).to_be_visible(timeout=90000)
        expect(graph.get_by_label("Actual Run Status", exact=True)).to_have_value("Not Executed", timeout=15000)
        enter.click()
        exit_button = graph.get_by_role("button", name="Exit Fullscreen", exact=True)
        expect(exit_button).to_be_visible(timeout=15000)
        exit_button.click()
        expect(enter).to_be_visible(timeout=15000)
        page.locator("#app-language-toggle").click()
        expect(page.locator("html")).to_have_attribute("data-ui-lang", "zh", timeout=15000)
        expect(graph.get_by_role("button", name="全屏画布", exact=True)).to_be_visible(timeout=60000)
        expect(graph.get_by_label("实际运行状态", exact=True)).to_have_value("尚未执行", timeout=15000)
        expect(page.locator('[data-workspace-module="strategy"] strong')).to_have_text("策略构建")
        page.locator("#app-language-toggle").click()
        expect(enter).to_be_visible(timeout=60000)
        expect(page.locator('[data-workspace-module="strategy"] strong')).to_have_text("Strategy Build")
        page.goto(cli_command.base_url + "/app/?module=ai&view=main", wait_until="domcontentloaded")
        ai = page.frame_locator("iframe.workspace-frame.active")
        backend = ai.locator('#ai-console-backend input[role="listbox"]')
        expect(backend).to_have_value("Model API", timeout=60000)
        text = ai.locator("#ai-console-input textarea")
        expect(text).to_have_attribute("placeholder", re.compile("^Type a message"))
        text.fill("English test: keep the selected backend and the user message unchanged.")
        text.press("Enter")
        expect(ai.locator("#ai-console-status")).to_contain_text("mock", timeout=60000)
        expect(text).to_have_value("")
        browser.close()
