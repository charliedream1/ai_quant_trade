import sys

import src.integration.mcp_client as mcp_client_module
from src.core.database import Database
from src.core.fts import FTSService
from src.core.repository import Repository
from src.integration.mcp_client import MCPServiceManager
from src.integration.remote_sources.service import RemoteSourceService


def test_remote_source_mcp_list_search_fetch_and_import(tmp_path, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "remote.db"))
    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))
    import src.core.config as config_module

    config_module._SETTINGS = None
    Database.reset_instance()
    server_script = """
import json
import sys

def read_message():
    first = sys.stdin.buffer.readline()
    if not first:
        return None
    if first.lower().startswith(b"content-length:"):
        length = int(first.split(b":", 1)[1].strip())
        while sys.stdin.buffer.readline().strip():
            pass
        body = sys.stdin.buffer.read(length)
    else:
        body = first.strip()
    return json.loads(body.decode("utf-8"))

def write_message(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\\n")
    sys.stdout.flush()

while True:
    message = read_message()
    if message is None:
        break
    if message.get("id") == 1:
        write_message({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "pytest-remote-source", "version": "1.0"},
            },
        })
    elif message.get("id") == 2 and message.get("method") == "tools/list":
        write_message({
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {"name": "list_nodes", "description": "列出文档", "inputSchema": {"type": "object"}},
                    {"name": "search", "description": "搜索文档", "inputSchema": {"type": "object"}},
                    {"name": "fetch_doc", "description": "获取文档", "inputSchema": {"type": "object"}},
                ]
            },
        })
        break
    elif message.get("id") == 2 and message.get("method") == "tools/call":
        params = message.get("params", {})
        name = params.get("name")
        if name == "list_nodes":
            payload = {
                "items": [
                    {
                        "id": "doc-001",
                        "title": "动量因子研究",
                        "summary": "趋势市场中的动量因子观察",
                        "type": "markdown",
                        "updated_at": "2026-10-01",
                    }
                ],
                "total": 1,
            }
        elif name == "search":
            payload = {
                "documents": [
                    {"document_id": "doc-001", "name": "动量因子研究", "description": "搜索命中"}
                ],
                "total": 1,
            }
        else:
            payload = {
                "document": {
                    "id": "doc-001",
                    "title": "动量因子研究",
                    "markdown": "# 动量因子研究\\n\\n动量因子在趋势市场中更稳定。",
                    "type": "markdown",
                }
            }
        write_message({
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "structuredContent": payload,
                "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                "isError": False,
            },
        })
        break
"""
    repo = Repository(Database(tmp_path / "remote.db"))
    try:
        mcp = MCPServiceManager(repo)
        mcp_row = mcp.create(
            {
                "name": "pytest-remote-mcp",
                "service_type": "测试",
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-c", server_script],
                "timeout_seconds": 3,
                "enabled": True,
            }
        )
        service = RemoteSourceService(repo)
        source = service.create(
            {
                "name": "测试知识源",
                "type": "custom",
                "mcp_server_id": mcp_row["server_id"],
                "token": "secret-token",
            }
        )
        source_id = source["source_id"]

        probe = service.test(source_id)
        listed = service.documents(source_id)
        searched = service.documents(source_id, keyword="动量")
        imported = service.pull(source_id, {"remote_doc_id": "doc-001"})
        repeated = service.pull(source_id, {"remote_doc_id": "doc-001"})
        shaped = service.list()[0]
        local_doc = repo.get("kb_documents", imported["local_doc_id"])
        chunk_count = repo.db.scalar(
            "SELECT COUNT(*) FROM kb_document_chunks WHERE doc_id = ?",
            (imported["local_doc_id"],),
        )
        cached = repo.db.query_one(
            "SELECT * FROM remote_docs_cache WHERE source_id = ? AND remote_id = ?",
            (source_id, "doc-001"),
        )
        fts_rows = FTSService(repo.db).search_kb("动量")
    finally:
        Database.reset_instance()
        config_module._SETTINGS = None

    assert probe["success"] is True
    assert probe["capabilities"] == ["list", "search", "fetch"]
    assert listed["items"][0]["remote_doc_id"] == "doc-001"
    assert listed["items"][0]["imported"] is False
    assert searched["items"][0]["title"] == "动量因子研究"
    assert imported["success_count"] == 1
    assert imported["chunk_count"] >= 1
    assert repeated["skipped_count"] == 1
    assert local_doc["content"].startswith("# 动量因子研究")
    assert chunk_count >= 1
    assert cached and cached["local_path"]
    assert fts_rows[0]["title"] == "动量因子研究"
    assert fts_rows[0]["chunk_id"]
    assert shaped["mcp_server_id"] == mcp_row["server_id"]
    assert shaped["config"]["token"] == "***"


def test_remote_source_sync_imports_current_listing(tmp_path, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "remote-sync.db"))
    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))
    import src.core.config as config_module

    config_module._SETTINGS = None
    Database.reset_instance()

    def fake_call_transport(
        transport: str,
        config: dict[str, object],
        tool_name: str,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        if tool_name == "list_nodes":
            payload = {
                "items": [
                    {"id": "sync-001", "title": "远程均值回归", "summary": "均值回归资料"},
                    {"id": "sync-002", "title": "远程波动率", "summary": "波动率资料"},
                ],
                "total": 2,
            }
        else:
            remote_id = str(arguments.get("remote_doc_id") or arguments.get("document_id") or "")
            payload = {
                "document": {
                    "id": remote_id,
                    "title": f"批量资料 {remote_id}",
                    "markdown": f"# 批量资料 {remote_id}\n\n均值回归与波动率同步验证。",
                }
            }
        return {
            "result": {
                "structuredContent": payload,
                "content": [],
                "isError": False,
            }
        }

    monkeypatch.setattr(mcp_client_module, "_call_transport", fake_call_transport)
    repo = Repository(Database(tmp_path / "remote-sync.db"))
    try:
        mcp = MCPServiceManager(repo)
        mcp_row = mcp.create(
            {
                "name": "sync-remote-mcp",
                "transport": "stdio",
                "command": sys.executable,
                "enabled": True,
            }
        )
        service = RemoteSourceService(repo)
        source = service.create(
            {
                "name": "同步知识源",
                "type": "custom",
                "mcp_server_id": mcp_row["server_id"],
            }
        )
        source_id = source["source_id"]

        synced = service.sync(source_id, {"folder": "research", "category_id": 0, "limit": 5})
        repeated = service.sync(source_id, {"folder": "research", "limit": 5})
        fts_rows = FTSService(repo.db).search_kb("波动率同步验证")
        source_row = repo.get("remote_sources", source_id)
    finally:
        Database.reset_instance()
        config_module._SETTINGS = None

    assert synced["scanned_count"] == 2
    assert synced["success_count"] == 2
    assert synced["skipped_count"] == 0
    assert synced["failed_count"] == 0
    assert synced["imported"][0]["remote_doc_id"] == "sync-001"
    assert synced["imported"][0]["chunk_count"] >= 1
    assert repeated["success_count"] == 0
    assert repeated["skipped_count"] == 2
    assert fts_rows[0]["title"].startswith("批量资料")
    assert fts_rows[0]["chunk_id"]
    assert source_row["status"] == "connected"
    assert source_row["last_sync_at"]
