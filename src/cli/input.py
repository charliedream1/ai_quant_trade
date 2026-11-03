"""Strict YAML/JSON inputs and deep, typed request overrides."""

import json
import re
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

from .errors import CliError


def load_file(filename: str, maximum: int) -> dict[str, Any]:
    try:
        text = sys.stdin.read(maximum + 1) if filename == "-" else Path(filename).read_text(encoding="utf-8-sig")
        if len(text.encode("utf-8")) > maximum:
            raise CliError("请求文件超过配置大小上限")
        value = json.loads(text) if Path(filename).suffix.lower() == ".json" else yaml.safe_load(text)
        if not isinstance(value, dict):
            raise CliError("请求文件必须是对象")
        json.dumps(value, allow_nan=False)
        return value
    except (OSError, UnicodeError, ValueError, TypeError, yaml.YAMLError) as exc:
        raise CliError("请求文件格式无效；只支持 JSON 兼容的 UTF-8 YAML/JSON") from exc


def decode(value: Any, kind: str) -> Any:
    if not isinstance(value, str):
        return value
    try:
        if kind == "int":
            return int(value)
        if kind == "float":
            return float(value)
        if kind == "bool":
            if value.lower() not in {"true", "false", "1", "0"}:
                raise ValueError("bool")
            return value.lower() in {"true", "1"}
        if kind == "json":
            try:
                return json.loads(value)
            except ValueError:
                return value
        return value
    except ValueError as exc:
        raise CliError(f"参数值类型错误：{kind}") from exc


def put(payload: dict[str, Any], key: str, value: Any) -> None:
    names = key.split(".")
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) for name in names):
        raise CliError("覆盖字段名不合法或使用了保留字段")
    target = payload
    for name in names[:-1]:
        if name not in target:
            target[name] = {}
        if not isinstance(target[name], dict):
            raise CliError("无法在标量或列表内部覆盖子字段")
        target = target[name]
    target[names[-1]] = value


def merged(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        result[key] = (
            merged(result[key], value) if isinstance(result.get(key), dict) and isinstance(value, dict) else value
        )
    return result


def build_request(options: Any, args: Any, definition: dict[str, Any], maximum: int) -> dict[str, Any]:
    files = [
        value
        for value in (
            options.file if not definition.get("upload") else None,
            options.params_file,
            options.message_file,
            options.question_file,
        )
        if value
    ]
    if files.count("-") > 1:
        raise CliError("标准输入只能被一个输入参数使用")
    payload = load_file(options.file, maximum) if options.file and not definition.get("upload") else {}
    if options.params_file:
        destination = (
            "default_params" if args._command_name in {"strategy create", "strategy examples import"} else "params"
        )
        payload[destination] = merged(payload.get(destination, {}), load_file(options.params_file, maximum))
    for override in options.sets or []:
        key, separator, text = override.partition("=")
        if not separator:
            raise CliError("--set 格式必须为 字段=值")
        try:
            value = json.loads(text)
        except ValueError:
            value = text
        put(payload, key, value)
    fields = {**definition.get("fields", {}), **definition.get("query", {})}
    explicit = {key: decode(value, fields[key]) for key, value in vars(args).items() if key in fields}
    for field, option in definition.get("global_fields", {}).items():
        value = getattr(options, option, None)
        if value is not None:
            explicit[field] = decode(value, fields[field])
    payload = merged(payload, explicit)
    payload = {key: decode(value, fields[key]) if key in fields else value for key, value in payload.items()}
    if "overwrite" in fields and options.overwrite is not None:
        payload["overwrite"] = bool(options.overwrite)
    if "server_workflow" in payload:
        payload["workflow_path"] = payload.pop("server_workflow")
    if set(payload).intersection(definition.get("unsupported_query", [])):
        raise CliError("当前后端尚未实现该筛选条件，不能静默忽略")
    for key, filename in (
        ("code", options.code_file),
        ("message", options.message_file),
        ("question", options.question_file),
    ):
        if filename:
            try:
                payload[key] = (
                    sys.stdin.read(maximum + 1) if filename == "-" else Path(filename).read_text(encoding="utf-8-sig")
                )
            except (OSError, UnicodeError) as exc:
                raise CliError(f"无法读取 {key} 文件") from exc
    allowed = set(fields) | ({"code"} if options.code_file else set())
    if definition.get("special") != "api" and set(payload) - allowed:
        raise CliError("命令不支持字段：" + ", ".join(sorted(set(payload) - allowed)))
    validate(payload, maximum)
    path = str(definition.get("path") or "")
    ids = []
    for key, kind in definition.get("positions", {}).items():
        value = getattr(args, key)
        if kind == "int" and value <= 0:
            raise CliError("对象 ID 必须为正数")
        ids.append(str(value))
        path = path.replace("{" + key + "}", quote(str(value), safe=""))
    if "{session_id}" in path:
        if not options.session_id or options.session_id <= 0:
            raise CliError("请用 --session-id 指定已创建的会话")
        path = path.replace("{session_id}", str(options.session_id))
        ids.append(str(options.session_id))
    elif options.session_id is not None and "session_id" in fields:
        payload["session_id"] = options.session_id
    query = {key: value for key, value in payload.items() if key in definition.get("query", {})}
    body = {key: value for key, value in payload.items() if key not in query}
    if "symbols" in body and not isinstance(body["symbols"], list):
        body["symbols"] = [value.strip() for value in str(body["symbols"]).split(",") if value.strip()]
    return {
        "method": definition.get("method", "GET"),
        "path": path,
        "query": query,
        "body": body,
        "confirm_id": ids[-1] if ids else str(body.get("config_id") or body.get("session_id") or "all"),
    }


def validate(payload: dict[str, Any], maximum: int) -> None:
    try:
        if len(json.dumps(payload, allow_nan=False).encode("utf-8")) > maximum:
            raise CliError("请求超过大小上限")
        for name in ("start_date", "end_date"):
            if name in payload:
                date.fromisoformat(str(payload[name]))
        if payload.get("start_date") and payload.get("end_date") and payload["start_date"] > payload["end_date"]:
            raise CliError("开始日期不能晚于结束日期")
    except (ValueError, TypeError) as exc:
        raise CliError("请求包含无效日期、NaN 或不支持的类型") from exc
