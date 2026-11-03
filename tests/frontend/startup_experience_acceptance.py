"""Actual visible operations for startup / attachment / navigation / report improvements."""

import argparse
import json
import re
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import requests
from loguru import logger
from playwright.sync_api import expect, sync_playwright
from workspace_revision_acceptance import active, navigate

from src.engine.insights.store import InsightStore
from src.engine.market.report_generator import MarketReportGenerator
from src.strategy.composition.config import template


def post(base, path, payload):
    result = requests.post(base + "/api/v1" + path, json=payload, timeout=60).json()
    assert result["code"] == 0, result
    return result["data"]


def seed_report(title, status="partial", html=False):
    store, key = InsightStore(), uuid4().hex
    store.save(
        {
            "run_id": key,
            "status": status,
            "request": {"kind": "market_review"},
            "title": title,
            "created_at": "2026-10-26T03:00:00Z",
        }
    )
    if html:
        store.append(key, "fixture", "隔离验收样本：未调用模型，验证历史报告展示")
        (store.directory(key) / "report.html").write_text(
            "<!doctype html><html lang='zh'><meta charset='utf-8'><body style='font:18px sans-serif;padding:32px'>"
            "<h1>隔离验收报告</h1><p>这是一份明确标注的展示样本，不表示执行过真实投研。</p></body></html>",
            encoding="utf-8",
        )
    return "skill:" + key


def screenshot(page, output, name):
    page.screenshot(path=str(output / (name + ".jpg")), type="jpeg", quality=88)


def main(base, output):
    output.mkdir(parents=True, exist_ok=True)
    suffix = uuid4().hex[:6]
    report_title, missing_title, late_title = (
        f"{title}-{suffix}" for title in ("验收样本：市场复盘", "验收样本：缺失文件", "稍后加入：显式刷新才出现")
    )
    report_key = seed_report(report_title, html=True)
    missing_key = seed_report(missing_title)
    MarketReportGenerator().create({"topic": "验收样本：旧模板", "use_llm": False})
    definition = template("rule_trend")
    definition["name"] += "-navigation-" + uuid4().hex[:8]
    draft = post(base, "/strategy-pipelines", {"definition": definition})
    version = post(base, f"/strategy-pipelines/{draft['id']}/publish", {})
    results, errors = {}, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
        page = context.new_page()
        try:
            page.goto(base + "/app/?module=strategy&view=etf")
            expect(active(page).get_by_label("ETF池", exact=True).filter(visible=True)).to_be_visible(timeout=90000)
            with context.expect_page() as popup:
                page.locator("#workspace-open-standalone").click()
            standalone = popup.value
            expect(standalone.get_by_label("ETF池", exact=True).filter(visible=True)).to_be_visible(timeout=90000)
            assert "view=etf" in standalone.url
            screenshot(standalone, output, "01-standalone-etf")
            standalone.close()
            results["standalone_etf"] = True

            page.goto(base + f"/app/?module=strategy&view=workshop&pipeline_version={version['id']}")
            expect(active(page).locator("#pipeline-route-version textarea")).to_have_value(
                str(version["id"]), timeout=90000
            )
            with context.expect_page() as popup:
                page.locator("#workspace-open-standalone").click()
            standalone = popup.value
            expect(standalone.locator("#pipeline-route-version textarea")).to_have_value(
                str(version["id"]), timeout=90000
            )
            expect(standalone.locator(".strategy-graph-app")).to_be_visible(timeout=90000)
            screenshot(standalone, output, "02-standalone-frozen-graph")
            standalone.close()
            navigate(page, "strategy", "etf")
            assert "pipeline_version" not in page.url
            page.go_back()
            expect(page.locator("[data-workspace-view='workshop']")).to_have_class(re.compile("active"))
            assert f"pipeline_version={version['id']}" in page.url
            page.go_forward()
            assert "view=etf" in page.url and "pipeline_version" not in page.url
            results["frozen_and_history"] = {"version": version["id"], "isolated_from_etf": True}

            page.goto(base + "/app/?module=knowledge&view=reports")
            frame = active(page)
            expect(frame.get_by_text(report_title, exact=True).first).to_be_visible(timeout=90000)
            selected = frame.locator("#report-selected input")
            selected.click()
            frame.get_by_role("option", name=re.compile(re.escape(report_key))).click()
            frame.get_by_role("button", name="打开报告", exact=True).click()
            expect(frame.get_by_label("实际过程或来源说明", exact=True)).to_have_value(
                re.compile("fixture"), timeout=30000
            )
            frame.locator("#report-keyword textarea").fill(report_title)
            expect(frame.get_by_text(missing_title, exact=True)).to_have_count(0, timeout=15000)
            frame.locator("#report-source").scroll_into_view_if_needed()
            screenshot(page, output, "03-report-library")
            before = selected.input_value()
            frame.get_by_role("button", name="刷新报告库", exact=True).click()
            expect(selected).to_have_value(before)
            frame.locator("#report-keyword textarea").fill(report_title)
            expect(frame.get_by_text(missing_title, exact=True)).to_have_count(0, timeout=15000)
            expect(selected).to_have_value(before)
            frame.locator("#report-keyword textarea").fill("")
            expect(frame.get_by_text(missing_title, exact=True).first).to_be_visible(timeout=15000)
            selected.click()
            frame.get_by_role("option", name=re.compile(re.escape(missing_key))).click()
            frame.get_by_role("button", name="打开报告", exact=True).click()
            expect(frame.get_by_text("HTML文件缺失或不可读取", exact=False).first).to_be_visible(timeout=15000)
            screenshot(page, output, "04-report-missing-artifact")
            late_key = seed_report(late_title)
            started = perf_counter()
            navigate(page, "knowledge", "library")
            frame = navigate(page, "knowledge", "reports")
            expect(frame.get_by_text(late_title, exact=True)).to_have_count(0)
            results["report_revisit_seconds"] = perf_counter() - started
            frame.get_by_role("button", name="刷新报告库", exact=True).click()
            expect(frame.get_by_text(late_title, exact=True).first).to_be_visible(timeout=15000)
            results["report_library"] = {
                "report": report_key,
                "missing": missing_key,
                "late": late_key,
                "selection_retained": True,
            }

            frame = navigate(page, "ai", "main")
            composer = frame.locator("#ai-console-composer")
            expect(composer.locator("textarea").first).to_be_visible(timeout=90000)
            with page.expect_file_chooser() as chooser:
                composer.locator(".composer-attach").click()
            chooser.value.set_files(
                {"name": "伪图片.jpg", "mimeType": "image/jpeg", "buffer": b"plain text renamed jpg"}
            )
            expect(composer).to_contain_text(re.compile(r"伪图片\s*\.jpg"), timeout=30000)
            message = frame.locator("#ai-console-input textarea")
            message.fill("分析附件（隔离验收）")
            message.press("Enter")
            expect(frame.get_by_text("校验失败", exact=False).filter(visible=True).first).to_be_visible(timeout=30000)
            expect(message).to_have_value("分析附件（隔离验收）")
            expect(composer).to_contain_text(re.compile(r"伪图片\s*\.jpg"))
            screenshot(page, output, "05-invalid-image-rejected")
            results["invalid_image_ui"] = True
            results["page_errors"] = errors
            assert not errors, errors
        finally:
            results["page_errors"] = errors
            (output / "browser-results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            screenshot(page, output, "browser-last")
            browser.close()
    logger.info("Startup experience browser acceptance passed: {}", results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base_url, args.output)
