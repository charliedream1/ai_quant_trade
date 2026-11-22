"""Generate and download a macro Skill report from its page without a prior data load."""

import json
import os

from playwright.sync_api import expect, sync_playwright

from src.core.timeutil import utc_now_iso


def _source(self, name, *, symbol="", refresh=False):
    definition = self.config["macro"][name]
    return {
        "rows": [
            {definition["date"]: stamp, definition["field"]: value}
            for stamp, value in (("2026-01-01", 1), ("2026-02-01", 2))
        ],
        "first_seen_at": utc_now_iso(),
        "checked_at": utc_now_iso(),
        "version": "fixture",
        "url": "https://example.com/macro",
        "source": "declared observations",
    }


def _macro_worker(connection):
    if os.name != "nt":
        os.setsid()
    from src.data.economics import EconomicDataSource
    from src.frontend.read_worker import invoke, transferable

    EconomicDataSource.fetch = _source
    while True:
        try:
            request = connection.recv()
        except EOFError:
            return
        if request is None:
            return
        connection.send(invoke(request, lambda index, data: connection.send(("panel", index, transferable(data)))))


def test_macro_report_uses_inline_launcher_and_bounded_snapshot(cli_command, monkeypatch, tmp_path):
    from src.engine.insights import execution
    from src.frontend import page_reads
    from src.frontend.common import composer_catalog
    from src.frontend.features import page_analysis

    monkeypatch.setattr(page_analysis, "capability", lambda *args: {})
    monkeypatch.setattr(execution, "validate_backend", lambda *args: {})
    monkeypatch.setattr(composer_catalog, "discover", lambda *args: {"status": "ready", "rows": []})

    def generate(prompt, payload, cfg, emit):
        assert "recent_observations_by_series" in prompt
        assert "example.com/macro" in prompt
        return json.dumps(
            {
                "title": "Declared macro report",
                "summary": "Observed changes in the loaded series.",
                "sections": [
                    {"heading": name, "paragraphs": ["The current observation rose."], "source_ids": ["E1"]}
                    for name in cfg["tasks"]["page_analysis"]["sections"]
                ],
                "risks": [],
                "missing": [],
            }
        )

    monkeypatch.setattr(execution, "generate_text", generate)
    page_reads.shutdown()
    monkeypatch.setattr(page_reads, "serve", _macro_worker)
    page_reads.start()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            page.goto(cli_command.base_url + "/app/?module=market&view=macro", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            launcher = frame.locator(".page-report-action").filter(visible=True)
            expect(launcher).to_have_count(1, timeout=90000)
            launcher.click()
            frame.locator("#page-skill-run").click()
            report = frame.frame_locator("#page-skill-preview iframe")
            expect(report.get_by_role("heading", name="Declared macro report")).to_be_visible(timeout=45000)
            anchor = frame.locator("#page-skill-download a").first
            uri = anchor.evaluate("node => node.href")
            assert b"Declared macro report" in page.request.get(uri).body()
            page.screenshot(path=str(tmp_path / "macro-report.png"), full_page=True)
        finally:
            browser.close()
