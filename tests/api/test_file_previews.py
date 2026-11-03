"""Shared file routes must preserve originals, enforce read-only formats and keep RAG in sync."""

import io

import pytest
from docx import Document

from src.core.repository import Repository
from src.documents.service import FilePreviewService
from src.documents.store import PreviewStore


def upload(client, name, content):
    result = client.post("/api/v1/file-previews/uploads", files={"file": (name, content)}).json()
    assert result["code"] == 0, result
    return result["data"]


def test_markdown_save_reopen_conflict_and_history(client):
    original = "# 量化笔记\n\n原始正文。".encode()
    row = upload(client, "研究笔记.md", original)
    assert row["editable"] and row["content"].startswith("# 量化")
    path = "/api/v1/file-previews/" + row["id"]
    saved = client.put(
        path + "/markdown", json={"revision": row["revision"], "content": "# 新版\n\n更新后的正文。"}
    ).json()
    assert saved["code"] == 0
    assert client.get(path).json()["data"]["content"] == "# 新版\n\n更新后的正文。"
    conflict = client.put(path + "/markdown", json={"revision": row["revision"], "content": "过时修改"}).json()
    assert conflict["code"] == 1007
    assert client.get(path + "/raw").content == "# 新版\n\n更新后的正文。".encode()
    backup = PreviewStore().directory(row["id"]) / "versions" / (row["revision"] + ".md")
    assert backup.read_bytes() == original
    assert client.get(path + "/view").status_code == 200
    assert "Markdown源码" in client.get(path + "/view").text


@pytest.mark.parametrize("name,content", [("说明.txt", b"read only"), ("report.html", b"<h1>read only</h1>")])
def test_non_markdown_formats_cannot_be_edited(client, name, content):
    row = upload(client, name, content)
    response = client.put(
        f"/api/v1/file-previews/{row['id']}/markdown", json={"revision": row["revision"], "content": "changed"}
    ).json()
    assert response["code"] == 1002
    assert client.get(f"/api/v1/file-previews/{row['id']}/raw").content == content


def test_knowledge_markdown_updates_original_text_chunks_and_search(client):
    content = "# 初始标题\n\n初始词条甲乙丙。".encode()
    data = client.post("/api/v1/kb/documents", files={"file": ("knowledge.md", content)}).json()["data"]
    row = client.post(f"/api/v1/file-previews/knowledge/{data['doc_id']}").json()["data"]
    assert row["id"] == data["original_file_id"]
    text = "# 保存后标题\n\n新版术语丁戊己，量化风控需要控制集中度。"
    result = client.put(
        f"/api/v1/file-previews/{row['id']}/markdown", json={"revision": row["revision"], "content": text}
    ).json()
    assert result["code"] == 0, result
    detail = client.get(f"/api/v1/kb/documents/{data['doc_id']}").json()["data"]
    assert detail["content"] == text and "丁戊己" in detail["chunks"][0]["content"]
    assert client.get("/api/v1/kb/search", params={"keyword": "丁戊己"}).json()["data"]["items"]
    assert not client.get("/api/v1/kb/search", params={"keyword": "甲乙丙"}).json()["data"]["items"]


def test_original_word_persists_and_office_is_readonly(client):
    stream = io.BytesIO()
    document = Document()
    document.add_heading("中文策略报告", 0)
    document.add_paragraph("原始Word包含段落及表格，应当保留原件。")
    document.add_table(rows=2, cols=2).cell(0, 0).text = "收益"
    document.save(stream)
    result = client.post("/api/v1/kb/documents", files={"file": ("策略报告.docx", stream.getvalue())}).json()
    assert result["code"] == 0, result
    row = client.post(f"/api/v1/file-previews/knowledge/{result['data']['doc_id']}").json()["data"]
    assert row["kind"] == "office" and not row["editable"]
    assert client.get(f"/api/v1/file-previews/{row['id']}/raw").content == stream.getvalue()
    denied = client.put(
        f"/api/v1/file-previews/{row['id']}/markdown", json={"revision": row["revision"], "content": "No"}
    ).json()
    assert denied["code"] == 1002


