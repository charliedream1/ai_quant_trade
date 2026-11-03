"""Real Gradio clicks validate reading, Markdown persistence and Office presentation."""

import argparse
import hashlib
import json
from pathlib import Path
from threading import Event
from time import perf_counter

import requests
from loguru import logger
from playwright.sync_api import expect, sync_playwright
from workspace_revision_acceptance import active, navigate


def reader(page):
    return active(page).frame_locator(".file-reader-panel iframe")


def shot(page, output, name):
    page.screenshot(path=str(output / (name + ".jpg")), type="jpeg", quality=88)


def project_markdown(page, base, output):
    page.goto(base + "/app/?module=ai&view=main")
    frame = active(page)
    expect(frame.locator("#ai-console-input textarea")).to_be_visible(timeout=90000)
    frame.locator("#ai-console-files-toggle").click()
    frame.get_by_label("相对路径", exact=True).fill("egs/file_preview_examples/preview.md")
    frame.get_by_role("button", name="打开文件", exact=True).click()
    view = reader(page)
    expect(view.locator("#file-title")).to_have_text("preview.md", timeout=30000)
    expect(view.locator("#markdown-preview")).to_contain_text("阅读与编辑演示")
    expect(view.locator("#markdown-preview img")).to_be_visible()
    assert view.locator("#markdown-preview img").evaluate("image=>image.complete&&image.naturalWidth>0")
    view.locator("#edit-file").click()
    editor = view.locator("#markdown-editor")
    original = editor.input_value()
    editor.fill(original + "\n\n浏览器保存验收：更新后的中文正文。")
    page.once("dialog", lambda dialog: dialog.dismiss())
    frame.get_by_role("button", name="关闭文件阅读", exact=True).click()
    expect(editor).to_have_value(original + "\n\n浏览器保存验收：更新后的中文正文。")
    metadata = view.locator("body").evaluate("body=>({id:body.dataset.fileId,api:body.dataset.api})")
    other = page.context.new_page()
    other.goto(base + metadata["api"] + "/file-previews/" + metadata["id"] + "/view")
    expect(other.locator("#edit-file")).to_be_visible(timeout=30000)
    other.locator("#edit-file").click()
    other.locator("#markdown-editor").fill("过时窗口修改，不应覆盖新文件。")
    view.locator("#save-file").click()
    expect(view.locator("#reader-status")).to_contain_text("已保存", timeout=30000)
    shot(page, output, "01-markdown-editor")
    other.locator("#save-file").click()
    expect(other.locator("#reader-status")).to_contain_text("其他窗口修改", timeout=15000)
    other.screenshot(path=str(output / "02-markdown-conflict.jpg"), type="jpeg", quality=88)
    other.once("dialog", lambda dialog: dialog.accept())
    other.close()
    view.locator("#reload-file").click()
    expect(view.locator("#markdown-preview")).to_contain_text("更新后的中文正文", timeout=15000)
    view.locator("#edit-file").click()
    editor.fill(original)
    view.locator("#save-file").click()
    expect(view.locator("#reader-status")).to_contain_text("已保存", timeout=15000)
    frame.get_by_role("button", name="关闭文件阅读", exact=True).click()
    return {"saved_reopened": True, "conflict_blocked": True, "dirty_close_cancelled": True, "source_restored": True}


def open_upload(page, sample):
    frame = navigate(page, "knowledge", "library")
    expect(frame.get_by_text("文件阅读与Markdown编辑", exact=True)).to_be_visible(timeout=90000)
    if not frame.locator("#reader-upload-open").is_visible():
        frame.get_by_text("文件阅读与Markdown编辑", exact=True).click()
    if frame.locator("#reader-upload input[type='file']").count() == 0:
        frame.locator("#reader-upload-replace").click()
    frame.locator("#reader-upload input[type='file']").set_input_files(str(sample))
    frame.locator("#reader-upload-open").click()
    view = reader(page)
    expect(view.locator("#file-title")).to_have_text(sample.name, timeout=30000)
    return view


def office_readers(page, base, samples, output):
    results = {}
    for kind, name in (("docx", "中文研报样本.docx"), ("xlsx", "组合配置样本.xlsx"), ("pptx", "presentation.pptx")):
        sample = samples / name
        started = perf_counter()
        view = open_upload(page, sample)
        expect(view.locator("#reader-status")).to_contain_text("已完成转换", timeout=90000)
        expect(view.locator("#pdf-canvas")).to_be_visible()
        assert view.locator("#pdf-canvas").evaluate("canvas=>canvas.width>0&&canvas.height>0")
        expect(view.locator("#edit-file")).to_be_hidden()
        if kind == "docx":
            shot(page, output, "03-office-docx-first")
            view.locator("#pdf-search").fill("第二页")
            view.locator("#search-pdf").click()
            expect(view.locator("#search-result")).to_contain_text("第 2 页匹配", timeout=30000)
            view.locator("#zoom-in").click()
        shot(page, output, "03-office-" + kind)
        with page.expect_download() as download:
            view.locator("#download-file").click()
        saved = output / ("download-" + sample.name)
        download.value.save_as(str(saved))
        assert hashlib.sha256(saved.read_bytes()).digest() == hashlib.sha256(sample.read_bytes()).digest()
        results[kind] = {"seconds": round(perf_counter() - started, 3), "readonly": True, "download_exact": True}
        active(page).get_by_role("button", name="关闭文件阅读", exact=True).click()
    return results


