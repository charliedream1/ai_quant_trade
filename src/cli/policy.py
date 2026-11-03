"""Shared operation controls for semantic and generic API commands."""

import re
import sys
from typing import Any
from urllib.parse import unquote

from loguru import logger

from .catalog import commands
from .errors import CliError, ExitCode


def resolve_operation(method: str, path: str) -> tuple[str, dict[str, Any]]:
    if (
        not path.startswith("/")
        or path.startswith("//")
        or "?" in path
        or "#" in path
        or ".." in unquote(path).split("/")
    ):
        raise CliError("只允许已登记的 API 相对路径")
    for name, entry in commands().items():
        pattern = entry.get("path", "")
        for key, kind in entry.get("positions", {}).items():
            pattern = pattern.replace("{" + key + "}", r"[1-9][0-9]*" if kind == "int" else r"[^/]+")
        pattern = re.sub(r"\{[^}]+\}", r"[^/]+", pattern)
        if entry.get("method") == method.upper() and re.fullmatch(pattern, path):
            return name, entry
    raise CliError("操作未登记，请使用 api operations 查看支持范围")


def operation_target(definition: dict[str, Any], path: str, body: dict[str, Any]) -> str:
    identifiers = [
        value
        for field, value in zip(str(definition["path"]).split("/"), path.split("/"), strict=True)
        if field.startswith("{")
    ]
    return identifiers[-1] if identifiers else str(body.get("config_id") or body.get("session_id") or "all")


def check_policy(definition: dict[str, Any], request: dict[str, Any], options: Any, config: dict[str, Any]) -> None:
    if definition.get("disabled"):
        raise CliError(str(definition["disabled"]), ExitCode.UNAVAILABLE)
    if options.market and not definition.get("market"):
        raise CliError("当前命令不支持 --market")
    if options.dry_run:
        return
    live_action = definition.get("live") or (
        request["path"].startswith("/live-configs/")
        and request["method"] != "GET"
        and "risk_controls" in request["body"]
    )
    if live_action and not config.get("allow_live_actions"):
        raise CliError("当前连接上下文未启用实盘启动/恢复/风险调整", ExitCode.UNAVAILABLE)
    if definition.get("confirm") or live_action:
        target = request["confirm_id"]
        if options.yes and options.confirm_id == target:
            return
        if not sys.stdin.isatty():
            raise CliError(f"非交互操作必须使用 --yes --confirm-id {target}")
        logger.warning("请确认 {} {}，输入对象标识 {} 后回车", request["method"], request["path"], target)
        if sys.stdin.readline().strip() != target:
            raise CliError("操作已取消")
