import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import src.integration.mcp_client as mcp_client_module
from src.core.database import Database
from src.core.repository import Repository
from src.integration.mcp_client import MCPServiceManager


def test_stdio_mcp_probe_initializes_and_lists_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "mcp.db"))
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
                "serverInfo": {"name": "pytest-mcp", "version": "1.0"},
            },
        })
    elif message.get("id") == 2 and message.get("method") == "tools/list":
        write_message({
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "name": "quote_lookup",
                        "description": "读取行情快照",
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
        })
    elif message.get("id") == 2 and message.get("method") == "tools/call":
        assert message.get("params", {}).get("name") == "quote_lookup"
        assert message.get("params", {}).get("arguments", {}).get("symbol") == "600519"
        write_message({
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [{"type": "text", "text": "贵州茅台 价格 1688.00"}],
                "isError": False,
            },
        })
        break
"""
    manager = MCPServiceManager(Repository(Database(tmp_path / "mcp.db")))
    try:
        created = manager.create(
            {
                "name": "pytest-mcp",
                "service_type": "测试",
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-c", server_script],
                "timeout_seconds": 3,
                "enabled": True,
            }
        )
        result = manager.test(created["server_id"])
        call_result = manager.call_tool(created["server_id"], "quote_lookup", {"symbol": "600519"})
        listed = manager.list()[0]
    finally:
        Database.reset_instance()
        config_module._SETTINGS = None

    assert result["success"] is True
    assert result["tool_count"] == 1
    assert result["tools"][0]["name"] == "quote_lookup"
    assert call_result["success"] is True
    assert call_result["transport_success"] is True
    assert call_result["content"][0]["text"] == "贵州茅台 价格 1688.00"
    assert listed["status"] == "connected"
    assert listed["tool_count"] == 1
    assert listed["last_probe"]["tools"][0]["name"] == "quote_lookup"
    assert listed["last_call"]["tool_name"] == "quote_lookup"


def test_mcp_probe_failure_is_structured_and_updates_status(tmp_path, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "mcp-failure.db"))
    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))
    import src.core.config as config_module

    config_module._SETTINGS = None
    Database.reset_instance()
    manager = MCPServiceManager(Repository(Database(tmp_path / "mcp-failure.db")))
    try:
        created = manager.create(
            {
                "name": "invalid-mcp",
                "transport": "stdio",
                "command": str(tmp_path / "missing-mcp-command.exe"),
                "enabled": True,
            }
        )
        result = manager.test(created["server_id"])
        sse_created = manager.create(
            {
                "name": "sse-mcp",
                "transport": "sse",
                "url": "http://127.0.0.1:9/mcp",
                "enabled": True,
            }
        )
        sse_result = manager.call_tool(sse_created["server_id"], "quote_lookup", {})
        listed = next(item for item in manager.list() if item["server_id"] == created["server_id"])
    finally:
        Database.reset_instance()
        config_module._SETTINGS = None

    assert result["success"] is False
    assert result["error"]
    assert listed["status"] == "failed"
    assert listed["last_probe"]["success"] is False
    assert sse_result["success"] is False
    assert "SSE" in sse_result["error"]


def test_mcp_tool_failure_enters_cooldown_and_can_be_reset(tmp_path, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "mcp-cooldown.db"))
    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))
    import src.core.config as config_module

    config_module._SETTINGS = None
    Database.reset_instance()
    call_count = 0

    def failing_transport(
        transport: str,
        config: dict[str, object],
        tool_name: str,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        raise RuntimeError(f"transport failed: {transport}/{tool_name}/{len(arguments)}")

    monkeypatch.setattr(mcp_client_module, "_call_transport", failing_transport)
    manager = MCPServiceManager(Repository(Database(tmp_path / "mcp-cooldown.db")))
    try:
        created = manager.create(
            {
                "name": "cooldown-mcp",
                "transport": "stdio",
                "command": sys.executable,
                "failure_cooldown_seconds": 60,
                "enabled": True,
            }
        )
        first = manager.call_tool(created["server_id"], "quote_lookup", {"symbol": "600519"})
        second = manager.call_tool(created["server_id"], "quote_lookup", {"symbol": "600519"})
        listed = manager.list()[0]
        reset = manager.enable(created["server_id"], True)
        third = manager.call_tool(created["server_id"], "quote_lookup", {"symbol": "000001"})
    finally:
        Database.reset_instance()
        config_module._SETTINGS = None

    assert first["success"] is False
    assert first["transport_success"] is False
    assert first["short_circuited"] is False
    assert first["failure_count"] == 1
    assert second["success"] is False
    assert second["short_circuited"] is True
    assert second["failure_count"] == 1
    assert second["retry_after_seconds"] > 0
    assert call_count == 2
    assert listed["cooldown"] is True
    assert listed["failure_count"] == 1
    assert listed["last_failure_reason"].startswith("transport failed")
    assert reset["cooldown"] is False
    assert reset["failure_count"] == 0
    assert third["success"] is False
    assert third["short_circuited"] is False
    assert third["failure_count"] == 1


def test_http_mcp_probe_and_tool_call_use_session(tmp_path, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "mcp-http.db"))
    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))
    import src.core.config as config_module

    config_module._SETTINGS = None
    Database.reset_instance()
    requests_seen: list[tuple[str, str]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            method = str(payload.get("method") or "")
            requests_seen.append((method, self.headers.get("Mcp-Session-Id", "")))
            if method == "initialize":
                body = {
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "pytest-http-mcp", "version": "1.0"},
                    },
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Mcp-Session-Id", "pytest-session")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode("utf-8"))
                return
            if method == "notifications/initialized":
                self.send_response(202)
                self.end_headers()
                return
            if method == "tools/list":
                body = {
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {
                        "tools": [
                            {
                                "name": "quote_lookup",
                                "description": "读取行情快照",
                                "inputSchema": {"type": "object"},
                            }
                        ]
                    },
                }
            elif method == "tools/call":
                body = {
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": "HTTP 行情 3123.45"}],
                        "isError": False,
                    },
                }
            else:
                self.send_error(404)
                return
            encoded = json.dumps(body).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, _format, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    manager = MCPServiceManager(Repository(Database(tmp_path / "mcp-http.db")))
    try:
        created = manager.create(
            {
                "name": "pytest-http-mcp",
                "service_type": "测试",
                "transport": "http",
                "url": f"http://127.0.0.1:{server.server_port}/mcp",
                "timeout_seconds": 3,
                "enabled": True,
            }
        )
        probe = manager.test(created["server_id"])
        call_result = manager.call_tool(created["server_id"], "quote_lookup", {"symbol": "000001"})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        Database.reset_instance()
        config_module._SETTINGS = None

    assert probe["success"] is True
    assert probe["tool_count"] == 1
    assert call_result["success"] is True
    assert call_result["content"][0]["text"] == "HTTP 行情 3123.45"
    assert requests_seen[0] == ("initialize", "")
    assert ("tools/list", "pytest-session") in requests_seen
    assert ("tools/call", "pytest-session") in requests_seen