def test_legacy_records_do_not_claim_originals_and_notes_share_revision(client):
    response = client.post("/api/v1/kb/documents", json={"title": "旧Word提取文本", "content": "历史正文"}).json()[
        "data"
    ]
    row = client.post(f"/api/v1/file-previews/knowledge/{response['doc_id']}").json()["data"]
    assert row["legacy"] and not row["editable"] and row["source"] == "knowledge_text"
    note = client.post("/api/v1/kb/notes", json={"title": "原生Markdown笔记", "content": "初始正文"}).json()["data"]
    first = FilePreviewService().knowledge(note["doc_id"])
    second = FilePreviewService().knowledge(note["doc_id"])
    assert first["id"] == second["id"] and first["editable"] and not first["legacy"]


@pytest.mark.parametrize(
    "path", ["../README.md", ".env", "data/all_in_one.db", "egs/config.yaml", "C:/Windows/win.ini"]
)
def test_project_preview_refuses_unscoped_or_private_files(client, path):
    assert client.post("/api/v1/file-previews/project", json={"path": path}).json()["code"] != 0


def test_actual_readme_can_open_but_protected_task_markdown_is_readonly(client, monkeypatch, tmp_path):
    from src.documents import access

    row = client.post("/api/v1/file-previews/project", json={"path": "README.md"}).json()
    assert row["code"] == 0 and row["data"]["kind"] == "markdown"
    (tmp_path / "docs").mkdir()
    path = tmp_path / "docs/task-fixture.md"
    path.write_text("protected fixture", encoding="utf-8")
    monkeypatch.setattr(access, "PROJECT_ROOT", tmp_path)
    assert not access.can_edit_project(path)


def test_invalid_ids_fake_office_and_mime_mismatch_fail_cleanly(client):
    assert client.get("/api/v1/file-previews/not-a-uuid").json()["code"] == 1002
    for name, content in (
        ("fake.docx", b"not zip"),
        ("fake.doc", b"not ole"),
        ("fake.pdf", b"not pdf"),
        ("fake.png", b"not image"),
    ):
        assert client.post("/api/v1/file-previews/uploads", files={"file": (name, content)}).json()["code"] == 1002


def test_deleted_knowledge_record_does_not_leave_accessible_original(client):
    result = client.post("/api/v1/kb/documents", files={"file": ("memo.md", b"# Original")}).json()["data"]
    # Model an existing removed record without calling a file-deletion route in this test.
    Repository().delete("kb_documents", result["doc_id"])
    assert client.get(f"/api/v1/file-previews/{result['original_file_id']}").json()["code"] == 1004


def test_failed_save_rolls_back_original_derived_content_and_search(client, monkeypatch):
    result = client.post("/api/v1/kb/documents", files={"file": ("rollback.md", "原文词条甲乙".encode())}).json()[
        "data"
    ]
    service = FilePreviewService()
    row = service.knowledge(result["doc_id"])

    def fail_manifest(*args):
        raise OSError("fixture persistence failure")

    monkeypatch.setattr(service.store, "save", fail_manifest)
    with pytest.raises(OSError, match="fixture persistence failure"):
        service.save_markdown(row["id"], row["revision"], "不能提交的新正文丙丁")
    restored = service.detail(row["id"])
    assert restored["revision"] == row["revision"] and restored["content"] == "原文词条甲乙"
    assert client.get(f"/api/v1/kb/documents/{result['doc_id']}").json()["data"]["content"] == "原文词条甲乙"
    assert not client.get("/api/v1/kb/search", params={"keyword": "丙丁"}).json()["data"]["items"]


def test_cross_site_browser_cannot_register_or_write_files(client):
    denied = client.post(
        "/api/v1/file-previews/project", json={"path": "README.md"}, headers={"Origin": "https://untrusted.invalid"}
    ).json()
    assert denied["code"] == 403
    row = upload(client, "origin.md", b"# Original")
    path = f"/api/v1/file-previews/{row['id']}/markdown"
    payload = {"revision": row["revision"], "content": "changed"}
    assert client.put(path, json=payload, headers={"Origin": "null"}).json()["code"] == 403
    assert client.get(f"/api/v1/file-previews/{row['id']}/raw").content == b"# Original"
    assert client.put(path, json=payload, headers={"Origin": "http://testserver"}).json()["code"] == 0
