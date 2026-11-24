"""Financial sections and bounded rule tasks remain usable in the browser."""

import json
from time import monotonic, sleep

from playwright.sync_api import expect, sync_playwright

from src.engine.market.rule_graph_jobs import RuleGraphJobs


def test_financial_defaults_sections_and_saved_rule_export(
    economic_sources, observations, cli_command, monkeypatch, tmp_path
):
    from src.core.config import get_settings
    from src.frontend import page_reads
    from tests.economics.source_worker_fixture import serve

    folder = get_settings().data_dir
    (folder / "economic-observations.json").write_text(json.dumps(observations), encoding="utf-8")
    page_reads.shutdown()
    monkeypatch.setattr(page_reads, "serve", serve)
    page_reads.start()
    service = RuleGraphJobs()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1000})
            page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
            page.goto(cli_command.base_url + "/app/?module=market&view=fundamentals", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            symbol = frame.locator("#fundamentals-symbol textarea")
            expect(symbol).to_have_value("600519", timeout=90000)
            frame.locator("#fundamentals-load").click()
            expect(frame.locator("#fundamentals-status")).to_contain_text("快照", timeout=30000)
            snapshots = (folder / "economics/snapshots").glob("*.json")
            assert any("explicit-test-fixture" in path.read_text(encoding="utf-8") for path in snapshots)
            cash_flow = frame.locator("#financial-analysis-sections").get_by_role("radio", name="现金流量表")
            cash_flow.check()
            expect(cash_flow).to_be_checked()
            expect(frame.get_by_text("经营现金流/合并净利润", exact=True).filter(visible=True).first).to_be_visible()
            page.screenshot(path=str(tmp_path / "financial-sections.png"))
            page.goto(cli_command.base_url + "/app/?module=market&view=relations", wait_until="domcontentloaded")
            expect(frame.locator("#rule-graph-start")).to_be_visible(timeout=30000)
            began = monotonic()
            frame.locator("#rule-graph-start").click()
            key = frame.locator("#rule-graph-run-id").locator("textarea,input").first
            expect(key).not_to_have_value("", timeout=10000)
            assert monotonic() - began < 5
            identifier = key.input_value()
            assert page.request.get(cli_command.base_url + "/api/v1/health", timeout=3000).ok
            deadline = monotonic() + 35
            while service.detail(identifier)["status"] in {"queued", "running"} and monotonic() < deadline:
                sleep(0.1)
            assert service.detail(identifier)["status"] == "completed"
            expect(frame.locator("#rule-graph-plot .js-plotly-plot")).to_be_visible(timeout=10000)
            page.screenshot(path=str(tmp_path / "rule-graph.png"))
            original = (service.store.directory(identifier) / "graph.json").read_bytes()
            frame.get_by_role("button", name="导出图谱JSON", exact=True).click()
            link = frame.locator("#rule-graph-download a[href*='graph.json']").filter(visible=True).first
            expect(link).to_be_visible(timeout=10000)
            file_url = link.evaluate("element => element.href")
            (tmp_path / "download-url.txt").write_text(file_url, encoding="utf-8")
            response = page.request.get(file_url)
            assert response.status == 200 and response.body() == original
            with page.expect_download() as pending:
                link.click()
            saved = tmp_path / "rule-download.json"
            pending.value.save_as(str(saved))
            assert saved.read_bytes() == original
            assert json.loads(original)["is_mock"]
            depth = frame.get_by_role("slider").filter(visible=True).first
            depth.focus()
            depth.press("End")
            frame.locator("#rule-graph-start").click()
            expect(key).not_to_have_value(identifier, timeout=10000)
            cancelled_id = key.input_value()
            frame.locator("#rule-graph-cancel").click()
            deadline = monotonic() + 10
            while service.detail(cancelled_id)["status"] in {"queued", "running"} and monotonic() < deadline:
                sleep(0.1)
            assert service.detail(cancelled_id)["status"] == "cancelled"
            expect(frame.locator("#rule-graph-plot .js-plotly-plot")).to_have_count(0, timeout=10000)
            expect(frame.locator("#rule-graph-download a[href*='graph.json']")).to_have_count(0)
            assert (service.store.directory(identifier) / "graph.json").read_bytes() == original
        finally:
            browser.close()
