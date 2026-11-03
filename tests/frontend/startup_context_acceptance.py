"""Visible task/account location and valid image delivery through both composers."""

import argparse
import io
import json
import re
from pathlib import Path
from uuid import uuid4

from loguru import logger
from PIL import Image
from playwright.sync_api import expect, sync_playwright
from startup_experience_acceptance import post
from workspace_revision_acceptance import active, navigate


def task_and_account(page, base, costs, output):
    task = costs["quick"]["id"]
    account = post(base, "/paper-accounts", {"name": "定位验收账户-" + uuid4().hex[:6], "initial_capital": 100000})[
        "account_id"
    ]
    page.goto(base + f"/app/?module=simulation&view=backtest&task_id={task}")
    frame = active(page)
    expect(frame.locator("#route-backtest-task-id input")).to_have_value(str(task), timeout=90000)
    expect(frame.get_by_text("实际执行成本", exact=True).filter(visible=True)).to_be_visible(timeout=60000)
    with page.context.expect_page() as pending:
        page.locator("#workspace-open-standalone").click()
    popup = pending.value
    expect(popup.locator("#route-backtest-task-id input")).to_have_value(str(task), timeout=90000)
    popup.close()
    page.goto(base + f"/app/?module=simulation&view=backtest&tab=模拟交易&account_id={account}")
    frame = active(page)
    field = frame.locator("#route-paper-account-id input")
    expect(field).to_have_value(str(account), timeout=90000)
    expect(field).to_be_visible()
    frame.get_by_role("button", name="刷新账户", exact=True).click()
    overview = frame.get_by_text("账户概览", exact=True).locator("xpath=ancestor::div[contains(@class,'block')][1]")
    expect(overview).to_contain_text("100000", timeout=30000)
    with page.context.expect_page() as pending:
        page.locator("#workspace-open-standalone").click()
    popup = pending.value
    expect(popup.locator("#route-paper-account-id input")).to_have_value(str(account), timeout=90000)
    expect(popup.locator("#route-paper-account-id input")).to_be_visible()
    popup.screenshot(path=str(output / "06-standalone-account.jpg"), type="jpeg", quality=88)
    popup.close()
    navigate(page, "strategy", "etf")
    assert "account_id" not in page.url and "task_id" not in page.url and "tab=" not in page.url
    return {"task": task, "account": account, "standalone": True, "context_isolated": True}


def valid_composers(page, base, output):
    picture = io.BytesIO()
    Image.new("RGB", (80, 60), "navy").save(picture, "PNG")
    page.goto(base + "/app/?module=ai&view=main")
    frame = active(page)
    expect(frame.locator("#ai-console-input textarea")).to_be_visible(timeout=90000)
    with page.expect_file_chooser() as chooser:
        frame.locator("#ai-console-composer .composer-attach").click()
    chooser.value.set_files({"name": "正常研究图.png", "mimeType": "image/png", "buffer": picture.getvalue()})
    expect(frame.locator("#ai-console-composer")).to_contain_text(re.compile(r"正常研究图\s*\.png"), timeout=30000)
    frame.locator("#ai-console-input textarea").fill("验证正常图片附件，明确使用测试后台。")
    frame.locator("#ai-console-input textarea").press("Enter")
    expect(frame.locator("#ai-console-chat-history")).to_contain_text("测试模式回答", timeout=60000)
    page.screenshot(path=str(output / "07-valid-image-workbench.jpg"), type="jpeg", quality=88)
    frame = navigate(page, "strategy", "etf")
    expect(frame.get_by_label("ETF池", exact=True).filter(visible=True)).to_be_visible(timeout=90000)
    frame.locator("#ai-floating-button").click()
    panel = frame.locator("#ai-floating-panel")
    expect(panel.locator("#ai-chat-input textarea")).to_be_visible()
    with page.expect_file_chooser() as chooser:
        panel.locator(".composer-attach").click()
    chooser.value.set_files({"name": "悬浮伪图片.jpg", "mimeType": "image/jpeg", "buffer": b"not an image"})
    expect(panel.locator("#ai-chat-composer")).to_contain_text(re.compile(r"悬浮伪图片\s*\.jpg"), timeout=30000)
    panel.locator("#ai-chat-input textarea").fill("图片入口拦截验收")
    panel.locator("#ai-chat-input textarea").press("Enter")
    expect(frame.get_by_text("校验失败", exact=False).filter(visible=True).first).to_be_visible(timeout=30000)
    expect(panel.locator("#ai-chat-input textarea")).to_have_value("图片入口拦截验收")
    page.screenshot(path=str(output / "08-floating-image-rejection.jpg"), type="jpeg", quality=88)
    return {"valid_image_mock_response": True, "floating_rejected_invalid": True, "real_vision_not_claimed": True}


def main(base, costs_path, output):
    output.mkdir(parents=True, exist_ok=True)
    results, errors = {}, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
        page = context.new_page()
        try:
            results["task_account"] = task_and_account(
                page, base, json.loads(costs_path.read_text(encoding="utf-8")), output
            )
            results["composers"] = valid_composers(page, base, output)
            assert not errors, errors
        finally:
            results["page_errors"] = errors
            (output / "context-results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            page.screenshot(path=str(output / "context-last.jpg"), type="jpeg", quality=88)
            browser.close()
    logger.info("Context and composers acceptance passed: {}", results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--costs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    main(args.base_url, args.costs, args.output)
