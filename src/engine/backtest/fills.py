"""Small adapters from simple-engine signals to the shared cost model."""

from src.engine.execution.costs import affordable_quantity, order_fee
from src.engine.execution.policy import blocked_reason, capacity, policy_for


def fill_details(signal, event, payload, cash, requested, buy, commission_rate, slippage):
    policy = policy_for(
        payload,
        {"commission_rate": commission_rate, "slippage_rate": slippage, "lot_size": payload.get("lot_size", 100)},
    )
    day = event.timestamp[:10]
    reason = blocked_reason(event.raw, buy, policy, day)
    past = payload.get("_past_events", {}).get(event.symbol, [])
    available = capacity(past, policy, int(requested))
    used_key = f"{event.symbol}:{day}"
    volume_used = payload.setdefault("_volume_used", {})
    used = volume_used.get(used_key, 0) if policy["max_participation"] < 1 else 0
    quantity = max(0, min(int(requested), available - used))
    index = len(payload.setdefault("_execution_orders", []))
    identity = str(signal.metadata.get("order_id") or f"{event.symbol}:{day}:{signal.side}:{index}")
    key = f"{event.symbol}:{signal.side}:{identity}"
    prior = payload.setdefault("_order_fee_states", {}).get(key)
    original_requested = int(prior.get("requested_quantity", requested)) if prior else int(requested)
    remaining_order = max(0, original_requested - int(prior.get("filled_quantity", 0))) if prior else int(requested)
    quantity = min(quantity, remaining_order)
    price = float(payload["_fill_price"])
    if buy:
        quantity = affordable_quantity(cash, quantity, int(policy["lot_size"]), price, policy, day, prior)
    if reason:
        quantity = 0
    fees, state = order_fee(policy, quantity * price, buy, day, prior)
    if quantity:
        state.update(
            requested_quantity=original_requested,
            filled_quantity=int((prior or {}).get("filled_quantity", 0)) + quantity,
        )
        payload["_order_fee_states"][key] = state
        payload["_volume_used"][used_key] = used + quantity
    reference = event.open if payload.get("order_type") == "open" else float(signal.price or event.close)
    record = {
        "order_id": identity,
        "symbol": event.symbol,
        "time": event.timestamp,
        "side": signal.side,
        "requested_quantity": int(requested),
        "quantity": quantity,
        "price": price,
        "reference_price": reference,
        "commission": fees["commission"],
        "costs": fees,
        "slippage_cost": abs(price - reference) * quantity,
        "status": "filled" if quantity == requested else "partial" if quantity else "deferred",
        "reason": reason or ("volume_or_cash_constraint" if quantity < requested else "filled"),
        "unfilled_policy": "expired_after_bar; explicit order_id can accumulate fee across fills",
    }
    payload["_execution_orders"].append(record)
    return quantity, fees


def record_rejection(payload, event, signal, reason):
    payload.setdefault("_execution_orders", []).append(
        {
            "symbol": event.symbol,
            "time": event.timestamp,
            "side": signal.side,
            "quantity": 0,
            "status": "rejected",
            "reason": reason,
        }
    )


def reduce_position(position, quantity, session):
    ratio = max(0, (position["quantity"] - quantity) / position["quantity"])
    position["quantity"] -= quantity
    for key in ("cost_basis", "open_value", "open_commission"):
        position[key] = float(position.get(key, 0)) * ratio
    position["open_costs"] = {key: value * ratio for key, value in position.get("open_costs", {}).items()}
    remaining = quantity
    for lot in position.get("lots", []):
        if lot["unlock_session"] > session:
            continue
        take = min(remaining, lot["quantity"])
        lot["quantity"] -= take
        remaining -= take
    position["lots"] = [lot for lot in position.get("lots", []) if lot["quantity"]]