def knowledge_and_attachment(page, base, samples, output):
    path = samples / "阅读笔记.md"
    response = requests.post(
        base + "/api/v1/kb/documents", files={"file": (path.name, path.read_bytes())}, timeout=30
    ).json()
    assert response["code"] == 0, response
    frame = navigate(page, "knowledge", "library")
    frame.get_by_label("文档 ID", exact=True).filter(visible=True).fill(str(response["data"]["doc_id"]))
    frame.locator("#kb-read-original").click()
    view = reader(page)
    expect(view.locator("#file-title")).to_have_text(path.name, timeout=30000)
    view.locator("#edit-file").click()
    view.locator("#markdown-editor").fill("# 已保存的知识笔记\n\n引用验收词条：风险暴露与集中度。")
    view.locator("#save-file").click()
    expect(view.locator("#reader-status")).to_contain_text("已保存", timeout=30000)
    assert requests.get(base + "/api/v1/kb/search", params={"keyword": "引用验收词条"}, timeout=30).json()["data"][
        "items"
    ]
    shot(page, output, "04-knowledge-markdown")
    frame.get_by_role("button", name="关闭文件阅读", exact=True).click()
    frame = navigate(page, "ai", "main")
    if frame.locator("#ai-console-files-close").is_visible():
        frame.locator("#ai-console-files-close").click()
    with page.expect_file_chooser() as chooser:
        frame.locator("#ai-console-composer .composer-attach").click()
    chooser.value.set_files(str(path))
    frame.locator("#ai-console-input textarea").fill("附件阅读入口验收，使用测试后台。")
    frame.locator("#ai-console-input textarea").press("Enter")
    link = frame.locator("#ai-console-chat-history").get_by_role("link", name=path.name, exact=True).first
    expect(link).to_be_visible(timeout=60000)
    link.click()
    expect(reader(page).locator("#markdown-preview")).to_contain_text("Markdown阅读与编辑样本", timeout=30000)
    shot(page, output, "05-chat-attachment-reader")
    frame.get_by_role("button", name="关闭文件阅读", exact=True).click()
    return {"knowledge_saved_and_indexed": True, "attachment_opened": True, "chat_backend": "explicit_mock"}


def other_readers(page, base, samples, output):
    view = open_upload(page, samples / "sample.html")
    expect(view.locator("#html-preview")).to_be_visible(timeout=30000)
    expect(view.frame_locator("#html-preview").get_by_text("HTML阅读样本", exact=True)).to_be_visible()
    expect(view.locator("#edit-file")).to_be_hidden()
    shot(page, output, "06-html-reader")
    active(page).get_by_role("button", name="关闭文件阅读", exact=True).click()
    view = open_upload(page, samples / "illustration.png")
    expect(view.locator("#image-preview")).to_be_visible(timeout=30000)
    assert view.locator("#image-preview").evaluate("image => image.complete && image.naturalWidth > 0")
    active(page).get_by_role("button", name="关闭文件阅读", exact=True).click()
    frame = navigate(page, "ai", "main")
    frame.locator("#ai-console-files-toggle").click()
    frame.get_by_label("相对路径", exact=True).fill("egs/file_preview_examples/preview.md")
    frame.get_by_role("button", name="打开文件", exact=True).click()
    view = reader(page)
    expect(view.locator("#markdown-preview")).to_be_visible(timeout=30000)
    page.locator("#app-theme-toggle").click()
    expect(view.locator("html")).to_have_attribute("data-theme", "dark", timeout=15000)
    expect(view.locator("#markdown-preview img")).not_to_have_js_property("naturalWidth", 0, timeout=15000)
    shot(page, output, "07-dark-reader")
    view.locator("#fullscreen").click()
    expect(view.locator("#fullscreen")).to_have_text("退出全屏", timeout=15000)
    assert view.locator("html").evaluate("element => document.fullscreenElement === element")
    shot(page, output, "08-fullscreen-reader")
    view.locator("#fullscreen").click()
    active(page).get_by_role("button", name="关闭文件阅读", exact=True).click()
    page.locator("#app-theme-toggle").click()
    payload = b"<!doctype html><h1>Isolated HTML fixture</h1><script>parent.__previewProbe=true</script>"
    row = requests.post(
        base + "/api/v1/file-previews/uploads", files={"file": ("isolated.html", payload)}, timeout=30
    ).json()["data"]
    isolated = page.context.new_page()
    isolated.goto(base + row["url"])
    expect(isolated.frame_locator("#html-preview").get_by_text("Isolated HTML fixture")).to_be_visible(timeout=30000)
    assert isolated.evaluate("typeof window.__previewProbe") == "undefined"
    isolated.close()
    return {"html": True, "image": True, "dark": True, "fullscreen": True, "html_scripts_blocked": True}


def main(base, samples, output):
    output.mkdir(parents=True, exist_ok=True)
    deadline = perf_counter() + 60
    while True:
        try:
            if requests.get(base + "/api/v1/health", timeout=5).status_code == 200:
                break
        except requests.RequestException:
            pass
        assert perf_counter() < deadline, "Isolated test service did not become ready"
        Event().wait(0.2)
    results, errors = {}, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
        page = context.new_page()
        try:
            results["markdown"] = project_markdown(page, base, output)
            results["office"] = office_readers(page, base, samples, output)
            results["knowledge_attachment"] = knowledge_and_attachment(page, base, samples, output)
            results["other_readers"] = other_readers(page, base, samples, output)
            assert not errors, errors
        finally:
            results["page_errors"] = errors
            (output / "browser-results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            shot(page, output, "browser-last")
            browser.close()
    logger.info("File preview browser checks passed: {}", results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--samples", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    main(args.base_url, args.samples, args.output)
