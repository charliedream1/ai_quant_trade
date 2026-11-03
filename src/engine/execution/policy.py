"""Honest capability checks and dated execution constraints shared by engines."""

from datetime import datetime
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo

from src.core.exceptions import BusinessError, ErrorCode

from .config import cost_config, resolve_costs


def policy_for(payload: dict[str, Any], legacy: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("_cost_policy"):
        payload["_cost_policy"] = resolve_costs(payload.get("execution_costs"), legacy)
    return payload["_cost_policy"]


def capability_gaps(history: dict[str, list[dict[str, Any]]], policy: dict[str, Any]) -> list[str]:
    gaps = []
    rows = [row for values in history.values() for row in values]
    if not rows or any(
        not isinstance(row.get("trading_status"), dict)
        or blocked_reason(row, True, policy, str(row.get("date") or row.get("timestamp"))[:10])
        in {"invalid_trading_status", "trading_status_not_available_before_session"}
        for row in rows
    ):
        gaps.append("缺少逐日历史交易状态；未证明完整停牌/涨跌停规则")
    if any("corporate_actions" not in row for row in rows):
        gaps.append("缺少逐日权益事件确认；未包含分红送股账户账本")
    elif any(row.get("corporate_actions") for row in rows):
        gaps.append("区间含权益事件，当前费用回测未实现完整公司行为账本")
    if gaps and policy["validation_mode"] == "strict":
        raise BusinessError(ErrorCode.DATA_SOURCE_ERROR, "严格执行校验阻断：" + "；".join(gaps))
    return gaps


def blocked_reason(row: dict[str, Any], buy: bool, policy: dict[str, Any], day: str) -> str:
    status = row.get("trading_status") or {}
    if status:
        required = {"suspended", "tradable", "limit_up", "limit_down", "available_at"}
        if not required <= set(status) or any(not isinstance(status[k], bool) for k in required - {"available_at"}):
            return "invalid_trading_status"
        # Date-only disclosure is insufficient evidence for execution earlier in that session.
        try:
            observed = datetime.fromisoformat(str(status["available_at"]))
            zone = ZoneInfo(policy.get("timezone", cost_config()["defaults"]["timezone"]))
            observed = observed.replace(tzinfo=zone) if observed.tzinfo is None else observed.astimezone(zone)
            cutoff = datetime.fromisoformat(
                day + "T" + policy.get("session_open_time", cost_config()["defaults"]["session_open_time"])
            ).replace(tzinfo=zone)
            if observed > cutoff:
                return "trading_status_not_available_before_session"
        except (ValueError, TypeError):
            return "invalid_trading_status"
    if status.get("suspended") or not status.get("tradable", True):
        return "not_tradable"
    if buy and status.get("limit_up") or not buy and status.get("limit_down"):
        return "price_limit"
    return ""


def capacity(past: list[dict[str, Any]], policy: dict[str, Any], requested: int) -> int:
    if policy["max_participation"] >= 1:
        return requested
    values = [float(row.get("volume") or 0) for row in past[-int(policy["liquidity_window"]) :]]
    values = [value for value in values if isfinite(value) and value >= 0]
    if not values:
        return 0
    lot = int(policy["lot_size"])
    return int(sum(values) / len(values) * policy["max_participation"]) // lot * lot
