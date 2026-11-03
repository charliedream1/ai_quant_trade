"""One aggregate market order, one minimum commission, exact sleeve allocation."""

from src.engine.execution.config import resolve_costs
from src.engine.execution.costs import order_fee, slipped_price, split_fees


def split_quantities(total: int, requests: dict[str, int], lot: int) -> dict[str, int]:
    requested = sum(requests.values())
    if requested <= total:
        return dict(requests)
    result = {key: min(value, int(total * value / requested) // lot * lot) for key, value in requests.items()}
    remaining = total - sum(result.values())
    for key in sorted(requests):
        extra = min(requests[key] - result[key], remaining) // lot * lot
        result[key] += extra
        remaining -= extra
    return result


def _quote(book, symbol, requests, total, lot, price, raw, buy, policy, limits):
    allocation = split_quantities(total, requests, lot)
    fees, _ = order_fee(policy, sum(allocation.values()) * price, buy, book.last_day)
    parts = split_fees(fees, allocation, int(policy["fee_precision"]))
    fits = all(
        price * amount + parts[key]["total"] <= book.sleeves[key].cash + 1e-9
        for key, amount in allocation.items()
        if amount
    )
    if buy and limits:
        nav = book.nav() - fees["total"] - (price - raw) * total
        positions = book.positions()
        market = sum(quantity * book.prices[key] for key, quantity in positions.items()) + total * raw
        symbol_value = positions.get(symbol, 0) * raw + total * raw
        fits = (
            fits
            and nav > 0
            and market <= nav * limits["max_exposure"] + 1e-9
            and symbol_value <= nav * limits["max_weight"] + 1e-9
        )
    return allocation, fees, parts, fits if buy else True


def market_fill(book, symbol, requests, maximum, lot, settlement, raw_price, buy, execution, hard_limits):
    policy = execution.get("_cost_policy") or resolve_costs(None, execution)
    price = slipped_price(raw_price, buy, policy)
    if price is None:
        return {"symbol": symbol, "quantity": 0, "status": "rejected", "reason": "invalid_execution_price"}, []
    low, high = 0, max(0, int(maximum) // lot)
    while low < high:
        middle = (low + high + 1) // 2
        *_, fits = _quote(book, symbol, requests, middle * lot, lot, price, raw_price, buy, policy, hard_limits)
        if fits:
            low = middle
        else:
            high = middle - 1
    allocation, fees, parts, _ = _quote(
        book, symbol, requests, low * lot, lot, price, raw_price, buy, policy, hard_limits
    )
    trades: list[dict] = []
    actual = {key: amount for key, amount in allocation.items() if amount}
    for key, amount in actual.items():
        closed = book.sleeves[key].fill(
            symbol,
            amount if buy else -amount,
            price,
            parts[key]["total"],
            book.session,
            settlement,
            book.last_day,
            "market",
            costs=parts[key],
        )
        trades.extend({**row, "sleeve": key} for row in closed)
    filled = sum(actual.values())
    return {
        "order_id": f"{book.last_day}:{symbol}:{'buy' if buy else 'sell'}",
        "symbol": symbol,
        "side": "buy" if buy else "sell",
        "time": book.last_day,
        "requested_quantity": sum(requests.values()),
        "quantity": filled,
        "price": price,
        "reference_price": raw_price,
        "commission": fees["commission"],
        "costs": fees,
        "slippage_cost": abs(price - raw_price) * filled,
        "status": "filled" if filled == sum(requests.values()) else "partial" if filled else "deferred",
        "reason": "daily_bar_open_research",
        "sleeves": actual,
        "requested_by_sleeve": requests,
        "unfilled_policy": "expired_after_daily_batch",
        "liquidity_basis": "past_average_volume",
    }, trades
