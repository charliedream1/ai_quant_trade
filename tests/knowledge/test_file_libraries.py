"""Real zvec lexical search with isolated libraries and controlled model replies."""

from io import BytesIO

import pytest
from docx import Document

from src.agent.llm_client import LLMClient
from src.core.kb_chunks import split_knowledge_chunks
from src.core.kb_importer import parse_document_bytes
from src.core.repository import Repository
from src.knowledge.files import KnowledgeFiles
from src.knowledge.search import KeywordSearch


def note(client, title, content, library="甲库"):
    response = client.post("/api/v1/kb/notes", json={"title": title, "content": content, "library_name": library})
    assert response.json()["code"] == 0, response.text
    return response.json()["data"]


def test_real_file_search_isolates_library_and_session(client):
    note(client, "甲", "# 风险\n回撤描述净值下降。")
    note(client, "乙", "回撤秘密内容。", "乙库")
    response = client.post(
        "/api/v1/kb/documents",
        data={"library_name": "甲库", "attachment_session": "private"},
        files={"file": ("附件.txt", "回撤附件内容".encode())},
    )
    assert response.json()["code"] == 0, response.text
    search = KeywordSearch()
    public = search.search(["回撤"], library="甲库", limit=10)
    private = search.search(["回撤"], library="甲库", session_id="private", limit=10)
    assert {row["title"] for row in public} == {"甲"}
    assert {row["title"] for row in private} == {"甲", "附件"}
    assert all(row["library_name"] == "甲库" for row in private)
    listed = client.get("/api/v1/kb/documents", params={"library_name": "甲库"}).json()["data"]["items"]
    assert len(listed) == 1
    assert not list(KnowledgeFiles().root.rglob(".zvec-grep"))


def test_recursive_planning_and_citations(client, monkeypatch):
    note(client, "风险", "# 风险\n回撤是净值下降。")
    note(client, "对策", "# 对策\n对冲可以降低敞口。")
    replies = iter(
        [
            '{keywords:["回撤"],sufficient:false}',
            '{"keywords":["对冲"],"sufficient":false}',
            '{"keywords":[],"sufficient":true}',
            "回撤是净值下降[1]，对冲可降低敞口[2]。",
        ]
    )
    monkeypatch.setattr(LLMClient, "complete", lambda *args, **kwargs: {"text": next(replies), "model": "fixture"})
    result = client.post(
        "/api/v1/kb/qa", json={"question": "如何处理风险？", "library_name": "甲库", "retrieval_rounds": 3}
    ).json()
    assert result["code"] == 0, result
    data = result["data"]
    assert data["status"] == "answered" and len(data["retrieval_trace"]) == 2
    assert {row["title"] for row in data["references"]} == {"风险", "对策"}
    assert all(row["library_name"] == "甲库" and row["line_number"] for row in data["references"])


def test_current_chunks_only_after_edit_and_delete(client):
    row = note(client, "版本", "旧词\n\n" + "正文" * 3500)
    repo = Repository()
    repo.update("kb_documents", row["id"], {"content": "新词"})
    from src.core.kb_chunks import refresh_document_chunks

    refresh_document_chunks(repo, row["id"])
    search = KeywordSearch(repo)
    assert not search.search(["旧词"], library="甲库", limit=5)
    assert search.search(["新词"], library="甲库", limit=5)
    repo.delete("kb_documents", row["id"])
    assert not search.search(["新词"], library="甲库", limit=5)


def test_heading_splitting_and_parser_structure():
    chunks = split_knowledge_chunks("# 一\n" + "甲" * 6000 + "\n# 二\n乙", overlap_chars=0)
    assert max(chunk["char_count"] for chunk in chunks) <= 5000
    assert chunks[-1]["heading"] == "二"
    document = Document()
    document.add_heading("研究结论", level=1)
    document.add_paragraph("正文证据")
    stream = BytesIO()
    document.save(stream)
    parsed = parse_document_bytes("研究.docx", stream.getvalue())
    assert "# 研究结论" in parsed["content"] and "正文证据" in parsed["content"]
    html = parse_document_bytes("页面.html", b"<h1>Title</h1><p>Evidence</p><script>secret()</script>")
    assert "# Title" in html["content"] and "secret()" not in html["content"]


@pytest.mark.parametrize("url", ["http://127.0.0.1/a", "http://169.254.169.254/a", "file:///etc/passwd"])
def test_web_import_blocks_nonpublic_targets(client, url):
    result = client.post("/api/v1/kb/urls", json={"url": url}).json()
    assert result["code"] != 0
