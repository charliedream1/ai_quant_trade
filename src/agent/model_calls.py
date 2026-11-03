"""Shared attempts, local quotas and deadline-aware retries for all API backends."""

import math
import time
from email.utils import parsedate_to_datetime
from typing import Any

import requests
from loguru import logger

from src.core.exceptions import BusinessError, ErrorCode
from src.core.llm_config import llm_config
from src.core.network_policy import validate_url
from src.core.repository import Repository

from .model_backends import ModelRequestError, sdk_request
from .model_budget import CallBudget
from .model_options import model_options
from .model_rate_limit import ModelRateLimiter


def call_model(
    config: dict,
    messages: list[dict[str, Any]],
    key: str,
    session: requests.Session,
    repo: Repository,
    *,
    reasoning_effort: str | None = None,
    enable_thinking: bool | None = None,
) -> dict:
    cfg = {**config, **model_options(config)}
    base = str(cfg.get("base_url") or "").strip().rstrip("/")
    validate_url(base)
    cfg["base_url"] = base
    timeout = float(cfg.get("timeout_seconds") or llm_config()["defaults"]["timeout_seconds"])
    budget = CallBudget(timeout)
    model = str(cfg.get("model_name") or "").strip()
    if not model:
        raise BusinessError(ErrorCode.INVALID_PARAM, "大模型名称不能为空")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": cfg.get("temperature", llm_config()["defaults"]["temperature"]),
        "max_tokens": cfg.get("max_tokens") or llm_config()["defaults"]["max_tokens"],
        "stream": False,
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    if enable_thinking is not None:
        payload["enable_thinking"] = enable_thinking
    limiter = ModelRateLimiter(repo.db.db_path, cfg)
    total_wait = 0.0
    request_ms = 0.0
    for attempt in range(cfg["max_retries"] + 1):
        try:
            with limiter.permit(budget) as wait_ms:
                total_wait += wait_ms
                start = time.monotonic()
                try:
                    body = (
                        _http(cfg, payload, key, session, budget)
                        if cfg["api_backend"] == "http"
                        else sdk_request(cfg, payload, key, session, budget)
                    )
                finally:
                    request_ms += (time.monotonic() - start) * 1000
            budget.remaining()
            result = _response(body)
            result["model"] = result["model"] or model
            return {
                **result,
                "duration_ms": round((time.monotonic() - budget.started) * 1000),
                "api_backend": cfg["api_backend"],
                "rate_limit_wait_ms": round(total_wait),
                "request_duration_ms": round(request_ms),
                "retry_count": attempt,
            }
        except ModelRequestError as exc:
            statuses = llm_config()["retry"]["statuses"]
            if attempt >= cfg["max_retries"] or (exc.status_code is not None and exc.status_code not in statuses):
                raise BusinessError(
                    ErrorCode.LLM_ERROR, f"模型接口请求失败（HTTP {exc.status_code or '连接/超时'}）"
                ) from None
            delay = _retry_delay(exc.retry_after, attempt)
            logger.info(
                "模型请求重试 | model_id={} attempt={} status={} wait_seconds={:.2f}",
                cfg.get("id"),
                attempt + 1,
                exc.status_code,
                delay,
            )
            budget.wait(delay)
    raise RuntimeError("Unreachable request state")


def _http(cfg, payload, key, session, budget):
    base = cfg["base_url"]
    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    remaining = budget.remaining()
    try:
        response = session.post(
            url,
            headers=headers,
            json={**payload, **cfg["extra_body"]},
            allow_redirects=False,
            timeout=(min(llm_config()["defaults"]["connect_seconds"], remaining), remaining),
        )
        response.raise_for_status()
        if response.status_code >= 300:
            raise ModelRequestError(response.status_code)
        return response.json()
    except requests.HTTPError as exc:
        raw = exc.response
        raise ModelRequestError(
            raw.status_code if raw is not None else None, raw.headers.get("Retry-After") if raw is not None else None
        ) from None
    except (requests.Timeout, requests.ConnectionError):
        raise ModelRequestError(None) from None
    except ValueError:
        raise BusinessError(ErrorCode.LLM_ERROR, "模型响应不是有效JSON") from None


def _response(body):
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise BusinessError(ErrorCode.LLM_ERROR, "大模型响应缺少choices[0].message.content") from None
    if isinstance(content, list):
        content = "".join(str(item.get("text") or "") for item in content if isinstance(item, dict))
    if not str(content or "").strip():
        raise BusinessError(ErrorCode.LLM_ERROR, "大模型返回了空回答")
    return {"model": str(body.get("model") or ""), "text": str(content).strip(), "usage": body.get("usage") or {}}


def _retry_delay(header: str | None, attempt: int) -> float:
    policy = llm_config()["retry"]
    if header:
        try:
            value = float(header)
        except ValueError:
            try:
                value = parsedate_to_datetime(header).timestamp() - time.time()
            except (ValueError, TypeError, OverflowError):
                value = -1
        if math.isfinite(value) and value >= 0:
            return value
    return min(policy["maximum_seconds"], policy["base_seconds"] * (2**attempt))
