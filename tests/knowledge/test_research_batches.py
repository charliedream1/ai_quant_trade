"""Research source scope, classification, persistence and browser coverage."""

from threading import Event
from time import monotonic, sleep

import pytest
from playwright.sync_api import expect, sync_playwright

from src.agent.llm_client import LLMClient
from src.agent.real_models import REQUIRE_REAL_MODEL
from src.core.repository import Repository
from src.knowledge import research_batch_import, research_batches, research_catalog
from src.knowledge.files import KnowledgeFiles
from src.knowledge.research_classification import classify
from src.knowledge.research_metadata import documents, facets, reclassify


def _report(title, identifier, org, date):
    return {
        "id": identifier,
        "title": title,
        "org": org,
        "publish_date": date,
        "source": "test-report",
        "url": f"https://example.org/research/{identifier}.txt",
    }


def _download(url, **kwargs):
    identifier = url.rsplit("/", 1)[-1]
    return identifier, f"量化因子回测、动量因子、价值策略。Factor momentum backtesting {identifier}".encode(), url


def _finish(service, key):
    deadline = monotonic() + 12
    while monotonic() < deadline:
        status, rows = service.status(key)
        if status in {"completed", "cancelled"}:
            return status, rows
        sleep(0.05)
    raise AssertionError(service.status(key))


def test_two_page_selection_all_duplicate_and_facets(client, monkeypatch):
    reports = [
        _report("因子回测", 100, "证券研究院", "2025-12-30"),
        _report("Factor momentum", 200, "", "2026-01-01"),
        _report("价值因子回测", 300, "资产研究院", ""),
    ]
    calls = []

    class Source:
        market = "CN"

        def research_report_page(self, symbol, page, size):
            calls.append((symbol, page))
            return reports[(page - 1) * size : page * size]

    monkeypatch.setattr(research_catalog, "DataSourceManager", Source)
    monkeypatch.setitem(research_catalog.policy()["limits"], "page_size", 2)
    monkeypatch.setattr(research_batch_import, "download_document", _download)
    service = research_batches.ResearchBatches()
    key, scope, choices = service.prepare("report", ("", "600519"))
    assert scope["complete"] and calls == [("600519", 1), ("600519", 2)]
    service.start(key, [choices[-1][1]], False, "Research", "traditional")
    status, rows = _finish(service, key)
    assert status == "completed" and len(rows) == 1 and rows[0][1] == "imported"
    reclassify("Research", rows[0][2], "risk")
    complete, _, _ = service.prepare("report", ("", "600519"))
    service.start(complete, [], True, "Research", "traditional")
    _, rows = _finish(service, complete)
    assert sorted(row[1] for row in rows) == ["duplicate", "imported", "imported"]
    assert [item["title"] for item in documents("Research", "2025", "证券研究院", "strategies", "研报")] == ["因子回测"]
    assert [item["topic"] for item in documents("Research", "unknown", "资产研究院")] == ["风险计量与对冲"]
    assert [item["title"] for item in documents("Research", "2026", "unknown")] == ["Factor momentum"]
    assert [row["year"] for row in facets("Research")[0]] == [2026, 2025]
    categories = facets("Research")[2]
    parent = next(row["parent_id"] for row in categories if row["name"] == "因子策略与回测")
    assert len(KnowledgeFiles().documents("Research", category_id=parent)) == 2
    assert KnowledgeFiles().documents("Other", category_id=parent) == []
    assert Repository().db.scalar("SELECT COUNT(*) FROM kb_research_metadata WHERE manual=1") == 1


def test_traditional_classifier_returns_review_when_evidence_is_missing():
    assert classify("Monetary policy central bank exchange rates", "traditional")[0] == "policy"
    assert classify("订单簿 做市 市场微观结构 滑点", "traditional")[0] == "execution"
    assert classify("an unrelated recipe for bread", "traditional")[0] == ""


def test_llm_repairs_response_and_requires_real_profile(monkeypatch):
    def complete(_self, prompt, **options):
        assert REQUIRE_REAL_MODEL.get() and options["model_id"] == 7
        assert options["max_output_chars"] > 0 and "categories" in prompt
        return {"text": "{category:'risk',confidence:0.91}", "model": "llm-contract-test"}

    monkeypatch.setattr(LLMClient, "complete", complete)
    assert classify("Credit exposure and issuer default scenarios", "llm", 7) == ("risk", 0.91, "llm-contract-test")


