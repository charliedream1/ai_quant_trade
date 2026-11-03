"""Validated, nonsecret model interface policy shared by every configuration entry."""

import json
from typing import Any

from src.core.llm_config import llm_config
from src.core.network_policy import validate_url
from src.core.redaction import SENSITIVE

FIELDS = ("api_backend", "rpm", "max_concurrency", "wait_on_limit", "quota_group", "max_retries", "extra_body")


def model_options(payload: dict, *, defaults: bool = True) -> dict[str, Any]:
    policy = llm_config()["interfaces"]
    result = {name: policy[name] for name in FIELDS} if defaults else {}
    result.update({name: payload[name] for name in FIELDS if name in payload})
    if "api_backend" in result and result["api_backend"] not in {row[1] for row in policy["choices"]}:
        raise ValueError("不支持的模型调用接口")
    for name, upper in (
        ("rpm", "maximum_rpm"),
        ("max_concurrency", "maximum_concurrency"),
        ("max_retries", "maximum_retries"),
    ):
        if name in result:
            raw = result[name]
            try:
                parsed = int(raw)
            except (ValueError, TypeError, OverflowError):
                raise ValueError(f"{name}必须是范围内的非负整数") from None
            if isinstance(raw, bool) or str(raw).strip() != str(parsed) or not 0 <= parsed <= policy[upper]:
                raise ValueError(f"{name}必须是范围内的非负整数")
            result[name] = parsed
    if "wait_on_limit" in result and type(result["wait_on_limit"]) is not bool:
        if result["wait_on_limit"] in (0, 1):
            result["wait_on_limit"] = bool(result["wait_on_limit"])
        else:
            raise ValueError("wait_on_limit必须是布尔值")
    if "quota_group" in result:
        result["quota_group"] = str(result["quota_group"] or "").strip()
        if len(result["quota_group"]) > policy["group_chars"] or any(ord(c) < 32 for c in result["quota_group"]):
            raise ValueError("共享配额组名称过长或含控制字符")
    if "extra_body" in result:
        body = result["extra_body"]
        if isinstance(body, str):
            body = json.loads(body)
        if not isinstance(body, dict):
            raise ValueError("extra_body必须是JSON对象")
        if set(body) & set(policy["protected_body_keys"]):
            raise ValueError("扩展参数不能覆盖核心调用参数")
        _check_body(body, policy)
        result["extra_body"] = body
    return result


def _check_body(value: Any, policy: dict) -> None:
    if isinstance(value, dict):
        for name, item in value.items():
            if str(name).lower() in policy["secret_body_keys"] or SENSITIVE.search(str(name)):
                raise ValueError("扩展参数不能保存凭据")
            _check_body(item, policy)
    elif isinstance(value, list):
        for item in value:
            _check_body(item, policy)
    elif isinstance(value, str) and "://" in value:
        validate_url(value)


def quota_identity(config: dict) -> str:
    if config.get("quota_group"):
        return "group:" + str(config["quota_group"])
    if config.get("id"):
        return "model:" + str(config["id"])
    # Ad-hoc connectivity checks must share quota without persisting the secret.
    return (
        "endpoint:"
        + str(config.get("base_url"))
        + ":"
        + str(config.get("model_name"))
        + ":"
        + str(config.get("api_key_env") or "")
    )
