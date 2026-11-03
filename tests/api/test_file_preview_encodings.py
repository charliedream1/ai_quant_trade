"""Windows text encodings and byte limits remain correct through editable file routes."""

from src.documents.config import preview_config


def test_gb18030_markdown_reads_and_saves_as_utf8(client):
    source = "# 旧编码笔记\n\n中文资料正常显示。"
    result = client.post("/api/v1/file-previews/uploads", files={"file": ("中文.md", source.encode("gb18030"))}).json()
    assert result["code"] == 0, result
    row = result["data"]
    assert row["content"] == source
    text = "# UTF-8笔记\n\n已更新中文。"
    assert (
        client.put(
            f"/api/v1/file-previews/{row['id']}/markdown", json={"revision": row["revision"], "content": text}
        ).json()["code"]
        == 0
    )
    assert client.get(f"/api/v1/file-previews/{row['id']}/raw").content == text.encode("utf-8")


def test_text_limit_counts_utf8_bytes_without_corrupting_chinese(client, monkeypatch):
    monkeypatch.setitem(preview_config()["limits"], "max_text_bytes", 10)
    content = "中文中文中文".encode()
    result = client.post("/api/v1/file-previews/uploads", files={"file": ("large.md", content)}).json()
    assert result["code"] == 0, result
    row = result["data"]
    assert row["preview_truncated"] and not row["editable"]
    assert len(row["content"].encode("utf-8")) <= 10 and "\ufffd" not in row["content"]
    assert client.get(f"/api/v1/file-previews/{row['id']}/raw").content == content
