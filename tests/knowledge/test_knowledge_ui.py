"""Actual browser upload, scoped Q&A and left-half citation reading."""

from playwright.sync_api import expect, sync_playwright

from src.agent.llm_client import LLMClient
from src.knowledge.config import knowledge_config


def test_browser_ingestion_question_and_citation(cli_command, keyword_model, tmp_path, monkeypatch):
    original = LLMClient.complete

    def answer(self, prompt, *args, **kwargs):
        if prompt.startswith(knowledge_config()["search"]["planner_prompt"].splitlines()[0]):
            return original(self, prompt, *args, **kwargs)
        return {"text": "测试模型回答：回撤是净值相对历史高点的下降。[1]", "model": "fixture-answer"}

    monkeypatch.setattr(LLMClient, "complete", answer)
    source = tmp_path / "风险资料.md"
    source.write_text("# 回撤\n\n回撤是净值相对历史高点的下降。", encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
        page.goto(cli_command.base_url + "/app/?module=knowledge&view=library", wait_until="domcontentloaded")
        frame = page.frame_locator("iframe.workspace-frame.active")
        library = frame.locator("#kb-ingest-library input")
        expect(library).to_be_visible(timeout=90000)
        library.fill("浏览器测试库")
        library.press("Enter")
        frame.get_by_role("button", name="创建知识库", exact=True).click()
        expect(frame.locator("#kb-ingest-status")).to_contain_text("已创建", timeout=30000)
        frame.locator("#kb-ingest-files input[type=file]").set_input_files(str(source))
        frame.get_by_role("button", name="文件入库", exact=True).click()
        expect(frame.locator("#kb-ingest-status")).to_contain_text("已入库", timeout=30000)
        if page.locator("#notification-toasts .notification-card-top button").count():
            page.locator("#notification-toasts .notification-card-top button").first.click()
        page.screenshot(path=str(tmp_path / "knowledge-ingestion.png"))
        page.locator('[data-workspace-view-module="knowledge"][data-workspace-view="qa"]').click()
        frame.get_by_role("button", name="刷新库名", exact=True).click()
        selector = frame.locator("#rag-library input")
        selector.click()
        frame.get_by_role("option", name="浏览器测试库", exact=True).click()
        frame.get_by_label("问题", exact=True).fill("回撤是什么？")
        attachment = tmp_path / "问答补充.txt"
        attachment.write_text("回撤分析需要核对统计区间。", encoding="utf-8")
        frame.locator("#rag-attachments input[type=file]").set_input_files(str(attachment))
        frame.get_by_role("button", name="提问", exact=True).click()
        expect(frame.locator("#rag-chat-references")).to_contain_text("风险资料", timeout=30000)
        page.screenshot(path=str(tmp_path / "knowledge-question.png"))
        (tmp_path / "references.html").write_text(frame.locator("#rag-chat-references").inner_html(), encoding="utf-8")
        frame.locator("#rag-chat-references").get_by_text("风险资料", exact=True).filter(visible=True).first.click()
        panel = frame.locator(".file-reader-panel-left")
        expect(panel).to_be_visible(timeout=30000)
        assert (
            abs(
                panel.bounding_box()["width"] / page.locator("iframe.workspace-frame.active").bounding_box()["width"]
                - 0.5
            )
            < 0.02
        )
        preview = panel.frame_locator("iframe")
        expect(preview.locator("#markdown-preview")).to_contain_text("回撤是净值", timeout=30000)
        page.screenshot(path=str(tmp_path / "knowledge-citation.png"))
        panel.get_by_role("button", name="关闭文件阅读").click()
        expect(panel).to_have_count(0)
        browser.close()
