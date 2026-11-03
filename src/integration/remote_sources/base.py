"""MCP-backed remote knowledge source adapter."""

from __future__ import annotations

import json
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import json_loads
from src.integration.mcp_client import MCPServiceManager

DEFAULT_TOOL_MAP = {
    "list": "list_nodes",
    "search": "search",
    "fetch": "fetch_doc",
}
REMOTE_ACTIONS = frozenset({"list", "search", "fetch", "import"})
SENSITIVE_CONFIG_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "headers",
        "client_secret",
        "credential",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "token",
    }
)


class RemoteSourceAdapter:
    """Translate a source configuration into MCP tool calls."""

    def __init__(self, source_row: dict[str, Any], manager: MCPServiceManager | None = None) -> None:
        self.source_row = source_row
        self.manager = manager or MCPServiceManager()
        config = json_loads(source_row.get("conn_config"), {})
        self.config = config if isinstance(config, dict) else {}
        self.server_id = self._server_id()
        self.tool_map = self._tool_map()

    def probe(self) -> dict[str, Any]:
        return self.manager.test(self.server_id)

    def call(self, action: str, values: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        if action not in REMOTE_ACTIONS - {"import"}:
            raise BusinessError(ErrorCode.INVALID_PARAM, f"远程知识源不允许执行动作：{action}")
        tool_name = self.tool_map[action]
        arguments = self._arguments(action, values)
        result = self.manager.call_tool(self.server_id, tool_name, arguments)
        if not result.get("transport_success"):
            raise BusinessError(ErrorCode.DOCUMENT_SOURCE_ERROR, str(result.get("error") or "远程工具调用失败"))
        if not result.get("success"):
            raise BusinessError(ErrorCode.DOCUMENT_SOURCE_ERROR, str(result.get("error") or "远程工具返回业务错误"))
        return self.decode_result(result), result

    def public_config(self) -> dict[str, Any]:
        return redact_config(self.config)

    def capabilities(self, probe: dict[str, Any]) -> list[str]:
        advertised = {str(item.get("name") or "") for item in probe.get("tools", []) if isinstance(item, dict)}
        return [action for action in ("list", "search", "fetch") if self.tool_map[action] in advertised]

    def _server_id(self) -> int:
        nested = self.config.get("mcp")
        nested_config = nested if isinstance(nested, dict) else {}
        raw_value = (
            self.config.get("mcp_server_id")
            or self.config.get("mcp_service_id")
            or self.config.get("server_id")
            or nested_config.get("server_id")
        )
        if raw_value is None:
            raise BusinessError(
                ErrorCode.CONFIG_DEPENDENCY,
                "远程知识源缺少有效的 mcp_server_id 配置。",
            )
        try:
            value = int(str(raw_value))
        except (TypeError, ValueError) as exc:
            raise BusinessError(
                ErrorCode.CONFIG_DEPENDENCY,
                "远程知识源缺少有效的 mcp_server_id 配置。",
            ) from exc
        if value <= 0:
            raise BusinessError(ErrorCode.CONFIG_DEPENDENCY, "远程知识源的 mcp_server_id 必须大于 0。")
        return value

    def _tool_map(self) -> dict[str, str]:
        configured = self.config.get("tool_map") or self.config.get("tools") or {}
        if not isinstance(configured, dict):
            raise BusinessError(ErrorCode.INVALID_PARAM, "远程知识源的 tool_map 必须是 JSON 对象。")
        result = dict(DEFAULT_TOOL_MAP)
        for action in DEFAULT_TOOL_MAP:
            value = configured.get(action) or self.config.get(f"{action}_tool")
            if value:
                result[action] = str(value).strip()
        if any(not value for value in result.values()):
            raise BusinessError(ErrorCode.INVALID_PARAM, "远程知识源工具映射不能包含空工具名。")
        return result

    def _arguments(self, action: str, values: dict[str, Any]) -> dict[str, Any]:
        base_arguments = self.config.get("base_arguments") or {}
        if not isinstance(base_arguments, dict):
            raise BusinessError(ErrorCode.INVALID_PARAM, "远程知识源的 base_arguments 必须是 JSON 对象。")
        arguments = dict(base_arguments)
        mappings = self.config.get("argument_map") or {}
        action_mapping = mappings.get(action, {}) if isinstance(mappings, dict) else {}
        if not isinstance(action_mapping, dict):
            raise BusinessError(ErrorCode.INVALID_PARAM, f"远程知识源的 {action} argument_map 必须是 JSON 对象。")
        for key, value in values.items():
            if value is None or value == "":
                continue
            target_key = str(action_mapping.get(key) or key)
            arguments[target_key] = value
        return arguments

    @staticmethod
    def decode_result(result: dict[str, Any]) -> Any:
        structured = result.get("structured_content")
        if structured is not None:
            return structured
        texts = [
            str(item.get("text") or "")
            for item in result.get("content", [])
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        text = "\n".join(item for item in texts if item).strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text


def normalize_documents(payload: Any) -> dict[str, Any]:
    """Normalize list/search tool payloads to the platform document shape."""
    source = _unwrap_collection(payload)
    if isinstance(source, dict):
        source = [source] if _document_id(source) else []
    if not isinstance(source, list):
        raise BusinessError(ErrorCode.DOCUMENT_SOURCE_ERROR, "远程文档列表不是数组或文档对象。")

    items: list[dict[str, Any]] = []
    for raw_item in source:
        if not isinstance(raw_item, dict):
            continue
        remote_id = _document_id(raw_item)
        if not remote_id:
            continue
        items.append(
            {
                "remote_doc_id": remote_id,
                "title": str(
                    raw_item.get("title") or raw_item.get("name") or raw_item.get("display_name") or remote_id
                ),
                "summary": str(raw_item.get("summary") or raw_item.get("description") or ""),
                "type": str(raw_item.get("type") or raw_item.get("doc_type") or raw_item.get("mime_type") or ""),
                "updated_at": str(raw_item.get("updated_at") or raw_item.get("modified_at") or ""),
                "folder": str(raw_item.get("folder") or raw_item.get("path") or ""),
                "url": str(raw_item.get("url") or raw_item.get("web_url") or ""),
            }
        )
    total = payload.get("total") if isinstance(payload, dict) else None
    return {
        "items": items,
        "total": int(total) if isinstance(total, int | float) else len(items),
        "next_cursor": str(payload.get("next_cursor") or payload.get("next") or "")
        if isinstance(payload, dict)
        else "",
    }


def normalize_document(payload: Any, remote_doc_id: str) -> dict[str, Any]:
    """Normalize a fetch tool payload to one document with Markdown content."""
    source = _unwrap_document(payload)
    if isinstance(source, str):
        source = {"content": source}
    if not isinstance(source, dict):
        raise BusinessError(ErrorCode.DOCUMENT_SOURCE_ERROR, "远程文档正文不是对象或文本。")
    content = source.get("content") or source.get("markdown") or source.get("text") or source.get("body")
    if isinstance(content, list):
        content = "\n".join(str(item.get("text") or item) if isinstance(item, dict) else str(item) for item in content)
    if not isinstance(content, str) or not content.strip():
        raise BusinessError(ErrorCode.DOCUMENT_SOURCE_ERROR, f"远程文档 {remote_doc_id} 没有可导入的正文。")
    normalized_id = _document_id(source) or remote_doc_id
    return {
        "remote_doc_id": normalized_id,
        "title": str(source.get("title") or source.get("name") or normalized_id),
        "summary": str(source.get("summary") or source.get("description") or content[:200]),
        "content": content,
        "type": str(source.get("type") or source.get("doc_type") or "远程文档"),
        "updated_at": str(source.get("updated_at") or source.get("modified_at") or ""),
        "url": str(source.get("url") or source.get("web_url") or ""),
    }


def redact_config(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {str(item_key): redact_config(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact_config(item, key) for item in value]
    if key.lower() in SENSITIVE_CONFIG_KEYS:
        return "***"
    return value


def _unwrap_collection(payload: Any) -> Any:
    current = payload
    for key in ("data", "result", "documents", "nodes", "items", "results"):
        if isinstance(current, dict) and key in current:
            candidate = current[key]
            if isinstance(candidate, list | dict):
                current = candidate
                if key in {"documents", "nodes", "items", "results"}:
                    break
    return current


def _unwrap_document(payload: Any) -> Any:
    current = payload
    for key in ("data", "result", "document", "doc", "item"):
        if isinstance(current, dict) and key in current:
            candidate = current[key]
            if isinstance(candidate, dict | str):
                current = candidate
    return current


def _document_id(value: dict[str, Any]) -> str:
    for key in ("remote_doc_id", "remote_id", "document_id", "doc_id", "node_id", "token", "id"):
        candidate = value.get(key)
        if candidate is not None and str(candidate).strip():
            return str(candidate).strip()
    return ""
