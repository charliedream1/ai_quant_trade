"""Visible Gradio operations for design 18; API only seeds an isolated fixture."""

import argparse
import base64
import json
from pathlib import Path
from time import perf_counter

import requests
from loguru import logger
from playwright.sync_api import expect, sync_playwright


def active(page):
    return page.frame_locator("iframe.workspace-frame.active")


def navigate(page, module, view):
    if page.locator(".sidebar-collapsed").count():
        page.locator("#workspace-sidebar-toggle").click()
    group = page.locator(f"[data-workspace-module='{module}']")
    if not page.locator(f"[data-workspace-view-module='{module}'][data-workspace-view='{view}']").is_visible():
        group.click()
    page.locator(f"[data-workspace-view-module='{module}'][data-workspace-view='{view}']").click()
    return active(page)


def composer(page, base, output):
    page.goto(base + "/app/?module=ai&view=main")
    frame = active(page)
    expect(frame.locator("#ai-console-input textarea")).to_be_visible(timeout=90000)
    expect(frame.locator(".composer-attach").first).to_be_visible()
    toolbar = frame.locator("#ai-console-composer-footer").bounding_box()
    assert toolbar["height"] <= 48, toolbar
    with page.expect_file_chooser() as chooser:
        frame.locator("#ai-console-composer .composer-attach").click()
    chooser.value.set_files(
        {"name": "research-note.txt", "mimeType": "text/plain", "buffer": "回测需核对真实日期与费用。".encode()}
    )
    expect(frame.locator("#ai-console-attachments .filename")).to_contain_text("research-note")
    frame.locator("#ai-console-input textarea").fill("请简要说明回测日期需要如何核对")
    frame.locator("#ai-console-input textarea").press("Enter")
    expect(frame.locator("#ai-console-chat-history")).to_contain_text("回测日期", timeout=90000)
    expect(frame.locator("#ai-console-status")).to_contain_text("GenericAgent mock", timeout=30000)
    page.screenshot(path=str(output / "01-flat-composer.jpg"), type="jpeg", quality=88)
    # A real browser DataTransfer exercises the same native upload input as the icon.
    png = base64.b64encode((output / "01-flat-composer.jpg").read_bytes()).decode()
    frame.locator("#ai-console-composer").evaluate(
        """(el, data) => {
      const transfer = new DataTransfer();
      const bytes = Uint8Array.from(atob(data), (character) => character.charCodeAt(0));
      transfer.items.add(new File([bytes], 'drag-picture.jpg', {type:'image/jpeg'}));
      el.dispatchEvent(new DragEvent('drop', {bubbles:true, cancelable:true, dataTransfer:transfer}));
    }""",
        png,
    )
    expect(frame.locator("#ai-console-attachments .filename")).to_contain_text("drag-picture")
    frame.locator("#ai-console-input textarea").fill("第一行")
    frame.locator("#ai-console-input textarea").press("Shift+Enter")
    assert "\n" in frame.locator("#ai-console-input textarea").input_value()
    page.locator("#workspace-sidebar-toggle").click()
    page.set_viewport_size({"width": 1180, "height": 900})
    assert frame.locator("#ai-console-composer-footer").bounding_box()["height"] <= 48
    page.screenshot(path=str(output / "02-compact-composer.jpg"), type="jpeg", quality=88)
    page.set_viewport_size({"width": 1440, "height": 1000})
    return {"toolbar": toolbar, "attachment_icon": True, "native_drop": True, "enter": True, "shift_enter": True}


def insights(page, output):
    started = perf_counter()
    frame = navigate(page, "ai", "insights")
    expect(frame.get_by_role("button", name="Market Review · 市场复盘", exact=True)).to_be_visible(timeout=60000)
    expect(frame.get_by_role("button", name="Single Stock Analysis · 个股分析", exact=True)).to_be_visible()
    frame.get_by_role("button", name="Single Stock Analysis · 个股分析", exact=True).click()
    expect(frame.get_by_label("运行状态", exact=True)).to_have_value("个股分析需要有效证券代码或名称")
    page.screenshot(path=str(output / "03-skill-report-controls.jpg"), type="jpeg", quality=88)
    return {"seconds": round(perf_counter() - started, 3), "initial_controls": True}


def knowledge(page, base, output):
    response = requests.post(
        base + "/api/v1/kb/notes",
        json={"title": "量化回撤教学", "content": "回撤是净值相对历史峰值的下降幅度。最大回撤衡量路径风险。"},
        timeout=30,
    ).json()
    assert response["code"] == 0, response
    frame = navigate(page, "knowledge", "qa")
    expect(frame.get_by_role("button", name="提问", exact=True)).to_be_visible(timeout=60000)
    frame.get_by_label("问题", exact=True).fill("回撤")
    frame.get_by_role("button", name="提问", exact=True).click()
    expect(frame.locator("#rag-chat-history")).to_contain_text("回撤", timeout=60000)
    expect(frame.get_by_text("answered", exact=False).first).to_be_visible(timeout=60000)
    frame.get_by_role("button", name="刷新索引与会话", exact=True).click()
    expect(frame.get_by_text("个分块", exact=False).first).to_be_visible()
    # Select the first citation row, then verify the original document text is displayed.
    frame.locator("#rag-chat-references").get_by_text("量化回撤教学", exact=True).filter(visible=True).first.click()
    expect(frame.get_by_text("最大回撤衡量路径风险。", exact=False).last).to_be_visible()
    page.screenshot(path=str(output / "04-rag-citations.jpg"), type="jpeg", quality=88)
    session = frame.get_by_label("会话 ID", exact=True).input_value()
    frame.get_by_role("button", name="恢复此会话", exact=True).click()
    expect(frame.locator("#rag-chat-history")).to_contain_text("回撤")
    return {"session": session, "citation_doc_id": response["data"]["doc_id"], "restored": True}


def learning(page, output):
    frame = navigate(page, "learning", "course")
    expect(frame.locator("#quant-course-content")).to_contain_text("课程导读", timeout=60000)
    frame.get_by_role("button", name="下一章", exact=True).click()
    expect(frame.locator("#quant-course-content")).to_contain_text("研究流程与假设")
    frame.get_by_text("08 · 回测撮合与偏差", exact=True).click()
    expect(frame.locator("#quant-course-content")).to_contain_text("净收益97.9元")
    page.screenshot(path=str(output / "05-quant-course.jpg"), type="jpeg", quality=88)
    frame.get_by_role("button", name="上一章", exact=True).click()
    expect(frame.locator("#quant-course-content")).to_contain_text("趋势、反转与轮动")
    return {"chapters": 13, "previous_next": True, "direct_chapter": True}


def main(base, output):
    output.mkdir(parents=True, exist_ok=True)
    results, errors = {}, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            for name, operation in (
                ("composer", lambda: composer(page, base, output)),
                ("insights", lambda: insights(page, output)),
                ("knowledge", lambda: knowledge(page, base, output)),
                ("learning", lambda: learning(page, output)),
            ):
                try:
                    results[name] = operation()
                    logger.info("Browser acceptance passed: {}", name)
                except Exception as exc:
                    results[name] = {"error": str(exc)}
                    page.screenshot(path=str(output / f"failure-{name}.jpg"), type="jpeg")
                    logger.exception("Browser acceptance failed: {}", name)
        finally:
            browser.close()
    (output / "browser-results.json").write_text(
        json.dumps({"results": results, "page_errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert not errors and all("error" not in row for row in results.values()), results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base_url, args.output)
