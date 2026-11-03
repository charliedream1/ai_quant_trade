import sys

from src.integration.mcp_client import MCPServiceManager


def test_remote_source_routes_call_mcp_and_import_local_document(client, keyword_model):
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
                "serverInfo": {"name": "api-remote-source", "version": "1.0"},
            },
        })
    elif message.get("method") == "tools/list":
        write_message({
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "tools": [
                    {"name": "list_nodes", "description": "list", "inputSchema": {"type": "object"}},
                    {"name": "search", "description": "search", "inputSchema": {"type": "object"}},
                    {"name": "fetch_doc", "description": "fetch", "inputSchema": {"type": "object"}},
                ]
            },
        })
    elif message.get("method") == "tools/call":
        name = message.get("params", {}).get("name")
        if name == "fetch_doc":
            payload = {
                "id": "api-doc-001",
                "title": "API 远程资料",
                "content": "# API 远程资料\\n\\n用于路由回归。",
            }
        else:
            payload = {"items": [{"id": "api-doc-001", "title": "API 远程资料"}], "total": 1}
        write_message({
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                "isError": False,
            },
        })
        break
"""
    mcp = MCPServiceManager().create(
        {
            "name": "api-remote-mcp",
            "service_type": "测试",
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-c", server_script],
            "timeout_seconds": 3,
            "enabled": True,
        }
    )
    source = client.post(
        "/api/v1/kb/remote-sources",
        json={
            "name": "API 远程源",
            "type": "custom",
            "mcp_server_id": mcp["server_id"],
        },
    ).json()
    assert source["code"] == 0
    source_id = source["data"]["source_id"]

    tested = client.post(f"/api/v1/kb/remote-sources/{source_id}/test").json()
    listed = client.get(
        f"/api/v1/kb/remote-sources/{source_id}/documents",
        params={"keyword": "资料"},
    ).json()
    pulled = client.post(
        f"/api/v1/kb/remote-sources/{source_id}/pull",
        json={"remote_doc_id": "api-doc-001"},
    ).json()
    synced = client.post(
        f"/api/v1/kb/remote-sources/{source_id}/sync",
        json={"keyword": "资料", "limit": 5},
    ).json()
    local_note = client.post(
        "/api/v1/kb/notes",
        json={"title": "本地路由回归", "content": "本地路由回归资料。"},
    ).json()
    remote_search = client.get(
        "/api/v1/kb/search",
        params={"keyword": "路由回归", "scope": "remote"},
    ).json()
    local_search = client.get(
        "/api/v1/kb/search",
        params={"keyword": "路由回归", "scope": "local"},
    ).json()
    all_search = client.get(
        "/api/v1/kb/search",
        params={"keyword": "路由回归", "scope": "all"},
    ).json()
    qa = client.post(
        "/api/v1/kb/qa",
        json={"question": "路由回归", "scope": "remote", "top_k": 3},
    ).json()

    assert tested["code"] == 0
    assert tested["data"]["success"] is True
    assert listed["code"] == 0
    assert listed["data"]["items"][0]["remote_doc_id"] == "api-doc-001"
    assert pulled["code"] == 0
    assert pulled["data"]["success_count"] == 1
    assert pulled["data"]["chunk_count"] >= 1
    assert synced["code"] == 0
    assert synced["data"]["scanned_count"] == 1
    assert synced["data"]["skipped_count"] == 1
    assert local_note["code"] == 0
    assert remote_search["code"] == 0
    assert local_search["code"] == 0
    assert all_search["code"] == 0
    assert {item["title"] for item in remote_search["data"]["items"]} == {"API 远程资料"}
    assert {item["source_scope"] for item in remote_search["data"]["items"]} == {"remote"}
    assert {item["source_name"] for item in remote_search["data"]["items"]} == {"API 远程源"}
    assert {item["chunk_id"] for item in remote_search["data"]["items"]}
    assert {item["title"] for item in local_search["data"]["items"]} == {"本地路由回归"}
    assert {item["source_scope"] for item in local_search["data"]["items"]} == {"local"}
    assert {item["source_scope"] for item in all_search["data"]["items"]} == {"local", "remote"}
    assert qa["code"] == 0
    assert {item["source_scope"] for item in qa["data"]["references"]} == {"remote"}
    assert {item["chunk_id"] for item in qa["data"]["references"]}
