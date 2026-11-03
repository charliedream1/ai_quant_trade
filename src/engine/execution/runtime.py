"""Freeze execution experiments separately from immutable research strategy versions."""

from copy import deepcopy
from typing import Any

from .config import resolve_costs


def prepare_execution(plan: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(plan)
    policy = (
        request.get("_cost_policy")
        or request.get("execution_cost_snapshot")
        or resolve_costs(request.get("execution_costs"), result["execution"])
    )
    result["execution"].update(
        {
            key: policy[key]
            for key in ("slippage_rate", "lot_size", "settlement_sessions", "max_participation", "liquidity_window")
        }
    )
    result["execution"].update(commission_rate=policy["buy_commission_rate"], _cost_policy=policy)
    request["execution_cost_snapshot"] = policy
    return result
