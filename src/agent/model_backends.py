"""Ordinary chat completions through SDKs with explicit, controlled transports."""

import importlib
import os
from typing import Any

import httpx
import requests
from openai import OpenAI

from src.core.exceptions import BusinessError, ErrorCode
from src.core.llm_config import llm_config
from src.core.network_policy import validate_url

from .model_budget import CallBudget
from .model_transport import ModelTransport


class ModelRequestError(Exception):
    def __init__(self, status: int | None, retry_after: str | None = None):
        super().__init__("模型接口请求失败")
        self.status_code, self.retry_after = status, retry_after


def sdk_request(config: dict, payload: dict, key: str, session: requests.Session, budget: CallBudget) -> dict[str, Any]:
    base = config["base_url"].rstrip("/")
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")]
    validate_url(base)
    request = {name: value for name, value in payload.items() if name != "enable_thinking"}
    extras = dict(config["extra_body"])
    if "enable_thinking" in payload:
        extras["enable_thinking"] = payload["enable_thinking"]
    request["extra_body"] = extras
    if config["api_backend"] == "litellm" and "/" in request["model"] and not request["model"].startswith("openai/"):
        raise BusinessError(
            ErrorCode.INVALID_PARAM, "当前受控LiteLLM接口支持openai/兼容模型，其他供应商原生传输尚未核验"
        )
    sdk_key = key or llm_config()["interfaces"]["unauthenticated_sdk_key"]
    transport = ModelTransport(session, budget, base)
    with httpx.Client(transport=transport, trust_env=False, follow_redirects=False) as http:
        with OpenAI(
            base_url=base, api_key=sdk_key, http_client=http, max_retries=0, timeout=budget.remaining()
        ) as client:
            try:
                if config["api_backend"] == "openai":
                    result = client.chat.completions.create(**request)
                else:
                    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
                    os.environ.setdefault("LITELLM_LOG", llm_config()["interfaces"]["sdk_log_level"])
                    try:
                        module: Any = importlib.import_module("litellm")
                    except ModuleNotFoundError:
                        raise BusinessError(
                            ErrorCode.CONFIG_DEPENDENCY, "LiteLLM未安装，请安装requirements或启用uv的llm扩展"
                        ) from None
                    module.telemetry = False
                    module.suppress_debug_info = True
                    model = request["model"]
                    request["model"] = model if model.startswith("openai/") else "openai/" + model
                    result = module.completion(
                        **request,
                        api_base=base,
                        api_key=sdk_key,
                        client=client,
                        num_retries=0,
                        max_retries=0,
                        timeout=budget.remaining(),
                        allowed_openai_params=[name for name in ("reasoning_effort",) if name in request],
                        drop_params=False,
                        turn_off_message_logging=True,
                        logger_fn=None,
                        metadata={"mask_input": True, "mask_output": True},
                    )
            except Exception as exc:
                # The SDK must not turn a policy refusal into an automatic retry.
                if transport.refusal is not None:
                    raise transport.refusal from None
                cause: BaseException = exc
                while cause.__cause__ is not None:
                    cause = cause.__cause__
                if isinstance(cause, (ValueError, BusinessError)):
                    raise cause from None
                status = getattr(exc, "status_code", None)
                headers = getattr(getattr(exc, "response", None), "headers", {}) or {}
                if status is None and not isinstance(cause, (httpx.TransportError, requests.RequestException)):
                    raise BusinessError(ErrorCode.LLM_ERROR, "模型SDK拒绝请求，请检查接口与参数配置") from None
                raise ModelRequestError(status, headers.get("retry-after")) from None
    return dict(result.model_dump()) if hasattr(result, "model_dump") else dict(result)
