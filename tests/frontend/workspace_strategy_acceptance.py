"""One-click ordinary/composition runs, frozen graph navigation and real CLI dialogue."""

import argparse
import json
import re
from pathlib import Path
from uuid import uuid4

import requests
from playwright.sync_api import expect, sync_playwright
from workspace_revision_acceptance import active, navigate

from src.strategy.composition.config import template


def api(base, path, payload):
    result = requests.post(base + "/api/v1" + path, json=payload, timeout=60).json()
    assert result["code"] == 0, result
    return result["data"]


def main(base, output):
    output.mkdir(parents=True, exist_ok=True)
    suffix = uuid4().hex[:8]
    ordinary = api(
        base,
        "/strategy-examples/import",
        {"example": "egs/examples/strategy_examples/dual_ma_strategy.py", "name": "workspace-ui-" + suffix},
    )
    definition = template("rule_trend")
    definition["name"] += "-" + suffix
    draft = api(base, "/strategy-pipelines", {"definition": definition})
    version = api(base, f"/strategy-pipelines/{draft['id']}/publish", {})
    results = {"ordinary_strategy": ordinary["id"], "version": version}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            page.goto(base + "/app/?module=strategy&view=management")
            frame = active(page)
            expect(frame.get_by_role("tab", name="策略库", exact=True)).to_be_visible(timeout=90000)
            frame.get_by_role("tab", name="策略库", exact=True).click()
            for label, strategy_id in (("ordinary", ordinary["id"]), ("composition", version["strategy_id"])):
                frame.get_by_label("策略 ID", exact=True).fill(str(strategy_id))
                frame.get_by_label("开始日期", exact=True).fill("2026-01-05")
                frame.get_by_label("结束日期", exact=True).fill("2026-01-16")
                previous_id = frame.get_by_label("回测任务 ID（可恢复）", exact=True).input_value()
                frame.get_by_role("button", name="策略一键回测", exact=True).click()
                if previous_id:
                    expect(frame.get_by_label("回测任务 ID（可恢复）", exact=True)).not_to_have_value(
                        previous_id, timeout=30000
                    )
                task_id = int(frame.get_by_label("回测任务 ID（可恢复）", exact=True).input_value())
                status = (
                    frame.locator(".status-strip")
                    .filter(has_text=re.compile(r"任务\s*" + str(task_id)))
                    .filter(visible=True)
                    .first
                )
                expect(status).to_contain_text(re.compile("finished|已完成"), timeout=90000)
                task = requests.get(base + f"/api/v1/backtests/{task_id}", timeout=30).json()["data"]
                assert task["status"] == "finished" and task["engine"] == (
                    "simple" if label == "ordinary" else "composition"
                )
                results[label] = task
                page.screenshot(path=str(output / f"06-{label}-oneclick.jpg"), type="jpeg", quality=88)
            frame.get_by_role("link", name="打开此冻结图形方案", exact=True).click()
            expect(frame.locator("#strategy-graph-editor")).to_be_visible(timeout=90000)
            expect(frame.get_by_label("预置方案", exact=True)).to_have_value(re.compile("已发布 /"), timeout=30000)
            expect(frame.locator("#pipeline-route-version textarea")).to_have_value(str(version["id"]))
            page.screenshot(path=str(output / "07-frozen-graph-navigation.jpg"), type="jpeg", quality=88)
            results["frozen_navigation"] = {"url": page.url, "version_id": version["id"]}

            frame = navigate(page, "ai", "main")
            expect(frame.locator("#ai-console-input textarea")).to_be_visible(timeout=90000)
            frame.locator("#ai-console-backend input").click()
            frame.get_by_role("option", name="Codex CLI", exact=True).click()
            frame.locator("#ai-console-input textarea").fill(
                "仅回答：端到端连接成功。不要读取或修改文件，不要执行命令。"
            )
            frame.locator("#ai-console-input textarea").press("Enter")
            expect(frame.locator("#ai-console-status")).to_contain_text(
                re.compile("Codex CLI (completed|finished|已完成)", re.IGNORECASE), timeout=90000
            )
            expect(frame.locator("#ai-console-chat-history")).to_contain_text("端到端连接成功")
            results["real_cli"] = {
                "status": frame.locator("#ai-console-status").inner_text(),
                "history": frame.locator("#ai-console-chat-history").inner_text(),
            }
            page.screenshot(path=str(output / "08-real-cli-workbench.jpg"), type="jpeg", quality=88)
            frame = navigate(page, "learning", "course")
            expect(frame.locator("#quant-course-content")).to_be_visible(timeout=60000)
            frame.locator("#ai-floating-button").click()
            panel = frame.locator("#ai-floating-panel")
            expect(panel).to_be_visible()
            panel.locator("#ai-chat-input textarea").fill("第一行")
            panel.locator("#ai-chat-input textarea").press("Shift+Enter")
            assert "\n" in panel.locator("#ai-chat-input textarea").input_value()
            panel.locator("#ai-chat-input textarea").fill("验证悬浮输入框回车发送")
            panel.locator("#ai-chat-input textarea").press("Enter")
            expect(panel.locator("#ai-chat-status")).to_contain_text("GenericAgent mock", timeout=60000)
            page.screenshot(path=str(output / "09-floating-composer.jpg"), type="jpeg", quality=88)
            results["floating_enter"] = True
            assert not errors, errors
        finally:
            results["page_errors"] = errors
            (output / "strategy-browser.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            page.screenshot(path=str(output / "strategy-last.jpg"), type="jpeg", quality=88)
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base_url, args.output)
