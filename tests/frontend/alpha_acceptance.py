"""Visible clicks audit new alpha navigation, real process events and negative gates."""

import argparse
import json
import re
from pathlib import Path
from threading import Event
from time import perf_counter

import requests
import yaml
from loguru import logger
from playwright.sync_api import expect, sync_playwright
from workspace_revision_acceptance import active, navigate


def configuration(frame, overrides):
    accordion = frame.get_by_text("高级配置：政策、模型分工、八配置及资产映射", exact=True)
    if not frame.locator("#alpha-advanced .cm-content").is_visible():
        accordion.click()
    frame.locator("#alpha-advanced .cm-content").fill(yaml.safe_dump(overrides, allow_unicode=True))


def choose(frame, selector, text):
    frame.locator(selector + " input").click()
    frame.get_by_role("option").filter(has_text=text).first.click()


def main(base, runtime, output):
    output.mkdir(parents=True, exist_ok=True)
    deadline = perf_counter() + 60
    while True:
        try:
            if requests.get(base + "/api/v1/health", timeout=5).status_code == 200:
                break
        except requests.RequestException:
            pass
        assert perf_counter() < deadline, "Browser test service not ready"
        Event().wait(0.2)
    fixture = yaml.safe_load(Path("tests/alpha_mining/fixtures/workflows.yaml").read_text(encoding="utf-8"))
    results, errors = {}, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1050})
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(base + "/app/?module=strategy&view=alpha")
            frame = active(page)
            expect(frame.locator("#alpha-name textarea")).to_be_visible(timeout=90000)
            frame.get_by_text("数据与来源（先导入或选择已核验归档）", exact=True).click()
            choose(frame, "#alpha-dataset", "market")
            choose(frame, "#alpha-model", "协议测试替身")
            frame.locator("#alpha-name textarea").fill("浏览器Alpha流程验收（协议替身）")
            configuration(frame, {"policy": fixture["policy"], "batch_size": 1})
            frame.locator("#alpha-create").click()
            expect(frame.locator("#alpha-status")).to_contain_text(re.compile("已登记|草稿"), timeout=30000)
            started = perf_counter()
            frame.locator("#alpha-run").click()
            expect(frame.locator("#alpha-status")).to_contain_text("待冻结候选", timeout=60000)
            results["discovery_seconds"] = round(perf_counter() - started, 3)
            expect(frame.locator("#alpha-process textarea")).to_have_value(
                re.compile("explicit-unit-test-double"), timeout=15000
            )
            page.screenshot(path=str(output / "01-alpha-discovery.jpg"), type="jpeg", quality=88)
            frame.locator("#alpha-stage").get_by_text("实现", exact=True).click()
            expect(frame.locator("#alpha-inspection")).to_contain_text("expression", timeout=15000)
            page.screenshot(path=str(output / "02-alpha-implementation.jpg"), type="jpeg", quality=88)
            frame.locator("#alpha-seal").click()
            expect(frame.locator("#alpha-status")).to_contain_text("候选已冻结", timeout=30000)
            started = perf_counter()
            frame.locator("#alpha-validate").click()
            expect(frame.locator("#alpha-status")).to_contain_text("验证结束", timeout=90000)
            results["validation_seconds"] = round(perf_counter() - started, 3)
            frame.locator("#alpha-stage").get_by_text("验证", exact=True).click()
            expect(frame.locator("#alpha-inspection")).to_contain_text("family_tests", timeout=20000)
            page.screenshot(path=str(output / "03-alpha-validation.jpg"), type="jpeg", quality=88)
            expect(
                frame.frame_locator("#alpha-report iframe").get_by_role("heading", name="冻结验证与全部候选")
            ).to_be_visible(timeout=30000)
            results["report_embedded"] = True
            frame.locator("#alpha-holdout").click()
            expect(frame.get_by_text("只有冻结验证通过的候选可以一次性使用留出", exact=False)).to_be_visible(
                timeout=15000
            )
            results["hard_gate_blocks_holdout"] = True
            frame.locator("#alpha-mode").scroll_into_view_if_needed()
            choose(frame, "#alpha-mode", "主题精炼")
            choose(frame, "#alpha-dataset", "documents")
            frame.locator("#alpha-name textarea").fill("浏览器主题关联验收（协议替身）")
            configuration(
                frame, {"policy": fixture["policy"], "theme": "云计算", "cutoff": "2019-05-01T00:00:00+00:00"}
            )
            frame.locator("#alpha-create").click()
            expect(frame.locator("#alpha-status")).to_contain_text(re.compile("已登记|草稿"), timeout=30000)
            frame.locator("#alpha-run").click()
            expect(frame.locator("#alpha-status")).to_contain_text("已完成", timeout=60000)
            expect(
                frame.frame_locator("#alpha-report iframe").get_by_role("heading", name="主题关联，非收益预测")
            ).to_be_visible(timeout=30000)
            page.screenshot(path=str(output / "04-alpha-theme.jpg"), type="jpeg", quality=88)
            results["theme_quote_and_report"] = True
            choose(frame, "#alpha-mode", "体制配置")
            choose(frame, "#alpha-dataset", "macro")
            frame.locator("#alpha-name textarea").fill("浏览器体制分类验收（协议替身）")
            configuration(
                frame,
                {
                    "policy": fixture["policy"],
                    "cutoff": "2019-05-01T00:00:00+00:00",
                    "asset_mapping": {"equity": "AAA", "bond": "BBB"},
                },
            )
            frame.locator("#alpha-create").click()
            expect(frame.locator("#alpha-status")).to_contain_text(re.compile("已登记|草稿"), timeout=30000)
            frame.locator("#alpha-run").click()
            expect(frame.locator("#alpha-status")).to_contain_text("已完成", timeout=60000)
            expect(frame.frame_locator("#alpha-report iframe").get_by_text("Goldilocks", exact=True)).to_be_visible(
                timeout=30000
            )
            page.screenshot(path=str(output / "05-alpha-regime.jpg"), type="jpeg", quality=88)
            results["regime_actual_events"] = True
            navigate(page, "ai", "workflow")
            expect(active(page).get_by_role("link", name="Alpha挖掘、主题精炼与体制实验")).to_be_visible(timeout=60000)
            active(page).get_by_role("link", name="Alpha挖掘、主题精炼与体制实验").click()
            expect(active(page).locator("#alpha-name textarea")).to_be_visible(timeout=60000)
            results["ai_navigation_preserved"] = True
            navigate(page, "knowledge", "reports")
            expect(active(page).locator("#report-selected")).to_be_visible(timeout=60000)
            choose(active(page), "#report-source", "Alpha研究")
            expect(active(page).get_by_text("浏览器体制分类验收", exact=False).first).to_be_visible(timeout=30000)
            page.screenshot(path=str(output / "06-alpha-report-library.jpg"), type="jpeg", quality=88)
            results["report_library"] = True
            assert not errors, errors
        finally:
            results["page_errors"] = errors
            results["model_scope"] = "explicit_protocol_test_double_not_real_llm_acceptance"
            (output / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            page.screenshot(path=str(output / "last.jpg"), type="jpeg", quality=88)
            browser.close()
    logger.info("Alpha browser acceptance: {}", results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base_url, args.runtime, args.output)
