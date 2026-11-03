"""Check dark/compact composers, fullscreen graph and a real CLI-generated Skill report."""

import argparse
import json
from pathlib import Path
from time import perf_counter

import requests
from playwright.sync_api import expect, sync_playwright
from workspace_revision_acceptance import active, navigate


def main(base, output, run_report):
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(base + "/app/?module=learning&view=course")
            frame = active(page)
            expect(frame.locator("#quant-course-content")).to_be_visible(timeout=90000)
            frame.locator("#ai-floating-button").click()
            send = frame.locator("#ai-chat-send")
            expect(send).to_be_in_viewport()
            expect(frame.locator("#ai-chat-composer-footer")).to_be_visible()
            results["floating_footer"] = send.bounding_box()
            page.screenshot(path=str(output / "10-floating-toolbar.jpg"), type="jpeg", quality=88)
            frame.locator("#ai-floating-close").click()
            frame = navigate(page, "ai", "main")
            expect(frame.locator("#ai-console-input textarea")).to_be_visible(timeout=90000)
            page.locator("#app-theme-toggle").click()
            expect(frame.locator("html")).to_have_attribute("data-theme", "dark")
            assert frame.locator("#ai-console-composer-footer").bounding_box()["height"] <= 48
            page.screenshot(path=str(output / "11-dark-composer.jpg"), type="jpeg", quality=88)
            page.locator("#app-theme-toggle").click()
            frame = navigate(page, "strategy", "workshop")
            expect(frame.locator("#strategy-graph-editor")).to_be_visible(timeout=90000)
            frame.get_by_role("button", name="全屏画布", exact=True).click()
            expect(frame.locator(".graph-canvas")).to_have_attribute("data-fit-pending", "false", timeout=30000)
            for _ in range(2):
                frame.locator(".svelte-flow__controls-zoomin").click()
            page.screenshot(path=str(output / "12-fullscreen-graph.jpg"), type="jpeg", quality=88)
            frame.get_by_role("button", name="退出全屏", exact=True).click()
            results["graph_fullscreen"] = True
            if run_report:
                frame = navigate(page, "ai", "insights")
                backend = frame.get_by_label("执行后端", exact=True)
                backend.click()
                frame.get_by_role("option", name="Codex CLI", exact=True).click()
                started = perf_counter()
                frame.get_by_role("button", name="Market Review · 市场复盘", exact=True).click()
                expect(frame.get_by_label("实际过程", exact=True).last).not_to_have_value("", timeout=30000)
                preview = frame.locator("iframe[title]")
                expect(preview).to_be_visible(timeout=300000)
                results["skill_report"] = {
                    "seconds": round(perf_counter() - started, 3),
                    "status": frame.get_by_label("运行状态", exact=True).input_value(),
                    "process": frame.get_by_label("实际过程", exact=True).last.input_value(),
                }
                page.screenshot(path=str(output / "13-real-skill-report.jpg"), type="jpeg", quality=88)
            config = requests.get(base + "/app/ai/config", timeout=30).json()
            results["ai_config"] = {
                "components": len(config["components"]),
                "characters": len(json.dumps(config, ensure_ascii=False)),
            }
        finally:
            (output / "visual-results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            page.screenshot(path=str(output / "visual-last.jpg"), type="jpeg", quality=88)
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-report", action="store_true")
    args = parser.parse_args()
    main(args.base_url, args.output, args.run_report)
