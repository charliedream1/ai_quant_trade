"""Shared model configuration application service for REST and Gradio."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from src.agent import LLMClient
from src.core.crypto import mask_secret
from src.core.env_file import default_key_name, save_env_value, validate_import_name
from src.core.network_policy import validate_url
from src.core.redaction import redact
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso


def list_models():
    rows = Repository().list("llm_models", order_by="is_default DESC, id DESC")
    return [_shape(row) for row in rows]


def get_model(model_id: int):
    return _shape(Repository().get("llm_models", model_id))


def create_model(payload: dict[str, Any]):
    values = _validated_values(payload, creating=True)
    repo = Repository()
    now = utc_now_iso()
    has_default = repo.db.query_one(
        "SELECT id FROM llm_models WHERE enabled = 1 AND is_default = 1 AND level = ?", (values["level"],)
    )
    row = repo.insert(
        "llm_models",
        {
            **values,
            "purpose": json.dumps(payload.get("purpose") or [], ensure_ascii=False),
            "is_default": 0 if has_default else 1,
            "enabled": 1,
            "remark": str(payload.get("remark") or ""),
            "created_at": now,
            "updated_at": now,
        },
    )
    return _shape(row)


def update_model(model_id: int, payload: dict[str, Any]):
    values = _validated_values(payload, creating=False)
    values["updated_at"] = utc_now_iso()
    for key in ("enabled", "remark"):
        if key in payload:
            values[key] = payload[key]
    if payload.get("enabled") is False:
        values["is_default"] = 0
    if "purpose" in payload:
        values["purpose"] = json.dumps(payload["purpose"] or [], ensure_ascii=False)
    return _shape(Repository().update("llm_models", model_id, values))


def delete_model(model_id: int):
    Repository().delete("llm_models", model_id)
    return None


def set_default(model_id: int, payload: dict[str, Any]):
    repo = Repository()
    level = str(payload.get("level") or "fast")
    repo.db.execute("UPDATE llm_models SET is_default = 0 WHERE level = ?", (level,))
    repo.update("llm_models", model_id, {"is_default": 1, "enabled": 1, "level": level, "updated_at": utc_now_iso()})
    fast = repo.db.query_one("SELECT id FROM llm_models WHERE level = 'fast' AND is_default = 1")
    deep = repo.db.query_one("SELECT id FROM llm_models WHERE level = 'deep' AND is_default = 1")
    return {
        "fast_default_model_id": fast["id"] if fast else None,
        "deep_default_model_id": deep["id"] if deep else None,
    }


def test_model(model_id: int):
    row = Repository().get("llm_models", model_id)
    return LLMClient().test_config(row)


def chat(payload: dict[str, Any]):
    messages = payload.get("messages") or []
    question = str(payload.get("question") or "").strip()
    history = [
        {"role": str(item.get("role") or "user"), "content": str(item.get("content") or "")}
        for item in messages
        if isinstance(item, dict) and item.get("role") in {"user", "assistant"}
    ]
    return LLMClient().complete(
        question,
        purpose="悬浮问答",
        history=history,
        model_id=int(payload["model_id"]) if payload.get("model_id") else None,
    )


def _validated_values(payload: dict[str, Any], creating: bool) -> dict[str, Any]:
    values: dict[str, Any] = {}
    text_fields = ("name", "base_url", "model_name", "api_key_env", "system_prompt", "level")
    for key in text_fields:
        if key in payload or creating:
            values[key] = str(payload.get(key) or "").strip()
    if creating and (not all(values.get(key) for key in ("name", "base_url", "model_name"))):
        raise ValueError("配置名称、Base URL 和模型名称不能为空")
    if "base_url" in values:
        validate_url(values["base_url"])
        parsed = urlparse(values["base_url"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Base URL 必须是有效的 HTTP(S) 地址")
        values["base_url"] = values["base_url"].rstrip("/")
    if "api_key" in payload or creating:
        api_key = str(payload.get("api_key") or "").strip()
        if api_key:
            env_name = values.get("api_key_env") or default_key_name(values.get("name") or "MODEL")
            validate_import_name(env_name)
            values["api_key_env"] = env_name
        values["api_key"] = ""
    if "temperature" in payload or creating:
        temperature = float(payload.get("temperature", 0.2))
        if not 0 <= temperature <= 2:
            raise ValueError("temperature 必须在 0 到 2 之间")
        values["temperature"] = temperature
    if "max_tokens" in payload or creating:
        max_tokens = int(payload.get("max_tokens", 1200))
        if not 1 <= max_tokens <= 131072:
            raise ValueError("max_tokens 必须在 1 到 131072 之间")
        values["max_tokens"] = max_tokens
    if "timeout_seconds" in payload or creating:
        timeout = float(payload.get("timeout_seconds", 60))
        if not 3 <= timeout <= 600:
            raise ValueError("超时时间必须在 3 到 600 秒之间")
        values["timeout_seconds"] = timeout
    if creating and values.get("level") not in {"fast", "deep"}:
        values["level"] = "fast"
    elif "level" in values and values["level"] not in {"fast", "deep"}:
        raise ValueError("层级必须是 fast 或 deep")
    if payload.get("api_key"):
        save_env_value(values["api_key_env"], str(payload["api_key"]).strip())
    return values


def _shape(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["model_id"] = result["id"]
    result["api_key"] = mask_secret(result.get("api_key") or "")
    result["purpose"] = json_loads(result.get("purpose"), [])
    result["enabled"] = bool(result.get("enabled"))
    result["is_default"] = bool(result.get("is_default"))
    result["provider"] = "openai-compatible"
    call_count = int(result.get("call_count") or 0)
    result["avg_duration_ms"] = (
        round(float(result.get("total_duration_ms") or 0) / call_count, 2) if call_count else 0.0
    )
    return redact(result)
