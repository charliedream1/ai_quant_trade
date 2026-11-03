"""OpenAI-compatible chat client backed by configured local model profiles."""

from __future__ import annotations

import os
import time
from typing import Any

import requests

from src.core.crypto import legacy_plaintext_secret
from src.core.env_file import resolve_env_value
from src.core.exceptions import BusinessError, ErrorCode
from src.core.llm_config import llm_config
from src.core.network_policy import network_session
from src.core.redaction import redact_text
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso

from .model_calls import call_model

DEFAULT_SYSTEM_PROMPT = llm_config()["system_prompt"]


class LLMClient:
    def __init__(self, repo: Repository | None = None, session: requests.Session | None = None) -> None:
        self.repo = repo or Repository()
        self.session = session or network_session()

    def complete(
        self,
        prompt: str,
        purpose: str = "问答",
        *,
        history: list[dict[str, str]] | None = None,
        model_id: int | None = None,
        reasoning_effort: str | None = None,
        image_paths: list[str] | None = None,
        enable_thinking: bool | None = None,
        max_output_tokens: int | None = None,
        timeout_seconds: float | None = None,
        max_output_chars: int | None = None,
    ) -> dict[str, Any]:
        try:
            config = self._select_config(model_id)
            if timeout_seconds is not None:
                if timeout_seconds <= 0:
                    raise BusinessError(ErrorCode.INVALID_PARAM, "模型截止时间必须为正数")
                config = {**config, "timeout_seconds": min(float(config.get("timeout_seconds") or 60), timeout_seconds)}
            if max_output_tokens is not None:
                if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 131072:
                    raise BusinessError(ErrorCode.INVALID_PARAM, "模型输出预算不合法")
                config = {
                    **config,
                    "max_tokens": min(max_output_tokens, _bounded_int(config.get("max_tokens"), 1200, 1, 131072)),
                }
        except BusinessError:
            if os.environ.get("ALL_IN_ONE_DATA_MODE", "").lower() != "mock":
                raise
            return {
                "model": "mock-llm",
                "text": f"测试模式回答：{str(prompt).strip()[:160]}",
                "duration_ms": 0,
                "usage": {},
                "purpose": purpose,
            }
        messages = [{"role": "system", "content": config.get("system_prompt") or DEFAULT_SYSTEM_PROMPT}]
        messages.extend((history or [])[-20:])
        user_content: str | list[dict[str, Any]] = str(prompt).strip()
        if image_paths:
            user_content = [{"type": "text", "text": str(prompt).strip()}]
            user_content.extend({"type": "image_url", "image_url": {"url": path}} for path in image_paths)
        messages.append({"role": "user", "content": user_content})  # type: ignore[list-item]
        started = time.perf_counter()
        try:
            options = {"enable_thinking": enable_thinking} if enable_thinking is not None else {}
            result = self._request(config, messages, reasoning_effort=reasoning_effort, **options)
            if max_output_chars is not None and len(str(result.get("text") or "")) > max_output_chars:
                raise BusinessError(ErrorCode.INVALID_PARAM, "模型正文超过输出预算")
        except Exception as exc:
            self._record_usage(
                config, success=False, duration_ms=round((time.perf_counter() - started) * 1000), error=exc
            )
            raise
        self._record_usage(config, success=True, duration_ms=int(result.get("duration_ms") or 0), error=None)
        result["purpose"] = purpose
        return result

    def test_config(self, config: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        test_config = dict(config, temperature=0, max_tokens=16)
        try:
            result = self._request(
                test_config,
                [
                    {"role": "system", "content": llm_config()["connectivity_system"]},
                    {"role": "user", "content": llm_config()["connectivity_prompt"]},
                ],
            )
        except Exception as exc:
            self._record_usage(
                config, success=False, duration_ms=round((time.perf_counter() - started) * 1000), error=exc
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000)
        self._record_usage(config, success=True, duration_ms=duration_ms, error=None)
        return {
            "success": True,
            "duration_ms": duration_ms,
            "model": result["model"],
            "summary": result["text"][:120],
            **{
                name: result.get(name)
                for name in ("api_backend", "rate_limit_wait_ms", "request_duration_ms", "retry_count")
            },
        }

    def _select_config(self, model_id: int | None) -> dict[str, Any]:
        if model_id:
            selected = self.repo.get("llm_models", int(model_id))
            if not selected.get("enabled"):
                raise BusinessError(ErrorCode.LLM_ERROR, "所选大模型配置未启用")
            return selected
        row = self.repo.db.query_one(
            "SELECT * FROM llm_models WHERE enabled = 1 "
            "ORDER BY is_default DESC, CASE level WHEN 'fast' THEN 0 ELSE 1 END, id DESC LIMIT 1"
        )
        if not row:
            raise BusinessError(ErrorCode.LLM_ERROR, "请先在“系统配置 > 模型管理”中添加并启用大模型")
        return row

    def _request(
        self,
        config: dict[str, Any],
        messages: list[dict[str, Any]],
        *,
        reasoning_effort: str | None = None,
        enable_thinking: bool | None = None,
    ) -> dict[str, Any]:
        return call_model(
            config,
            messages,
            self._resolve_api_key(config),
            self.session,
            self.repo,
            reasoning_effort=reasoning_effort,
            enable_thinking=enable_thinking,
        )

    def _record_usage(self, config: dict[str, Any], success: bool, duration_ms: int, error: Exception | None) -> None:
        model_id = config.get("id") or config.get("model_id")
        if not model_id:
            return
        status = "success" if success else "failed"
        error_text = "" if success else redact_text(str(error or ""))[:500]
        now = utc_now_iso()
        self.repo.db.execute(
            """
            UPDATE llm_models
            SET call_count = COALESCE(call_count, 0) + 1,
                success_count = COALESCE(success_count, 0) + ?,
                failure_count = COALESCE(failure_count, 0) + ?,
                total_duration_ms = COALESCE(total_duration_ms, 0) + ?,
                last_duration_ms = ?,
                last_called_at = ?,
                last_status = ?,
                last_error = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                1 if success else 0,
                0 if success else 1,
                int(max(duration_ms, 0)),
                int(max(duration_ms, 0)),
                now,
                status,
                error_text,
                now,
                int(model_id),
            ),
        )

    @staticmethod
    def _resolve_api_key(config: dict[str, Any]) -> str:
        env_name = str(config.get("api_key_env") or "").strip()
        if env_name:
            value = resolve_env_value(env_name)
            if not value:
                raise BusinessError(ErrorCode.LLM_ERROR, f"环境变量 {env_name} 未配置")
            return value
        return legacy_plaintext_secret(str(config.get("api_key") or ""))


def _bounded_int(value: Any, fallback: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = fallback
    return min(max(number, minimum), maximum)
