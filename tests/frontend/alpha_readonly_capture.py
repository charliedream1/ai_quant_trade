"""Capture real-model evidence through normal read-only page actions; no new LLM calls."""

import argparse
import json
from pathlib import Path

import requests
from loguru import logger
from playwright.sync_api import expect, sync_playwright
from workspace_revision_acceptance import active, navigate


def choose(frame, selector, text):
    frame.locator(selector + " input").click()
    frame.get_by_role("option").filter(has_text=text).first.click()


def scroll_shot(page, locator, output, name):
    locator.evaluate("element => element.scrollIntoView({block:'start'})")
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(250)
    page.screenshot(path=str(output / (name + ".jpg")), type="jpeg", quality=88)


def main(base, output):
    output.mkdir(parents=True, exist_ok=True)
    before = requests.get(base + "/api/v1/alpha/studies").json()["data"]["items"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base + "/app/?module=strategy&view=alpha")
        frame = active(page)
        expect(frame.locator("#alpha-study input")).to_be_visible(timeout=90000)
        choose(frame, "#alpha-study", "#1 ·")
        expect(frame.locator("#alpha-status")).to_contain_text("通过候选0个", timeout=30000)
        scroll_shot(page, frame.locator("#alpha-study"), output, "74-alpha-main")
        frame.get_by_text("新建研究与统一政策", exact=True).click()
        frame.locator("#alpha-stage").get_by_text("实现", exact=True).click()
        expect(frame.locator("#alpha-inspection")).to_contain_text("expression", timeout=30000)
        scroll_shot(page, frame.locator("#alpha-inspection"), output, "75-alpha-evidence")
        choose(frame, "#alpha-study", "#2 ·")
        expect(frame.locator("#alpha-status")).to_contain_text("已完成", timeout=30000)
        expect(
            frame.frame_locator("#alpha-report iframe").get_by_role("heading", name="主题关联，非收益预测")
        ).to_be_visible(timeout=30000)
        scroll_shot(page, frame.locator("#alpha-report"), output, "76-alpha-theme")
        choose(frame, "#alpha-study", "#5 ·")
        expect(frame.locator("#alpha-status")).to_contain_text("模型错误1项", timeout=30000)
        frame.locator("#alpha-stage").get_by_text("验证", exact=True).click()
        expect(frame.locator("#alpha-inspection")).to_contain_text("不一致", timeout=30000)
        scroll_shot(page, frame.locator("#alpha-inspection"), output, "77-alpha-regime")
        navigate(page, "knowledge", "reports")
        expect(active(page).locator("#report-source input")).to_be_visible(timeout=60000)
        choose(active(page), "#report-source", "Alpha研究")
        expect(active(page).get_by_text("真实PIT体制单配置验收", exact=False).filter(visible=True).first).to_be_visible(
            timeout=30000
        )
        scroll_shot(page, active(page).locator("#report-source"), output, "78-alpha-library")
        after = requests.get(base + "/api/v1/alpha/studies").json()["data"]["items"]
        assert before == after and not errors
        browser.close()
    (output / "capture-checks.json").write_text(
        json.dumps(
            {"study_count_unchanged": True, "read_only": True, "new_model_calls": 0, "page_errors": errors}, indent=2
        ),
        encoding="utf-8",
    )
    logger.info("Real report screenshots captured without starting new studies or model calls")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base_url, args.output)
