"""Measure a fresh launcher, initial panel completion and repeat navigation separately."""

import argparse
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from time import monotonic, sleep

import requests
from loguru import logger
from playwright.sync_api import expect, sync_playwright

from src.core.process_control import stop_process_tree

ROOT = Path(__file__).resolve().parents[2]


def inspect(base, output):
    results = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            start = monotonic()
            page.goto(base + "/app/?module=dashboard&view=overview", wait_until="domcontentloaded")
            expect(page.locator('[data-workspace-module="market"]')).to_be_visible(timeout=90000)
            results["cold_shell_seconds"] = round(monotonic() - start, 3)
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#home-refresh")).to_be_visible(timeout=90000)
            results["cold_home_controls_seconds"] = round(monotonic() - start, 3)
            expect(frame.locator("#home-data-status")).not_to_contain_text("正在读取", timeout=90000)
            results["cold_account_complete_seconds"] = round(monotonic() - start, 3)
            expect(frame.locator("#home-sectors .js-plotly-plot")).to_be_visible(timeout=90000)
            results["cold_market_complete_seconds"] = round(monotonic() - start, 3)
            expect(frame.locator("#home-news article").first).to_be_visible(timeout=90000)
            results["cold_news_complete_seconds"] = round(monotonic() - start, 3)
            page.screenshot(path=str(output / "cold-home.png"))
            start = monotonic()
            page.locator('[data-workspace-module="market"]').click()
            expect(frame.locator("#market-quotes-refresh")).to_be_visible(timeout=90000)
            results["cold_market_module_seconds"] = round(monotonic() - start, 3)
            start = monotonic()
            page.locator('[data-workspace-module="dashboard"]').click()
            expect(frame.locator("#home-refresh")).to_be_visible(timeout=15000)
            expect(frame.locator("#home-sectors .js-plotly-plot")).to_be_visible(timeout=15000)
            results["cached_home_return_seconds"] = round(monotonic() - start, 3)
            page.screenshot(path=str(output / "cached-home.png"))
        finally:
            browser.close()
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interpreter", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["mock", "real"], default="mock")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    environment = {
        **os.environ,
        "ALL_IN_ONE_DATA_DIR": str(output / "data"),
        "ALL_IN_ONE_DB_PATH": str(output / "data/app.db"),
        "ALL_IN_ONE_DATA_MODE": args.mode,
        "ALL_IN_ONE_RUNTIME_MODE": "non-strict",
        "ALL_IN_ONE_ACCESS_MODE": "local",
        "ALL_IN_ONE_HELP_DOCS_AUTO_BUILD": "false",
        "ALL_IN_ONE_CHANNELS_ENABLED": "false",
        "ALL_IN_ONE_LANGFUSE_ENABLED": "false",
        "ALL_IN_ONE_LOG_FILE_LEVEL": "DEBUG",
        "GRADIO_TEMP_DIR": str(output / "uploads"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
    }
    report = {"mode": args.mode}
    with (output / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [args.interpreter, "-B", "start.py", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=environment,
            stdout=log,
            stderr=log,
            start_new_session=sys.platform != "win32",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            start = monotonic()
            while monotonic() - start < 90:
                if process.poll() is not None:
                    raise RuntimeError("Owned launcher exited")
                try:
                    if requests.get(base + "/api/v1/health", timeout=2).ok:
                        break
                except requests.RequestException:
                    pass
                sleep(0.2)
            report["startup_health_seconds"] = round(monotonic() - start, 3)
            report.update(inspect(base, output))
            report["status"] = "passed"
        except Exception as exc:
            report.update(status="failed", error=type(exc).__name__, detail=str(exc))
        finally:
            if process.poll() is None:
                stop_process_tree(process)
                process.wait(timeout=10)
            with socket.socket() as probe:
                report["port_released"] = probe.connect_ex(("127.0.0.1", port)) != 0
            (output / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Load acceptance: {}", report)
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
