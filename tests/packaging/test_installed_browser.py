"""Launch an installed server and interact with its real lazy page workers."""

import os
import socket
import subprocess
import time

import pytest
import requests
from playwright.sync_api import expect, sync_playwright

from src.core.process_control import stop_process_tree

PYTHON = os.environ.get("AIQUANT_TEST_INSTALLED_PYTHON")
pytestmark = pytest.mark.skipif(not PYTHON, reason="Requires a disposable installed-wheel interpreter")


def test_installed_server_rule_page_and_assets(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = {
        **os.environ,
        "ALL_IN_ONE_DATA_MODE": "mock",
        "ALL_IN_ONE_HELP_DOCS_AUTO_BUILD": "false",
        "PYTHONDONTWRITEBYTECODE": "1",
        "ALL_IN_ONE_RUNTIME_MODE": "non-strict",
    }
    environment.pop("PYTHONPATH", None)
    if os.environ.get("AIQUANT_TEST_INSTALLED_TARGET"):
        environment["PYTHONPATH"] = os.environ["AIQUANT_TEST_INSTALLED_TARGET"]
    environment.pop("ALL_IN_ONE_DATA_DIR", None)
    base = f"http://127.0.0.1:{port}"
    with (tmp_path / "server.log").open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [str(PYTHON), "-B", "-m", "src", "--workspace", str(tmp_path / "workspace"), "--port", str(port)],
            cwd=tmp_path,
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            start_new_session=os.name != "nt",
        )
        try:
            deadline = time.monotonic() + 90
            while True:
                assert process.poll() is None, (tmp_path / "server.log").read_text(encoding="utf-8")
                try:
                    if requests.get(base + "/api/v1/health", timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                assert time.monotonic() < deadline
                time.sleep(0.1)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page(viewport={"width": 1600, "height": 1100})
                    page.goto(base + "/app/?module=market&view=quotes", wait_until="domcontentloaded")
                    frame = page.frame_locator("iframe.workspace-frame.active")
                    expect(frame.locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]')).to_be_visible(timeout=90000)
                    frame.locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]').click()
                    expect(frame.locator("#market-sectors-plot .js-plotly-plot")).to_be_visible(timeout=60000)
                    page.screenshot(path=str(tmp_path / "installed-market.png"), full_page=True)
                finally:
                    browser.close()
        finally:
            stop_process_tree(process)
            process.wait(timeout=10)
    with socket.socket() as listener:
        listener.settimeout(1)
        assert listener.connect_ex(("127.0.0.1", port)) != 0
