"""Dated HKD cash-equity execution; historical trading units require explicit evidence."""

from copy import deepcopy
from datetime import date
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT
from src.data.hong_kong import hk_symbol


@lru_cache(maxsize=1)
def hk_execution_config():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/strategies/hong_kong_execution.yaml").read_text(encoding="utf-8"))


def dated_policy(symbol, day, policy):
    if policy.get("market") != "HK":
        raise ValueError("HK instruments require the HK execution profile")
    config = policy.get("hk_rules") or hk_execution_config()
    day = str(day)[:10]
    date.fromisoformat(day)
    if day < config["valid_from"]:
        raise ValueError("HK execution rules do not cover this date")
    canonical = hk_symbol(symbol)
    records = policy.get("instruments", {}).get(canonical, [])
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise ValueError("HK instrument metadata must be a record or list of records")
    eligible = [row for row in records if row.get("from", "") <= day <= row.get("to", "9999-12-31")]
    if not eligible:
        raise ValueError("Provide dated instruments metadata with a board lot for " + canonical)
    row = max(eligible, key=lambda record: record.get("from", ""))
    date.fromisoformat(row["from"])
    if row.get("to"):
        date.fromisoformat(row["to"])
    if type(row.get("lot_size")) is not int or row["lot_size"] <= 0 or not row.get("from") or not row.get("source"):
        raise ValueError("HK instrument metadata requires from, lot_size and source")
    if row.get("currency") != "HKD" or row.get("asset_type") != "stock":
        raise ValueError("This HK execution table supports HKD ordinary equities only; ETF metadata/table required")
    if policy["validation_mode"] == "strict" and row.get("assumption", True):
        raise ValueError("Strict HK execution rejects assumed trading-unit metadata")
    bands = max((item for item in config["tick_tables"] if item["from"] <= day), key=lambda item: item["from"])
    return {
        **policy,
        "currency": "HKD",
        "timezone": config["timezone"],
        "lot_size": row["lot_size"],
        "settlement_sessions": config["sale_wait_sessions"],
        "hk_tick_bands": deepcopy(bands["bands"]),
        "hk_metadata": deepcopy(row),
        "hk_day": day,
    }


def tick_for(price, bands, minimum=None):
    amount = Decimal(str(price))
    if amount < Decimal(str(minimum if minimum is not None else hk_execution_config()["minimum_price"])):
        raise ValueError("HK execution price is below the board-lot market minimum")
    for maximum, size in bands:
        if amount <= Decimal(str(maximum)):
            return Decimal(str(size))
    raise ValueError("HK execution price is outside the dated spread table")


def rounded_price(base, buy, policy, limit=None):
    direction = 1 if buy else -1
    price = Decimal(str(base))
    minimum = (policy.get("hk_rules") or hk_execution_config())["minimum_price"]
    tick = tick_for(price, policy["hk_tick_bands"], minimum)
    if policy["slippage_mode"] == "ratio":
        price *= 1 + direction * Decimal(str(policy["slippage_rate"]))
    elif policy["slippage_mode"] == "ticks":
        price += direction * tick * Decimal(str(policy["slippage_ticks"]))
    if price < Decimal(str(minimum)):
        return None
    tick = tick_for(price, policy["hk_tick_bands"], minimum)
    price = (price / tick).to_integral_value(rounding=ROUND_CEILING if buy else ROUND_FLOOR) * tick
    next_tick = tick_for(price, policy["hk_tick_bands"], minimum)
    price = (price / next_tick).to_integral_value(rounding=ROUND_CEILING if buy else ROUND_FLOOR) * next_tick
    if price <= 0 or limit is not None and (price > Decimal(str(limit)) if buy else price < Decimal(str(limit))):
        return None
    return float(price)


def hk_fees(policy, turnover, buy, day, prior=None):
    config = policy.get("hk_rules") or hk_execution_config()
    if day < config["valid_from"]:
        raise ValueError("HK fee schedule does not cover this historical date")
    state = deepcopy(prior or {})
    if state and state.get("buy") != buy:
        raise ValueError("External order direction cannot change")
    if turnover < 0:
        raise ValueError("HK turnover cannot be negative")
    if turnover == 0:
        return dict.fromkeys(("commission", "tax", "transfer_fee", "other_fee", "total"), 0.0), state
    amount = Decimal(str(state.get("hk_turnover", 0))) + Decimal(str(turnover))
    rate = policy["buy_commission_rate" if buy else "sell_commission_rate"]
    targets = {
        "commission": max(amount * Decimal(str(rate)), Decimal(str(policy["minimum_commission"]))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    }
    days = state.setdefault("hk_component_days", {})
    day_amount = Decimal(str(days.get(day, {}).get("turnover", 0))) + Decimal(str(turnover))
    current_components = {}
    for name, definition in config["fees"].items():
        if isinstance(definition, list):
            definition = max((part for part in definition if part["from"] <= day), key=lambda part: part["from"])
        raw = day_amount * Decimal(str(definition["rate"]))
        raw = max(raw, Decimal(str(definition.get("minimum", 0))))
        if definition.get("maximum") is not None:
            raw = min(raw, Decimal(str(definition["maximum"])))
        current_components[name] = raw.quantize(
            Decimal(definition["quantum"]),
            rounding=(ROUND_CEILING if definition["rounding"] == "ceiling" else ROUND_HALF_UP),
        )
        if policy["commission_includes_regulatory"] and name in {"sfc", "afrc", "trading"}:
            current_components[name] = Decimal(0)
    days[day] = {"turnover": str(day_amount), "fees": {name: str(value) for name, value in current_components.items()}}
    components = {
        name: sum((Decimal(part["fees"][name]) for part in days.values()), Decimal(0)) for name in current_components
    }
    state["hk_components"] = {name: str(value) for name, value in components.items()}
    targets.update(
        tax=components.pop("stamp"),
        transfer_fee=components.pop("settlement"),
        other_fee=sum(components.values(), Decimal(0)),
    )
    result = {key: float(value - Decimal(str(state.get("paid_" + key, 0)))) for key, value in targets.items()}
    for key, value in targets.items():
        state["paid_" + key] = str(value)
    state.update(hk_turnover=str(amount), buy=buy)
    result["total"] = float(
        sum(targets.values()) - sum(Decimal(str((prior or {}).get("paid_" + key, 0))) for key in targets)
    )
    return result, state
