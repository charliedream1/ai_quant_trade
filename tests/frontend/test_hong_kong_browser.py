"""Browser HK market round trips and technical analysis with explicit development fixtures."""

import json
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from src.data import current_market, set_current_market


def test_hk_switch_stock_analysis_and_reload(cli_command, tmp_path, monkeypatch):
    original_market = current_market()
    if os.environ.get("HK_UI_REAL") == "1":
        monkeypatch.setenv("ALL_IN_ONE_DATA_MODE", "real")
    output = Path(os.environ.get("HK_UI_OUTPUT", str(tmp_path)))
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
            page.goto(cli_command.base_url + "/app/?module=market&view=stock", wait_until="domcontentloaded")
            page.locator("[data-workspace-market='hk']").click()
            expect(page.locator("[data-workspace-market='hk']")).to_have_class("active")
            frame = page.frame_locator("iframe.workspace-frame.active")
            symbol = frame.get_by_label("股票代码/名称", exact=True).filter(visible=True).first
            expect(symbol).to_be_visible(timeout=90000)
            symbol.fill("00700.HK")
            frame.get_by_role("button", name="分析", exact=True).click()
            page.screenshot(path=str(tmp_path / "hk-stock-request.png"))
            expect(frame.locator(".status-strip").filter(has_text="Currency: HKD").first).to_be_visible(timeout=30000)
            expect(frame.locator("#stock-kline-chart .js-plotly-plot")).to_be_visible(timeout=30000)
            if os.environ.get("HK_UI_REAL") == "1":
                expect(frame.locator(".status-strip").filter(has_text="tencent-hk").first).to_be_visible()
                assert "mock-local-hk" not in frame.locator(".status-strip").first.inner_text()
            page.screenshot(path=str(output / "hk-stock-analysis.png"))
            frame.locator("#stock-kline-chart").scroll_into_view_if_needed()
            expect(frame.locator("#stock-kline-chart .legendtext").filter(has_text="MA20")).to_have_text("MA20")
            page.screenshot(path=str(output / "hk-kline.png"))
            page.locator("#app-language-toggle").click()
            expect(page.locator("[data-workspace-market='hk']")).to_have_class("active")
            page.screenshot(path=str(output / "hk-english.png"))
            page.locator("#app-language-toggle").click()
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("[data-workspace-market='hk']")).to_have_class("active")
            page.locator("[data-workspace-market='us']").click()
            expect(page.locator("[data-workspace-market='us']")).to_have_class("active")
            page.locator("[data-workspace-market='hk']").click()
            expect(page.locator("[data-workspace-market='hk']")).to_have_class("active")
            page.locator("[data-workspace-market='cn']").click()
            expect(page.locator("[data-workspace-market='cn']")).to_have_class("active")
            page.locator("[data-workspace-market='hk']").click()
            page.goto(cli_command.base_url + "/app/?module=simulation&view=backtest", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.get_by_text("交易成本与执行假设", exact=True)).to_be_visible(timeout=90000)
            frame.get_by_text("交易成本与执行假设", exact=True).click()
            frame.get_by_label("费用方案", exact=True).click()
            frame.get_by_role("option", name="Hong Kong HKD cash equities", exact=True).click()
            frame.get_by_role("button", name="预览实际执行配置", exact=True).click()
            expect(frame.locator(".execution-cost-preview").filter(visible=True).first).to_contain_text(
                '"HKD"', timeout=30000
            )
            page.screenshot(path=str(output / "hk-execution-preview.png"))
            expect(frame.get_by_label("每外部订单最低佣金（HKD）", exact=True)).to_be_visible()
            page.set_viewport_size({"width": 390, "height": 844})
            expect(page.locator("#quant-workspace-shell")).to_have_class(re.compile("sidebar-collapsed"))
            expect(page.locator("[data-workspace-market='hk']")).to_be_visible()
            page.screenshot(path=str(output / "hk-mobile.png"))
            (output / "browser-checks.json").write_text(
                json.dumps(
                    {
                        "actual_market_feed": os.environ.get("HK_UI_REAL") == "1",
                        "chart_visible": True,
                        "language_preserves_hk": True,
                        "execution_preview_currency": "HKD",
                        "market_reload": True,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        finally:
            browser.close()
            set_current_market(original_market)
