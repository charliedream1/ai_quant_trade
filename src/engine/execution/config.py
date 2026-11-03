"""Versioned, project-local execution profiles and immutable run resolution."""

import json
import math
from copy import deepcopy
from datetime import date, time
from functools import lru_cache
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode


@lru_cache(maxsize=1)
def cost_config() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/execution_costs.yaml").read_text(encoding="utf-8"))


def resolve_costs(value: dict[str, Any] | None = None, legacy: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg, request = cost_config(), deepcopy({} if value is None else value)
    if not isinstance(request, dict):
        raise BusinessError(ErrorCode.INVALID_PARAM, "执行配置必须为对象")
    profile = str(request.pop("profile", "inherit"))
    if profile not in cfg["profiles"]:
        raise BusinessError(ErrorCode.INVALID_PARAM, "未知执行费用方案")
    base = cfg["profiles"][profile]
    result = {**deepcopy(cfg["defaults"]), **_legacy(legacy or {}), **deepcopy(base["settings"])}
    unknown = set(request) - set(cfg["defaults"])
    if unknown:
        raise BusinessError(ErrorCode.INVALID_PARAM, "未知执行字段：" + ",".join(sorted(unknown)))
    result.update(request)
    _validate(result)
    result.update(
        profile=profile,
        profile_version=cfg["version"],
        verified_at=cfg["verified_at"],
        description=base["description"],
        sources=base.get("sources", []),
        valid_from=base.get("valid_from"),
        schedule=deepcopy(base.get("schedule", [])),
        explicit_fields=sorted(request),
    )
    result["sha256"] = sha256(
        json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    return result


def _legacy(value: dict[str, Any]) -> dict[str, Any]:
    fields = set(cost_config()["defaults"])
    result = {key: item for key, item in value.items() if key in fields and item is not None}
    if value.get("commission_rate") is not None:
        result.update(buy_commission_rate=value["commission_rate"], sell_commission_rate=value["commission_rate"])
    return result


def _validate(value: dict[str, Any]) -> None:
    for key, default in cost_config()["defaults"].items():
        item = value[key]
        if isinstance(default, bool):
            if not isinstance(item, bool):
                raise BusinessError(ErrorCode.INVALID_PARAM, f"{key}必须为布尔值")
        elif isinstance(default, int | float):
            if isinstance(item, bool) or not isinstance(item, int | float) or not math.isfinite(item) or item < 0:
                raise BusinessError(ErrorCode.INVALID_PARAM, f"{key}必须为非负有限数")
            if key in cost_config()["integer_fields"] and int(item) != item:
                raise BusinessError(ErrorCode.INVALID_PARAM, f"{key}必须为整数")
            if key in cost_config()["integer_fields"]:
                value[key] = int(item)
            if key.endswith("_rate") or key == "max_participation":
                if item > 1:
                    raise BusinessError(ErrorCode.INVALID_PARAM, f"{key}应为0至1的小数")
        elif not isinstance(item, str):
            raise BusinessError(ErrorCode.INVALID_PARAM, f"{key}必须为文本")
    if value["lot_size"] < 1 or value["tick_size"] <= 0 or value["liquidity_window"] < 1 or value["fee_precision"] > 8:
        raise BusinessError(ErrorCode.INVALID_PARAM, "成交数量、价位、量能窗口或费用精度无效")
    if value["slippage_mode"] not in {"ratio", "ticks", "none"} or value["validation_mode"] not in {
        "research",
        "strict",
    }:
        raise BusinessError(ErrorCode.INVALID_PARAM, "滑点或校验模式无效")
    if value["commission_includes_regulatory"] and value["other_fee_rate"]:
        raise BusinessError(ErrorCode.INVALID_PARAM, "佣金已包含规费，请清零其他规费或选择佣金不含规费")
    try:
        time.fromisoformat(value["session_open_time"])
        ZoneInfo(value["timezone"])
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise BusinessError(ErrorCode.INVALID_PARAM, "开盘时间或市场时区无效") from exc


def effective_policy(policy: dict[str, Any], day: str) -> dict[str, Any]:
    stamp = str(day)[:10]
    if policy.get("valid_from") and stamp < policy["valid_from"]:
        raise BusinessError(ErrorCode.INVALID_PARAM, "费用方案不覆盖该历史日期，请配置相应生效规则")
    if stamp:
        date.fromisoformat(stamp)
    result = dict(policy)
    for segment in policy.get("schedule", []):
        if segment["from"] <= stamp:
            result.update({k: v for k, v in segment.items() if k != "from" and k not in policy["explicit_fields"]})
    return result
