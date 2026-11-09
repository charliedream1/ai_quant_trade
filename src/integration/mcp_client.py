"""MCP service configuration and lightweight protocol probes."""

from __future__ import annotations

import json
import shlex
import subprocess
import threading
import time
from datetime import datetime, timezone
from queue import Empty, Queue
from typing import Any
from uuid import uuid4

import requests
from loguru import logger

from src.core.config import get_settings
from src.core.credential_config import preserve_configuration, protect_configuration, resolve_configuration
from src.core.exceptions import BusinessError, ErrorCode
from src.core.network_policy import network_session, validate_url
from src.core.process_env import process_environment
from src.core.redaction import redact
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso

MCP_PROTOCOL_VERSION = "2025-06-18"
DEFAULT_MCP_TIMEOUT_SECONDS = 10.0
MAX_MCP_TIMEOUT_SECONDS = 60.0
DEFAULT_MCP_FAILURE_COOLDOWN_SECONDS = 60.0
MAX_MCP_FAILURE_COOLDOWN_SECONDS = 900.0
MCP_CLIENT_INFO = {"name": "AIQuant", "version": "0.1.0"}


class MCPServiceManager:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()

    def list(self) -> list[dict[str, Any]]:
        rows = self.repo.list("mcp_services", order_by="id DESC")
        for row in rows:
            self._shape(row)
        return rows

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not str(payload.get("name") or "").strip():
            raise ValueError("MCP服务名称不能为空")
        if payload.get("url") or payload.get("endpoint"):
            validate_url(str(payload.get("url") or payload["endpoint"]))
        payload = protect_configuration(payload, uuid4().hex)
        now = utc_now_iso()
        enabled = bool(payload.get("enabled", True))
        row = self.repo.insert(
            "mcp_services",
            {
                "name": payload["name"],
                "service_type": payload.get("service_type") or payload.get("type") or "自定义",
                "transport": payload.get("transport") or "stdio",
                "conn_params": json.dumps(payload, ensure_ascii=False),
                "enabled": 1 if enabled else 0,
                "status": "disconnected",
                "remark": payload.get("remark") or "",
                "created_at": now,
                "updated_at": now,
            },
        )
        return self._shape(row)

    def update(self, server_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        current = json_loads(self.repo.get("mcp_services", server_id).get("conn_params"), {})
        payload = protect_configuration(preserve_configuration(payload, current), uuid4().hex)
        values: dict[str, Any] = {"updated_at": utc_now_iso()}
        for key in ("name", "service_type", "transport", "enabled", "remark"):
            if key in payload:
                values[key] = payload[key]
        if payload:
            values["conn_params"] = json.dumps(payload, ensure_ascii=False)
        if "enabled" in payload and not payload["enabled"]:
            values["status"] = "disconnected"
        elif payload.get("transport") or payload.get("url") or payload.get("command"):
            values["status"] = "disconnected"
        return self._shape(self.repo.update("mcp_services", server_id, values))

    def delete(self, server_id: int) -> None:
        self.repo.delete("mcp_services", server_id)

    def enable(self, server_id: int, enabled: bool) -> dict[str, Any]:
        row = self.repo.get("mcp_services", server_id)
        config = self._connection_config(row)
        return self._shape(
            self.repo.update(
                "mcp_services",
                server_id,
                {
                    "enabled": 1 if enabled else 0,
                    "status": "disconnected",
                    "conn_params": json.dumps(
                        config | {"_failure_state": {}},
                        ensure_ascii=False,
                    ),
                    "updated_at": utc_now_iso(),
                },
            )
        )

    def test(self, server_id: int) -> dict[str, Any]:
        row = self.repo.get("mcp_services", server_id)
        config = self._connection_config(row)
        transport = str(row.get("transport") or config.get("transport") or "stdio").strip().lower()
        cooldown = _failure_snapshot(config.get("_failure_state"))
        if cooldown["active"]:
            remaining = cooldown["remaining_seconds"]
            logger.warning(
                "MCP 服务处于失败冷却中：server_id={} transport={} retry_after={}s",
                server_id,
                transport,
                remaining,
            )
            return {
                "server_id": server_id,
                "transport": transport,
                "success": False,
                "latency_ms": 0.0,
                "tools": [],
                "tool_count": 0,
                "error": f"MCP 服务失败冷却中，约 {remaining} 秒后自动重试。",
                "cooldown": True,
                "short_circuited": True,
                "retry_after_seconds": remaining,
                "failure_count": cooldown["failure_count"],
            }
        started = time.perf_counter()
        logger.info("MCP 服务测试开始：server_id={} transport={}", server_id, transport)
        try:
            result = _probe_transport(transport, config)
            result.update(
                {
                    "server_id": server_id,
                    "transport": transport,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )
            status = "connected" if result.get("success") else "failed"
        except Exception as exc:  # noqa: BLE001
            logger.warning("MCP 服务测试失败：server_id={} transport={} error={}", server_id, transport, exc)
            result = {
                "server_id": server_id,
                "transport": transport,
                "success": False,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "tools": [],
                "error": str(exc),
            }
            status = "failed"
        result = redact(result)
        failure_state = (
            {}
            if result.get("success")
            else _next_failure_state(
                config,
                cooldown,
                str(result.get("error") or "MCP 服务探测失败。"),
            )
        )
        cooldown_after = _failure_snapshot(failure_state)
        result.update(
            {
                "cooldown": cooldown_after["active"],
                "short_circuited": False,
                "retry_after_seconds": cooldown_after["remaining_seconds"],
                "failure_count": cooldown_after["failure_count"],
            }
        )
        logger.info(
            "MCP 服务测试完成：server_id={} transport={} status={} tool_count={}",
            server_id,
            transport,
            status,
            result.get("tool_count", 0),
        )
        self.repo.update(
            "mcp_services",
            server_id,
            {
                "status": status,
                "conn_params": json.dumps(
                    config
                    | {
                        "_last_probe": _probe_snapshot(result),
                        "_failure_state": failure_state,
                    },
                    ensure_ascii=False,
                ),
                "updated_at": utc_now_iso(),
            },
        )
        return redact(result)

    def call_tool(self, server_id: int, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        row = self.repo.get("mcp_services", server_id)
        if not row.get("enabled"):
            raise BusinessError(ErrorCode.MCP_ERROR, "MCP 服务未启用，无法调用工具。")
        name = str(tool_name or "").strip()
        if not name:
            raise BusinessError(ErrorCode.MISSING_PARAM, "MCP 工具名不能为空。")
        if not isinstance(arguments, dict):
            raise BusinessError(ErrorCode.INVALID_PARAM, "MCP 工具参数必须是 JSON 对象。")

        config = self._connection_config(row)
        transport = str(row.get("transport") or config.get("transport") or "stdio").strip().lower()
        cooldown = _failure_snapshot(config.get("_failure_state"))
        if cooldown["active"]:
            remaining = cooldown["remaining_seconds"]
            logger.warning(
                "MCP 工具调用被失败冷却短路：server_id={} transport={} tool={} retry_after={}s",
                server_id,
                transport,
                name,
                remaining,
            )
            return {
                "server_id": server_id,
                "transport": transport,
                "tool_name": name,
                "success": False,
                "transport_success": False,
                "content": [],
                "structured_content": None,
                "is_error": False,
                "error": f"MCP 服务失败冷却中，约 {remaining} 秒后自动重试。",
                "latency_ms": 0.0,
                "cooldown": True,
                "short_circuited": True,
                "retry_after_seconds": remaining,
                "failure_count": cooldown["failure_count"],
            }
        started = time.perf_counter()
        logger.info("MCP 工具调用开始：server_id={} transport={} tool={}", server_id, transport, name)
        try:
            payload = _call_transport(transport, config, name, arguments)
            call_result = _tool_call_result(payload)
            result = {
                "server_id": server_id,
                "transport": transport,
                "tool_name": name,
                "success": call_result["success"],
                "transport_success": True,
                "content": call_result["content"],
                "structured_content": call_result["structured_content"],
                "is_error": call_result["is_error"],
                "error": call_result["error"],
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            status = "connected"
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "MCP 工具调用失败：server_id={} transport={} tool={} error={}",
                server_id,
                transport,
                name,
                exc,
            )
            result = {
                "server_id": server_id,
                "transport": transport,
                "tool_name": name,
                "success": False,
                "transport_success": False,
                "content": [],
                "structured_content": None,
                "is_error": False,
                "error": str(exc),
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            status = "failed"

        result = redact(result)
        failure_state = (
            {}
            if status == "connected"
            else _next_failure_state(
                config,
                cooldown,
                str(result.get("error") or "MCP 工具调用失败。"),
            )
        )
        cooldown_after = _failure_snapshot(failure_state)
        result.update(
            {
                "cooldown": cooldown_after["active"],
                "short_circuited": False,
                "retry_after_seconds": cooldown_after["remaining_seconds"],
                "failure_count": cooldown_after["failure_count"],
            }
        )
        logger.info(
            "MCP 工具调用完成：server_id={} transport={} tool={} status={} success={} latency_ms={}",
            server_id,
            transport,
            name,
            status,
            result["success"],
            result["latency_ms"],
        )
        self.repo.update(
            "mcp_services",
            server_id,
            {
                "status": status,
                "conn_params": json.dumps(
                    config
                    | {
                        "_last_call": _call_snapshot(result),
                        "_failure_state": failure_state,
                    },
                    ensure_ascii=False,
                ),
                "updated_at": utc_now_iso(),
            },
        )
        return redact(result)

    @staticmethod
    def _connection_config(row: dict[str, Any]) -> dict[str, Any]:
        payload = json_loads(row.get("conn_params"), {})
        if not isinstance(payload, dict):
            return {}
        nested = payload.get("config")
        if isinstance(nested, dict):
            merged = dict(nested)
            merged.update(payload)
            return merged
        return payload

    def _shape(self, row: dict[str, Any]) -> dict[str, Any]:
        row["server_id"] = row["id"]
        config = json_loads(row.get("conn_params"), {})
        if not isinstance(config, dict):
            config = {}
        probe = config.pop("_last_probe", {})
        call = config.pop("_last_call", {})
        failure_state = config.pop("_failure_state", {})
        cooldown = _failure_snapshot(failure_state)
        row["config"] = config
        row["enabled"] = bool(row.get("enabled"))
        row["last_probe"] = probe if isinstance(probe, dict) else {}
        row["last_call"] = call if isinstance(call, dict) else {}
        row["tool_count"] = int(row["last_probe"].get("tool_count") or 0)
        row["last_connected_at"] = row["last_probe"].get("checked_at") if row.get("status") == "connected" else None
        row["cooldown"] = cooldown["active"]
        row["cooldown_remaining_seconds"] = cooldown["remaining_seconds"]
        row["failure_count"] = cooldown["failure_count"]
        row["last_failure_at"] = cooldown["last_failure_at"]
        row["last_failure_reason"] = cooldown["last_failure_reason"]
        row["cooldown_until"] = cooldown["cooldown_until"]
        row["conn_params"] = json.dumps(redact(config), ensure_ascii=False)
        row.update(redact(row))
        return row


def _probe_transport(transport: str, config: dict[str, Any]) -> dict[str, Any]:
    config = resolve_configuration(config)
    if transport == "stdio":
        return _probe_stdio(config)
    if transport == "http":
        return _probe_http(config)
    if transport == "sse":
        return _probe_sse(config)
    raise ValueError(f"不支持的 MCP 传输方式：{transport}")


def _call_transport(
    transport: str, config: dict[str, Any], tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    config = resolve_configuration(config)
    if transport == "stdio":
        return _call_stdio(config, tool_name, arguments)
    if transport == "http":
        return _call_http(config, tool_name, arguments)
    if transport == "sse":
        raise ValueError("SSE 当前仅支持可达性检查，暂不支持工具调用。")
    raise ValueError(f"不支持的 MCP 传输方式：{transport}")


def _probe_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    raw_tools = result.get("tools")
    tools: list[Any] = raw_tools if isinstance(raw_tools, list) else []
    return {
        "checked_at": utc_now_iso(),
        "success": bool(result.get("success")),
        "latency_ms": result.get("latency_ms"),
        "tool_count": len(tools),
        "tools": [
            {
                "name": str(item.get("name") or ""),
                "description": str(item.get("description") or ""),
            }
            for item in tools[:50]
            if isinstance(item, dict)
        ],
        "error": str(result.get("error") or ""),
        "warning": str(result.get("warning") or ""),
    }


def _call_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "checked_at": utc_now_iso(),
        "tool_name": str(result.get("tool_name") or ""),
        "success": bool(result.get("success")),
        "transport_success": bool(result.get("transport_success")),
        "latency_ms": result.get("latency_ms"),
        "is_error": bool(result.get("is_error")),
        "error": str(result.get("error") or ""),
    }


def _failure_snapshot(raw_state: Any) -> dict[str, Any]:
    state = raw_state if isinstance(raw_state, dict) else {}
    try:
        failure_count = max(int(state.get("failure_count") or 0), 0)
    except (TypeError, ValueError):
        failure_count = 0
    try:
        cooldown_until_epoch = float(state.get("cooldown_until_epoch") or 0)
    except (TypeError, ValueError):
        cooldown_until_epoch = 0.0
    remaining = max(0.0, cooldown_until_epoch - time.time())
    remaining_seconds = int(remaining + 0.999) if remaining else 0
    return {
        "active": remaining_seconds > 0,
        "remaining_seconds": remaining_seconds,
        "failure_count": failure_count,
        "cooldown_until": str(state.get("cooldown_until") or ""),
        "last_failure_at": str(state.get("last_failure_at") or ""),
        "last_failure_reason": str(state.get("last_failure_reason") or ""),
    }


def _failure_cooldown_seconds(config: dict[str, Any]) -> float:
    raw = config.get("failure_cooldown_seconds") or config.get("cooldown_seconds")
    try:
        configured = float(raw) if raw is not None else DEFAULT_MCP_FAILURE_COOLDOWN_SECONDS
    except (TypeError, ValueError):
        configured = DEFAULT_MCP_FAILURE_COOLDOWN_SECONDS
    return min(max(configured, 1.0), MAX_MCP_FAILURE_COOLDOWN_SECONDS)


def _next_failure_state(
    config: dict[str, Any],
    previous: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    failure_count = previous["failure_count"] + 1
    cooldown_seconds = min(
        _failure_cooldown_seconds(config) * (2 ** max(failure_count - 1, 0)),
        MAX_MCP_FAILURE_COOLDOWN_SECONDS,
    )
    now = time.time()
    cooldown_until_epoch = now + cooldown_seconds
    last_failure_at = utc_now_iso()
    return {
        "failure_count": failure_count,
        "cooldown_seconds": cooldown_seconds,
        "cooldown_until_epoch": cooldown_until_epoch,
        "cooldown_until": _utc_iso_from_epoch(cooldown_until_epoch),
        "last_failure_at": last_failure_at,
        "last_failure_reason": reason[:500],
    }


def _utc_iso_from_epoch(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _probe_stdio(config: dict[str, Any]) -> dict[str, Any]:
    response = _stdio_exchange(config, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = _tools_from_response(response)
    return {"success": True, "tools": tools, "tool_count": len(tools), "error": ""}


def _call_stdio(config: dict[str, Any], tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return _stdio_exchange(
        config,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
    )


def _stdio_exchange(config: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    command = _stdio_command(config)
    timeout = _mcp_timeout(config)
    env = process_environment()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    configured_env = config.get("env")
    if isinstance(configured_env, dict):
        env.update({str(key): str(value) for key, value in configured_env.items()})
    process = subprocess.Popen(
        command,
        cwd=str(get_settings().project_root),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    messages: Queue[dict[str, Any] | None] = Queue()
    reader = threading.Thread(target=_read_stdio_messages, args=(process.stdout, messages), daemon=True)
    reader.start()
    try:
        _write_stdio_message(process, _initialize_request())
        initialize = _wait_for_message(messages, 1, timeout)
        _raise_rpc_error(initialize)
        _write_stdio_message(process, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        _write_stdio_message(process, request)
        message_id = request.get("id")
        if not isinstance(message_id, int):
            raise ValueError("MCP 请求缺少有效的 JSON-RPC id。")
        response = _wait_for_message(messages, message_id, timeout)
        _raise_rpc_error(response)
        return response
    finally:
        _terminate_process(process)


def _probe_http(config: dict[str, Any]) -> dict[str, Any]:
    session, url, headers, timeout = _open_http_session(config)
    try:
        tools_response = session.post(
            url,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers=headers,
            timeout=timeout,
        )
        tools_response.raise_for_status()
        tools_payload = _rpc_payload_from_http(tools_response)
        _raise_rpc_error(tools_payload)
        tools = _tools_from_response(tools_payload)
        return {"success": True, "tools": tools, "tool_count": len(tools), "error": ""}
    finally:
        session.close()


def _call_http(config: dict[str, Any], tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    session, url, headers, timeout = _open_http_session(config)
    try:
        response = session.post(
            url,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = _rpc_payload_from_http(response)
        _raise_rpc_error(payload)
        return payload
    finally:
        session.close()


def _open_http_session(config: dict[str, Any]) -> tuple[requests.Session, str, dict[str, str], float]:
    url = str(config.get("url") or config.get("endpoint") or "").strip()
    if not url:
        raise ValueError("MCP HTTP 配置缺少 url 或 endpoint。")
    timeout = _mcp_timeout(config)
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    configured_headers = config.get("headers")
    if isinstance(configured_headers, dict):
        headers.update({str(key): str(value) for key, value in configured_headers.items()})
    session = network_session()
    try:
        initialize_response = session.post(url, json=_initialize_request(), headers=headers, timeout=timeout)
        initialize_response.raise_for_status()
        initialize = _rpc_payload_from_http(initialize_response)
        _raise_rpc_error(initialize)
        session_id = initialize_response.headers.get("Mcp-Session-Id")
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        session.post(
            url,
            json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            headers=headers,
            timeout=timeout,
        ).raise_for_status()
    except Exception:
        session.close()
        raise
    return session, url, headers, timeout


def _probe_sse(config: dict[str, Any]) -> dict[str, Any]:
    url = str(config.get("url") or config.get("endpoint") or "").strip()
    if not url:
        raise ValueError("MCP SSE 配置缺少 url 或 endpoint。")
    timeout = _mcp_timeout(config)
    headers = {"Accept": "text/event-stream"}
    configured_headers = config.get("headers")
    if isinstance(configured_headers, dict):
        headers.update({str(key): str(value) for key, value in configured_headers.items()})
    with network_session() as session:
        with session.get(url, headers=headers, timeout=timeout, stream=True) as response:
            response.raise_for_status()
    return {
        "success": True,
        "tools": [],
        "tool_count": 0,
        "error": "",
        "warning": "SSE 传输已完成可达性检查，工具枚举需由 SSE 会话适配器继续执行。",
    }


def _stdio_command(config: dict[str, Any]) -> list[str]:
    raw_command = config.get("command") or config.get("cmd")
    if isinstance(raw_command, list):
        command = [str(item) for item in raw_command if str(item).strip()]
    elif raw_command:
        command = shlex.split(str(raw_command), posix=False)
    else:
        command = []
    if not command:
        raise ValueError("MCP stdio 配置缺少 command。")
    raw_args = config.get("args") or []
    if isinstance(raw_args, str):
        raw_args = shlex.split(raw_args, posix=False)
    if not isinstance(raw_args, list):
        raise ValueError("MCP stdio 配置的 args 必须是数组或字符串。")
    return [*command, *(str(item) for item in raw_args)]


def _mcp_timeout(config: dict[str, Any]) -> float:
    raw = config.get("timeout_seconds") or config.get("timeout") or DEFAULT_MCP_TIMEOUT_SECONDS
    return min(max(float(raw), 0.5), MAX_MCP_TIMEOUT_SECONDS)


def _initialize_request() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": MCP_CLIENT_INFO,
        },
    }


def _write_stdio_message(process: subprocess.Popen[bytes], message: dict[str, Any]) -> None:
    if process.stdin is None:
        raise RuntimeError("MCP stdio stdin 不可用。")
    body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    process.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
    process.stdin.flush()


def _read_stdio_messages(stream: Any, messages: Queue[dict[str, Any] | None]) -> None:
    try:
        while True:
            message = _read_stdio_message(stream)
            if message is None:
                messages.put(None)
                return
            messages.put(message)
    except Exception as exc:  # noqa: BLE001
        logger.debug("MCP stdio 消息读取结束：{}", exc)
        messages.put(None)


def _read_stdio_message(stream: Any) -> dict[str, Any] | None:
    first_line = stream.readline()
    if not first_line:
        return None
    if first_line.lower().startswith(b"content-length:"):
        length = int(first_line.split(b":", 1)[1].strip())
        while stream.readline().strip():
            pass
        body = stream.read(length)
    else:
        body = first_line.strip()
    if not body:
        return None
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("MCP 返回消息不是 JSON 对象。")
    return payload


def _wait_for_message(messages: Queue[dict[str, Any] | None], message_id: int, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"MCP 等待响应超时：id={message_id}")
        try:
            message = messages.get(timeout=remaining)
        except Empty as exc:
            raise TimeoutError(f"MCP 等待响应超时：id={message_id}") from exc
        if message is None:
            raise RuntimeError("MCP stdio 服务提前关闭输出。")
        if message.get("id") == message_id:
            return message


def _raise_rpc_error(payload: dict[str, Any]) -> None:
    error = payload.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        message = error.get("message") or "MCP JSON-RPC 调用失败。"
        raise RuntimeError(f"MCP JSON-RPC 错误 {code}: {message}")


def _tools_from_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload.get("result")
    raw_tools = result.get("tools") if isinstance(result, dict) else []
    if not isinstance(raw_tools, list):
        return []
    tools: list[dict[str, Any]] = []
    for item in raw_tools:
        if not isinstance(item, dict):
            continue
        tools.append(
            {
                "name": str(item.get("name") or ""),
                "description": str(item.get("description") or ""),
                "inputSchema": item.get("inputSchema") or {},
            }
        )
    return tools


def _tool_call_result(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError("MCP 工具调用响应缺少 result 对象。")
    raw_content = result.get("content")
    if raw_content is None:
        content: list[Any] = []
    elif isinstance(raw_content, list):
        content = raw_content
    else:
        content = [raw_content]
    is_error = bool(result.get("isError"))
    error = str(result.get("error") or "")
    if is_error and not error:
        error = _content_text(content) or "MCP 工具返回业务错误。"
    return {
        "success": not is_error,
        "content": content,
        "structured_content": result.get("structuredContent"),
        "is_error": is_error,
        "error": error,
    }


def _content_text(content: list[Any]) -> str:
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
            parts.append(str(item["text"]))
    return " ".join(parts).strip()


def _rpc_payload_from_http(response: requests.Response) -> dict[str, Any]:
    text = response.text.strip()
    if not text:
        raise ValueError("MCP HTTP 响应为空。")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
        for line in text.splitlines():
            if line.startswith("data:"):
                try:
                    candidate = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict):
                    payload = candidate
                    break
        if payload is None:
            raise ValueError("MCP HTTP 响应不是 JSON-RPC 或 SSE data 消息。") from None
    if not isinstance(payload, dict):
        raise ValueError("MCP HTTP 响应不是 JSON 对象。")
    return payload


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=1)
