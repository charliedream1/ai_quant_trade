"""MCP server configuration routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.core.exceptions import BusinessError, ErrorCode
from src.integration.mcp_client import MCPServiceManager

router = APIRouter(tags=["模型配置-MCP"], route_class=ValidatedRoute)
JsonBody = Annotated[dict[str, Any], Body()]


@router.get("/mcp-servers")
def list_servers():
    return ok(MCPServiceManager().list())


@router.post("/mcp-servers")
def create_server(payload: JsonBody):
    return ok(MCPServiceManager().create(payload))


@router.put("/mcp-servers/{server_id}")
def update_server(server_id: int, payload: JsonBody):
    return ok(MCPServiceManager().update(server_id, payload))


@router.delete("/mcp-servers/{server_id}")
def delete_server(server_id: int):
    MCPServiceManager().delete(server_id)
    return ok(None)


@router.post("/mcp-servers/{server_id}/enable")
def enable(server_id: int):
    return ok(MCPServiceManager().enable(server_id, True))


@router.post("/mcp-servers/{server_id}/disable")
def disable(server_id: int):
    return ok(MCPServiceManager().enable(server_id, False))


@router.post("/mcp-servers/{server_id}/test")
def test(server_id: int):
    return ok(MCPServiceManager().test(server_id))


@router.post("/mcp-servers/{server_id}/tools/call")
def call_tool(server_id: int, payload: JsonBody):
    tool_name = str(payload.get("name") or payload.get("tool_name") or "").strip()
    if not tool_name:
        raise BusinessError(ErrorCode.MISSING_PARAM, "MCP 工具名不能为空。")
    arguments = payload.get("arguments", {})
    if not isinstance(arguments, dict):
        raise BusinessError(ErrorCode.INVALID_PARAM, "MCP 工具参数必须是 JSON 对象。")
    return ok(MCPServiceManager().call_tool(server_id, tool_name, arguments))
