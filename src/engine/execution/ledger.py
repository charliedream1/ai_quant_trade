"""Actual external fill costs and return attribution without charging slippage twice."""

from typing import Any

from .costs import CATEGORIES


def cost_summary(orders: list[dict[str, Any]], initial: float, final: float) -> dict[str, Any]:
    filled = [row for row in orders if row.get("quantity", 0) > 0]
    values = {
        key: sum(float((row.get("costs") or {"commission": row.get("commission", 0)}).get(key, 0)) for row in filled)
        for key in CATEGORIES
    }
    slippage = sum(float(row.get("slippage_cost") or 0) for row in filled)
    total = sum(values.values()) + slippage
    net = final - initial
    return {
        "commission_paid": values["commission"],
        "tax_paid": values["tax"],
        "transfer_fee_paid": values["transfer_fee"],
        "other_fee_paid": values["other_fee"],
        "slippage_cost": slippage,
        "total_execution_cost": total,
        "net_pnl": net,
        "gross_pnl_before_costs": net + total,
        "net_return": net / initial if initial else 0,
        "gross_return_before_costs": (net + total) / initial if initial else 0,
        "cost_attribution_scope": "实际成交不变、加回成本的归因；不是重新运行的零成本策略",
        "cost_breakdown_complete": all("costs" in row for row in filled),
        "execution_orders": orders,
        "unfilled_order_count": sum(row.get("status") in {"rejected", "deferred", "partial"} for row in orders),
    }
