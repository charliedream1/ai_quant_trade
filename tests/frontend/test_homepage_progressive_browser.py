"""Full homepage content survives initialization, explicit refresh and cached return."""

import json
from time import monotonic

from playwright.sync_api import expect, sync_playwright

from tests.frontend.home_fixtures import seed_home_account

PLOTS = ("home-trend", "home-allocation", "home-risk-radar", "home-sentiment", "home-sectors", "home-contribution")


def complete_home(frame):
    expect(frame.locator("#home-kpis .home-metric")).to_have_count(8, timeout=60000)
    for key in PLOTS:
        expect(frame.locator(f"#{key} .js-plotly-plot")).to_be_visible(timeout=60000)
    for key in (
        "home-risk",
        "home-market-summary",
        "home-actions",
        "dashboard-ai-workbench-entry",
        "home-themes",
        "home-news",
    ):
        expect(frame.locator(f"#{key}")).not_to_have_text("", timeout=60000)
    expect(frame.locator("#home-dashboard .section-loading")).to_have_count(0, timeout=15000)


def test_full_homepage_survives_initial_market_sync_refresh_and_return(cli_command, tmp_path):
    seed_home_account()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        try:
            began = monotonic()
            page.goto(cli_command.base_url + "/app/?module=dashboard&view=overview", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            complete_home(frame)
            first_complete = monotonic() - began
            # Automatic language/market synchronization must not reset completed sections.
            page.wait_for_timeout(1200)
            complete_home(frame)
            original = frame.locator("#home-data-status").inner_text()
            page.screenshot(path=str(tmp_path / "complete-home-before-refresh.png"), full_page=True)
            frame.locator("#home-refresh").click()
            expect(frame.locator("#home-data-status")).not_to_have_text(original, timeout=60000)
            complete_home(frame)
            page.locator('[data-workspace-module="market"]').click()
            expect(frame.locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]')).to_be_visible(timeout=60000)
            began = monotonic()
            page.locator('[data-workspace-module="dashboard"]').click()
            complete_home(frame)
            returned = monotonic() - began
            page.screenshot(path=str(tmp_path / "complete-home-after-return.png"), full_page=True)
            (tmp_path / "timings.json").write_text(
                json.dumps(
                    {
                        "cold_complete_seconds": first_complete,
                        "cached_return_seconds": returned,
                        "plots": len(PLOTS),
                        "metrics": 8,
                    }
                ),
                encoding="utf-8",
            )
        except Exception:
            page.screenshot(path=str(tmp_path / "failed-homepage.png"), full_page=True)
            if "frame" in locals():
                (tmp_path / "failed-kpis.html").write_text(frame.locator("#home-kpis").inner_html(), encoding="utf-8")
            raise
        finally:
            browser.close()
