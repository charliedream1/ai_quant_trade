"""Measure unloaded reader cost and verify the ordinary PDF entry against live HTTP."""

import argparse
import json
from pathlib import Path
from statistics import median
from threading import Event
from time import perf_counter

import requests
from loguru import logger
from playwright.sync_api import expect, sync_playwright


def main(base, sample, output):
    output.mkdir(parents=True, exist_ok=True)
    deadline = perf_counter() + 60
    while True:
        try:
            if requests.get(base + "/api/v1/health", timeout=5).status_code == 200:
                break
        except requests.RequestException:
            pass
        assert perf_counter() < deadline
        Event().wait(0.2)
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        urls, errors = [], []
        page.on("request", lambda request: urls.append(request.url))
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base + "/app/?module=ai&view=main")
        expect(page.frame_locator("iframe.workspace-frame.active").locator("#ai-console-input textarea")).to_be_visible(
            timeout=90000
        )
        assert not any("/vendor/pdfjs/" in url for url in urls)
        results["pdf_assets_loaded_before_open"] = 0
        for module in ("ai", "knowledge", "strategy"):
            times = []
            for _ in range(3):
                started = perf_counter()
                response = requests.get(base + f"/app/{module}/config", timeout=90)
                response.raise_for_status()
                times.append((perf_counter() - started) * 1000)
            config = response.json()
            results[module] = {
                "components": len(config["components"]),
                "serialized_chars": len(json.dumps(config, ensure_ascii=False)),
                "warm_ms": times,
                "median_ms": median(times),
            }
        row = requests.post(
            base + "/api/v1/file-previews/uploads", files={"file": (sample.name, sample.read_bytes())}, timeout=30
        ).json()["data"]
        started = perf_counter()
        state = requests.post(base + f"/api/v1/file-previews/{row['id']}/conversion", timeout=30).json()["data"]
        assert state["status"] == "completed" and state["cached"], state
        results["cached_office_lookup_ms"] = (perf_counter() - started) * 1000
        pdf = requests.get(base + f"/api/v1/file-previews/{row['id']}/pdf", timeout=30).content
        (output / "reading.pdf").write_bytes(pdf)
        pdf_row = requests.post(
            base + "/api/v1/file-previews/uploads", files={"file": ("reading.pdf", pdf)}, timeout=30
        ).json()["data"]
        page.goto(base + pdf_row["url"])
        expect(page.locator("#pdf-canvas")).to_be_visible(timeout=30000)
        page.locator("#pdf-search").fill("第二页")
        page.locator("#search-pdf").click()
        expect(page.locator("#search-result")).to_contain_text("第 2 页匹配", timeout=30000)
        expect(page.locator("#edit-file")).to_be_hidden()
        page.screenshot(path=str(output / "09-native-pdf.jpg"), type="jpeg", quality=88)
        results["native_pdf"] = {"readonly": True, "chinese_phrase_search": True}
        results["page_errors"] = errors
        assert not errors, errors
        browser.close()
    (output / "metrics.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Reader metrics and native PDF passed: {}", results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base_url, args.sample, args.output)
