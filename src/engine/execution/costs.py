"""Cumulative per-order fees and adverse, limit-safe slippage."""

from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode

from .config import effective_policy

CATEGORIES = ("commission", "tax", "transfer_fee", "other_fee")


def money(value: float | Decimal, precision: int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP)


def order_fee(policy: dict[str, Any], turnover: float, buy: bool, day: str, prior: dict[str, Any] | None = None):
    """Charge incremental amounts; minimum commission applies once to the external order."""
    if turnover < 0:
        raise BusinessError(ErrorCode.INVALID_PARAM, "成交金额不能为负")
    cfg = effective_policy(policy, day)
    state = dict(prior or {})
    if turnover == 0:
        return dict.fromkeys((*CATEGORIES, "total"), 0.0), state
    if state and state.get("buy") != buy:
        raise BusinessError(ErrorCode.INVALID_PARAM, "同一外部订单不能改变买卖方向")
    state["buy"] = buy
    amount = Decimal(str(turnover))
    rates = {
        "commission": cfg["buy_commission_rate" if buy else "sell_commission_rate"],
        "tax": cfg["buy_tax_rate" if buy else "sell_tax_rate"],
        "transfer_fee": cfg["transfer_rate"],
        "other_fee": cfg["other_fee_rate"],
    }
    result = {}
    for key, rate in rates.items():
        accumulated = Decimal(str(state.get("raw_" + key, "0"))) + amount * Decimal(str(rate))
        target = max(accumulated, Decimal(str(cfg["minimum_commission"]))) if key == "commission" else accumulated
        target = money(target, int(cfg["fee_precision"]))
        result[key] = float(target - Decimal(str(state.get("paid_" + key, "0"))))
        state["raw_" + key], state["paid_" + key] = str(accumulated), str(target)
    result["total"] = float(sum(Decimal(str(result[key])) for key in CATEGORIES))
    return result, state


def slipped_price(base: float, buy: bool, policy: dict[str, Any], limit: float | None = None) -> float | None:
    mode = policy["slippage_mode"]
    direction = Decimal(1 if buy else -1)
    raw, tick = Decimal(str(base)), Decimal(str(policy["tick_size"]))
    delta = (
        raw * Decimal(str(policy["slippage_rate"]))
        if mode == "ratio"
        else tick * Decimal(str(policy["slippage_ticks"]))
        if mode == "ticks"
        else Decimal(0)
    )
    price = raw + direction * delta
    if mode == "ticks" or policy["round_prices"]:
        price = (price / tick).to_integral_value(rounding=ROUND_CEILING if buy else ROUND_FLOOR) * tick
    if price <= 0 or limit is not None and (price > Decimal(str(limit)) if buy else price < Decimal(str(limit))):
        return None
    return float(price)


def affordable_quantity(cash: float, maximum: int, lot: int, price: float, policy, day, prior=None) -> int:
    low, high = 0, max(0, maximum // lot)
    while low < high:
        middle = (low + high + 1) // 2
        turnover = middle * lot * price
        fees, _ = order_fee(policy, turnover, True, day, prior)
        if turnover + fees["total"] <= cash:
            low = middle
        else:
            high = middle - 1
    return low * lot


def split_fees(total: dict[str, float], allocations: dict[str, int], precision: int) -> dict[str, dict[str, float]]:
    """Allocate each rounded category exactly; deterministic final sleeve takes the remainder."""
    keys = sorted(key for key, amount in allocations.items() if amount > 0)
    result: dict[str, dict[str, float]] = {key: {} for key in keys}
    quantity = sum(allocations.values())
    for category in CATEGORIES:
        remaining = Decimal(str(total[category]))
        for index, key in enumerate(keys):
            part = (
                remaining
                if index == len(keys) - 1
                else min(remaining, money(Decimal(str(total[category])) * allocations[key] / quantity, precision))
            )
            result[key][category] = float(part)
            remaining -= part
    for value in result.values():
        value["total"] = float(sum(Decimal(str(value[key])) for key in CATEGORIES))
    return result
