"""Both lazy views load without fetching sources or generating model responses."""

from playwright.sync_api import expect, sync_playwright

from src.data.economics import EconomicDataSource


def test_browser_economic_views(economic_sources, cli_command, tmp_path, monkeypatch):
    calls = []
    original = EconomicDataSource.fetch

    def counted(self, *args, **kwargs):
        calls.append(args[0])
        return original(self, *args, **kwargs)

    monkeypatch.setattr(EconomicDataSource, "fetch", counted)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1100})
        page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
        page.goto(cli_command.base_url + "/app/?module=market&view=macro", wait_until="domcontentloaded")
        frame = page.frame_locator("iframe.workspace-frame.active")
        expect(frame.locator("#macro-load")).to_be_visible(timeout=90000)
        assert not calls
        frame.locator("#macro-load").click()
        expect(frame.locator("#macro-status")).to_contain_text("当前公开版本", timeout=30000)
        assert len(calls) == 8
        page.screenshot(path=str(tmp_path / "macroeconomics.png"))
        page.locator('[data-workspace-view="fundamentals"][data-workspace-view-module="market"]').click()
        expect(frame.locator("#fundamentals-load")).to_be_visible(timeout=30000)
        assert len(calls) == 8
        frame.locator("#fundamentals-symbol textarea").fill("600519")
        frame.locator("#fundamentals-load").click()
        expect(frame.locator("#fundamentals-status")).to_contain_text("当前公开版本", timeout=30000)
        assert len(calls) == 12
        expect(frame.get_by_text("营收TTM", exact=True)).to_be_visible()
        page.screenshot(path=str(tmp_path / "fundamentals.png"))
        browser.close()
