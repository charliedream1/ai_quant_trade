"""Actual Gradio navigation cancels blocked reads without dropping drafts or other windows."""

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from time import monotonic

import pytest
from filelock import FileLock
from playwright.sync_api import expect, sync_playwright

from src.core.config import get_settings
from src.frontend import page_reads
from tests.frontend.page_worker_fixture import serve
from tests.frontend.test_page_lifetimes import wait_for


@pytest.fixture
def stalled_source():
    accepted, closed = Event(), Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", "1000000")
            self.end_headers()
            accepted.set()
            try:
                while not closed.wait(0.05):
                    self.wfile.write(b"blocking source\n")
                    self.wfile.flush()
            except (ConnectionError, OSError):
                closed.set()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/slow", accepted, closed
    finally:
        closed.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_two_window_navigation_cancels_last_read(cli_command, monkeypatch, tmp_path, stalled_source, caplog):
    page_reads.shutdown()
    monkeypatch.setattr(page_reads, "serve", serve)
    page_reads.start()
    folder = get_settings().data_dir
    marker = folder / "worker-started.json"
    endpoint, accepted, closed = stalled_source
    (folder / "slow-source-url.txt").write_text(endpoint, encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            first = browser.new_page(viewport={"width": 1500, "height": 1000})
            second = browser.new_page(viewport={"width": 1500, "height": 1000})
            url = cli_command.base_url + "/app/?module=market&view=fundamentals"
            for page in (first, second):
                page.goto(url, wait_until="domcontentloaded")
                frame = page.frame_locator("iframe.workspace-frame.active")
                expect(frame.locator("#fundamentals-symbol textarea")).to_have_value("600519", timeout=90000)
                frame.locator("#fundamentals-load").click()
            wait_for(marker.exists)
            assert accepted.wait(3)
            wait_for(lambda: any(len(job.consumers) == 2 for job in page_reads.JOBS.values()), 10)
            pid = json.loads(marker.read_text(encoding="utf-8"))["pid"]
            first_frame = first.frame_locator("iframe.workspace-frame.active")
            first_frame.locator("#fundamentals-symbol textarea").fill("600036")
            started = monotonic()
            first.locator('[data-workspace-view="analysis"]').click()
            first_frame.locator("#market-analysis-tabs").get_by_role(
                "tab", name=re.compile("行情与板块|Quotes and Sectors")
            ).click()
            expect(first_frame.locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]')).to_be_visible(timeout=3000)
            switch_seconds = monotonic() - started
            assert switch_seconds < 3
            wait_for(lambda: any(len(job.consumers) == 1 for job in page_reads.JOBS.values()), 3)
            assert page_reads.BUSY
            assert not closed.is_set()
            second.locator('[data-workspace-view="analysis"]').click()
            second.frame_locator("iframe.workspace-frame.active").locator("#market-analysis-tabs").get_by_role(
                "tab", name=re.compile("行情与板块|Quotes and Sectors")
            ).click()
            wait_for(lambda: not page_reads.BUSY, 8)
            assert closed.wait(3), "Cancelling the last consumer must close its actual source connection"
            with FileLock(str(folder / "source.lock"), timeout=0.1):
                pass
            first.locator('[data-workspace-view="stock"]').click()
            expect(first_frame.locator("#fundamentals-symbol textarea")).to_have_value("600036")
            expect(first_frame.locator("#fundamentals-status")).not_to_contain_text("快照")
            first.screenshot(path=str(tmp_path / "cancelled-load-draft-retained.png"))
            (tmp_path / "navigation-result.json").write_text(
                json.dumps({"worker_pid": pid, "switch_seconds": switch_seconds, "two_windows": True}), encoding="utf-8"
            )
            # A cold module remains reachable after cancellation; returning uses the cached frame.
            first.locator('[data-workspace-module="learning"]').click()
            expect(first.locator('iframe.workspace-frame.active[data-module-key="learning"]')).to_be_visible(
                timeout=3000
            )
            expect(first.frame_locator("iframe.workspace-frame.active").locator(".course-layout")).to_be_visible(
                timeout=60000
            )
            first.go_back()
            expect(first_frame.locator("#fundamentals-symbol textarea")).to_have_value("600036", timeout=10000)
        finally:
            browser.close()
    assert "async generator ignored GeneratorExit" not in caplog.text


def test_cold_module_build_releases_queue_on_navigation(cli_command, monkeypatch, tmp_path):
    from src.frontend import modular
    from src.frontend.service_dispatch import CallbackServices

    page_reads.shutdown()
    monkeypatch.setattr(page_reads, "serve", serve)
    page_reads.start()
    original = modular.render_ai

    def blocked_build(*args, **kwargs):
        CallbackServices().stock("SLOW")
        return original(*args, **kwargs)

    monkeypatch.setattr(modular, "render_ai", blocked_build)
    folder = get_settings().data_dir
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1000})
            page.goto(cli_command.base_url + "/app/?module=ai&view=workbench", wait_until="domcontentloaded")
            wait_for((folder / "worker-started.json").exists, 60)
            began = monotonic()
            page.locator('[data-workspace-module="market"]').click()
            expect(page.locator('iframe.workspace-frame.active[data-module-key="market"]')).to_be_visible(timeout=3000)
            expect(page.frame_locator("iframe.workspace-frame.active").locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]')).to_be_visible(
                timeout=20000
            )
            wait_for(lambda: not page_reads.BUSY, 8)
            with FileLock(str(folder / "source.lock"), timeout=0.1):
                pass
            (tmp_path / "cold-module-result.json").write_text(
                json.dumps({"destination_ready_seconds": monotonic() - began}), encoding="utf-8"
            )
        finally:
            from src.core import page_work

            page_work.shutdown()
            browser.close()


def test_preview_draft_survives_view_navigation(client, cli_command, tmp_path):
    original = b"# Original preview\n\nRetained source.\n"
    uploaded = client.post("/api/v1/file-previews/uploads", files={"file": ("draft.md", original)}).json()["data"]
    url = f"/api/v1/file-previews/{uploaded['id']}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1000})
            page.goto(cli_command.base_url + "/app/?module=market&view=fundamentals", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#fundamentals-load")).to_be_visible(timeout=90000)
            frame.locator("body").evaluate(
                "(body, url) => { const link = document.createElement('a'); link.href = url; body.append(link); link.click(); }",
                url + "/view",
            )
            reader = frame.frame_locator(".file-reader-panel iframe")
            expect(reader.locator("#file-title")).to_have_text("draft.md", timeout=15000)
            reader.locator("#edit-file").click()
            reader.locator("#markdown-editor").fill("# Unsaved draft retained")
            page.locator('[data-workspace-view="analysis"]').click()
            frame.locator("#market-analysis-tabs").get_by_role(
                "tab", name=re.compile("行情与板块|Quotes and Sectors")
            ).click()
            expect(frame.locator(".file-reader-panel")).to_be_hidden()
            expect(frame.locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]')).to_be_visible()
            page.locator('[data-workspace-view="stock"]').click()
            expect(frame.locator(".file-reader-panel")).to_be_visible()
            expect(reader.locator("#markdown-editor")).to_have_value("# Unsaved draft retained")
            assert client.get(url + "/raw").content == original
            page.screenshot(path=str(tmp_path / "preview-draft-retained.png"))
        finally:
            browser.close()
