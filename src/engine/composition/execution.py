"""Net sleeve intents, trade settled lots and preserve physical cash conservation."""

from typing import Any

import numpy as np

from src.engine.execution.policy import blocked_reason
from src.strategy.composition.config import config, fail
from src.strategy.composition.contracts import Frame

from .book import PortfolioBook
from .external_fills import market_fill


def _split(total: int, requests: dict[str, int], lot: int) -> dict[str, int]:
    requested = sum(requests.values())
    if requested <= total:
        return dict(requests)
    allocated = {key: min(value, int(total * value / requested) // lot * lot) for key, value in requests.items()}
    remainder = total - sum(allocated.values())
    for key in sorted(requests):
        extra = min(requests[key] - allocated[key], remainder) // lot * lot
        allocated[key] += extra
        remainder -= extra
    return allocated


def _build_intents(book, targets, opens, frame, policy, emergency):
    """Translate targets into executable sleeve quantities using only prior observations."""
    nav = book.nav()
    epsilon = config()["defaults"]["epsilon"]
    intents: dict[str, dict[str, int]] = {}
    rules = {}
    orders: list[dict[str, Any]] = []
    for symbol in sorted(set(book.positions()) | {s for values in targets.values() for s in values}):
        if symbol not in opens:
            orders.append({"symbol": symbol, "status": "deferred", "reason": "stale"})
            continue
        meta = frame.metadata.get(symbol, {})
        dated_reason = blocked_reason(opens[symbol], False, policy.get("_cost_policy", {}), book.last_day)
        if dated_reason and dated_reason != "price_limit":
            orders.append({"symbol": symbol, "quantity": 0, "status": "deferred", "reason": dated_reason})
            continue
        if meta.get("suspended") or not meta.get("tradable", True):
            orders.append({"symbol": symbol, "status": "deferred", "reason": "not_tradable"})
            continue
        lot = int(meta.get("lot_size") or policy["lot_size"])
        settlement = int(meta.get("settlement_sessions", policy["settlement_sessions"]))
        price = float(opens[symbol]["open"])
        if price <= 0:
            continue
        rules[symbol] = (lot, settlement)
        intents[symbol] = {}
        for key, sleeve in book.sleeves.items():
            weight = float(targets.get(key, {}).get(symbol, 0))
            desired = int(nav * weight / price) // lot * lot
            current = sleeve.quantity(symbol)
            delta = desired - current
            if blocked_reason(opens[symbol], delta > 0, policy.get("_cost_policy", {}), book.last_day):
                delta = 0
            if delta > 0 and (meta.get("limit_up") or meta.get("is_st")):
                delta = 0
            if delta < 0:
                if meta.get("limit_down"):
                    delta = 0
                else:
                    delta = -min(-delta, sleeve.available(symbol, book.session))
            previous = frame.history.get(symbol, ())
            if delta > 0 and previous and abs(price / float(previous[-1]["close"]) - 1) > policy["max_gap"]:
                delta = 0
            if (
                symbol not in emergency
                and weight > 0
                and abs(delta) * price / max(nav, epsilon) < policy["rebalance_band"]
            ):
                delta = 0
            intents[symbol][key] = delta
            if delta == 0 and desired != current:
                orders.append(
                    {
                        "symbol": symbol,
                        "sleeve": key,
                        "status": "deferred",
                        "reason": "execution_constraint",
                        "desired": desired,
                        "actual": current,
                    }
                )
    return intents, rules, orders


def _cross_internal(book, intents, opens):
    """Transfer sleeve attribution without broker turnover or duplicate market fees."""
    transfers = []
    for symbol, deltas in intents.items():
        price = float(opens[symbol]["open"])
        for seller in sorted(deltas):
            for buyer in sorted(deltas):
                quantity = min(max(-deltas[seller], 0), max(deltas[buyer], 0))
                if not quantity:
                    continue
                closed = book.sleeves[seller].fill(
                    symbol, -quantity, price, 0, book.session, 0, book.last_day, "internal"
                )
                book.sleeves[buyer].fill(symbol, quantity, price, 0, book.session, 0, book.last_day, "internal")
                transfers.append(
                    {
                        "symbol": symbol,
                        "seller": seller,
                        "buyer": buyer,
                        "quantity": quantity,
                        "price": price,
                        "realized_attribution": sum(row["pnl"] for row in closed),
                    }
                )
                deltas[seller] += quantity
                deltas[buyer] -= quantity
    return transfers


def execute_targets(
    book: PortfolioBook,
    targets: dict[str, dict[str, float]],
    budgets: dict[str, float],
    opens: dict[str, dict[str, Any]],
    frame: Frame,
    policy: dict[str, Any],
    emergency: set[str] | None = None,
    hard_limits: dict[str, Any] | None = None,
) -> dict[str, Any]:
    emergency = emergency or set()
    epsilon = config()["defaults"]["epsilon"]
    intents, rules, orders = _build_intents(book, targets, opens, frame, policy, emergency)
    transfers = _cross_internal(book, intents, opens)
    trades: list[dict[str, Any]] = []
    turnover_left = policy["turnover_limit"] * book.nav()

    def fill_side(buy: bool) -> None:
        nonlocal turnover_left
        for symbol, deltas in intents.items():
            requests = {
                key: (quantity if buy else -quantity)
                for key, quantity in deltas.items()
                if (quantity > 0 if buy else quantity < 0)
            }
            if not requests:
                continue
            raw_price = float(opens[symbol]["open"])
            lot, settlement = rules[symbol]
            history = frame.history.get(symbol, ())[-policy["liquidity_window"] :]
            average_volume = float(np.mean([float(row.get("volume") or 0) for row in history])) if history else 0.0
            capacity = int(average_volume * policy["max_participation"]) // lot * lot
            if symbol not in emergency:
                capacity = min(capacity, int(turnover_left / raw_price) // lot * lot)
            quantity = min(sum(requests.values()), capacity)
            limits = dict(hard_limits or {})
            if buy and limits:
                positions = book.positions()
                if symbol not in positions and len(positions) >= limits["max_positions"]:
                    quantity = 0
                limits["max_weight"] = min(
                    limits["max_weight"], sum(values.get(symbol, 0) for values in targets.values())
                )
            order, closed = market_fill(
                book, symbol, requests, quantity, lot, settlement, raw_price, buy, policy, limits
            )
            orders.append(order)
            trades.extend(closed)
            turnover_left = max(0.0, turnover_left - order["quantity"] * raw_price)

    fill_side(False)
    flows = book.rebudget_cash(budgets)
    fill_side(True)
    if book.cash() < -epsilon or any(sleeve.cash < -epsilon for sleeve in book.sleeves.values()):
        raise fail("invalid", "cash conservation")
    return {
        "orders": orders,
        "trades": trades,
        "internal_transfers": transfers,
        "capital_flows": flows,
        "turnover": sum(row.get("quantity", 0) * row.get("price", 0) for row in orders),
        "fees": sum((row.get("costs") or {}).get("total", row.get("commission", 0)) for row in orders),
        "account_after_execution": book.snapshot(),
    }