def test_cancel_and_retry_preserve_finished_papers(client, monkeypatch):
    items = [
        research_catalog._manifest(
            "paper",
            {
                "title": title,
                "source": "arXiv",
                "published_at": "2024-05-02",
                "institutions": ["Research University", "Applied Finance Institute"],
                "url": f"https://example.org/{index}.txt",
            },
        )
        for index, title in enumerate(["Momentum factor", "Value factor"], 1)
    ]
    blocked = Event()

    def download(url, *, check, **options):
        if url.endswith("/2.txt"):
            blocked.set()
            while True:
                check()
                sleep(0.02)
        return _download(url)

    monkeypatch.setattr(research_batches, "collect", lambda *args: (items, {"kind": "paper"}))
    monkeypatch.setattr(research_batch_import, "download_document", download)
    service = research_batches.ResearchBatches()
    key, _, _ = service.prepare("paper", ("", "", None, None))
    service.start(key, [], True, "Papers", "traditional")
    assert blocked.wait(12)
    service.cancel(key)
    status, rows = _finish(service, key)
    assert status == "cancelled" and sorted(row[1] for row in rows) == ["imported", "pending"]
    monkeypatch.setattr(research_batch_import, "download_document", _download)
    service.retry(key)
    _, rows = _finish(service, key)
    assert [row[1] for row in rows] == ["imported", "imported"]
    filtered = documents("Papers", 2024, "applied finance institute", "group:investment", "论文")
    assert len(filtered) == 2 and all("Research University" in row["institutions"] for row in filtered)


def test_model_installer_requires_confirmation():
    from src.knowledge.research_onnx import install

    with pytest.raises(ValueError, match="Confirm"):
        install(False)


def test_report_landing_page_resolves_the_published_pdf(monkeypatch):
    landing = "https://example.org/report/100"
    pdf = "https://example.org/pdf/100.pdf?published.pdf"
    calls = []

    def download(url, **options):
        calls.append(url)
        if url == landing:
            return "100.html", b'<a class="pdf-link" href="/pdf/100.pdf?published.pdf">PDF</a>', url
        return "100.pdf", b"%PDF-1.7", url

    monkeypatch.setattr(research_batch_import, "download_document", download)
    item = {"kind": "report", "provider": "eastmoney-report", "landing_url": landing, "url": pdf}
    assert research_batch_import._download(item, lambda: None) == ("100.pdf", b"%PDF-1.7")
    assert calls == [landing, pdf]
    monkeypatch.setattr(
        research_batch_import, "download_document", lambda *args, **kwargs: ("100.pdf", b"<script></script>", pdf)
    )
    with pytest.raises(ValueError, match="without a PDF"):
        research_batch_import._download(item, lambda: None)


@pytest.mark.parametrize("kind,tab,all_results", [("report", "研报检索", True), ("paper", "论文检索", False)])
def test_browser_batch_and_library_facets(cli_command, monkeypatch, kind, tab, all_results):
    title = "因子回测批量验收"
    item = research_catalog._manifest(
        kind,
        _report(title, 100, "证券研究院", "2025-12-30")
        if kind == "report"
        else {
            "title": title,
            "source": "arXiv",
            "published_at": "2025-12-30",
            "institutions": ["证券研究院"],
            "url": "https://example.org/paper/100.txt",
        },
    )
    monkeypatch.setattr(
        research_batches, "collect", lambda *args: ([item], {"kind": kind, "market": "CN", "complete": True})
    )
    monkeypatch.setattr(research_batch_import, "download_document", _download)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
            page.goto(
                cli_command.base_url + f"/app/?module=knowledge&view=research&tab={tab}",
                wait_until="domcontentloaded",
            )
            frame = page.frame_locator("iframe.workspace-frame.active")
            prefix = f"#research-batch-{kind}"
            panel = frame.locator(prefix)
            expect(panel).to_be_visible(timeout=90000)
            panel.locator(".label-wrap").first.click()
            panel.locator(f"{prefix}-prepare").click()
            expect(panel).to_contain_text("共 1 条", timeout=30000)
            if all_results:
                panel.locator(f"{prefix}-all input").check()
            else:
                panel.locator(f"{prefix}-selection input").click()
                panel.get_by_role("option", name=title).click()
            panel.locator(f"{prefix}-start").click()
            expect(panel.locator(f"{prefix}-status")).to_contain_text("处理完成", timeout=30000)
            expect(panel.locator(f"{prefix}-status")).to_contain_text("已入库 1")
            page.locator('[data-workspace-view-module="knowledge"][data-workspace-view="library"]').click()
            frame.get_by_role("button", name="刷新知识库", exact=True).click()
            expect(frame.locator("#kb-research-documents")).to_contain_text("证券研究院", timeout=30000)
            expect(frame.locator("#kb-research-documents")).to_contain_text("2025")
        finally:
            browser.close()
