"""Real text-only Office/PDF extraction and downloads through the import boundary."""

from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfWriter

from src.core.kb_importer import parse_document_bytes
from src.core.repository import Repository
from src.data import DataSourceManager
from src.knowledge import download
from src.knowledge.search import KeywordSearch
from tests.engine.preview_fixture_builder import export


def test_actual_doc_pdf_and_scanned_pdf_rejection(client, tmp_path):
    source = tmp_path / "text.docx"
    document = Document()
    document.add_heading("量化研究", level=1)
    document.add_paragraph("回撤风险与仓位控制")
    document.save(source)
    legacy = export(source, "doc", tmp_path)
    pdf = export(source, "pdf", tmp_path)
    for path in (legacy, pdf):
        response = client.post(
            "/api/v1/kb/documents", data={"library_name": "格式测试库"}, files={"file": (path.name, path.read_bytes())}
        ).json()
        assert response["code"] == 0, response
        assert "回撤" in response["data"]["content"]
    assert len(KeywordSearch().search(["回撤"], library="格式测试库", limit=10)) == 2
    blank = PdfWriter()
    blank.add_blank_page(width=600, height=800)
    stream = BytesIO()
    blank.write(stream)
    with pytest.raises(Exception, match="OCR"):
        parse_document_bytes("scan.pdf", stream.getvalue())


def test_web_research_and_paper_imports_share_target_library(client, monkeypatch):
    requested = []

    def fetch(url):
        requested.append(url)
        return "full.md", "# 下载原文\n回撤全文证据。".encode(), url

    monkeypatch.setattr(download, "download_document", fetch)
    monkeypatch.setattr(
        DataSourceManager,
        "report_detail",
        lambda *args: {"title": "研报原文", "url": "https://research.example/full.md"},
        raising=False,
    )
    report = client.post("/api/v1/reports/import", json={"report_id": 17, "library_name": "研究库"}).json()
    assert report["code"] == 0, report
    assert report["data"]["doc_type"] == "研报"
    repo = Repository()
    paper = repo.insert(
        "papers",
        {
            "title": "论文原文",
            "authors": "[]",
            "abstract": "仅有摘要",
            "source": "arXiv",
            "url": "https://arxiv.org/abs/2601.00001",
            "published_at": "2026-01-01",
            "fetched_at": "2026-11-02",
        },
    )
    payload = {"paper_id": paper["id"], "library_name": "研究库", "download_fulltext": True}
    imported = client.post("/api/v1/papers/import", json=payload).json()
    assert imported["code"] == 0, imported
    assert requested[-1] == "https://arxiv.org/pdf/2601.00001"
    assert "全文证据" in imported["data"]["content"] and "仅有摘要" not in imported["data"]["content"]
    again = client.post("/api/v1/papers/import", json=payload).json()
    assert again["data"]["doc_id"] == imported["data"]["doc_id"] and not again["data"]["imported"]
    webpage = client.post(
        "/api/v1/kb/urls", json={"url": "https://research.example/page.md", "library_name": "网页库"}
    ).json()
    assert webpage["code"] == 0, webpage
    assert {row["title"] for row in KeywordSearch().search(["回撤"], library="研究库", limit=10)} == {
        "研报原文",
        "论文原文",
    }
