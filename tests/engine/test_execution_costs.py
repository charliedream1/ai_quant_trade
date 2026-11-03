"""Independent cash arithmetic, shared fee allocation, limits and dated capability gates."""

from decimal import Decimal

import pytest

from src.core.exceptions import BusinessError
from src.engine.execution.config import resolve_costs
from src.engine.execution.costs import affordable_quantity, order_fee, slipped_price, split_fees
from src.engine.execution.policy import blocked_reason, capability_gaps


def test_actual_cn_example_buy_sell_arithmetic_and_minimum_once():
    policy = resolve_costs({"profile": "cn_a"})
    buy, _ = order_fee(policy, 1000, True, "2026-01-05")
    sell, state = order_fee(policy, 1000, False, "2026-01-05")
    assert buy == {"commission": 5, "tax": 0, "transfer_fee": 0.01, "other_fee": 0, "total": 5.01}
    assert sell["total"] == 5.51
    second, state = order_fee(policy, 2000, False, "2026-01-05", state)
    assert second["commission"] == 0 and second["tax"] == 1
    assert second["total"] == 1.02
    assert state["paid_commission"] == "5.00"


def test_cost_schedule_is_applied_per_fill_without_retaxing_past_fills():
    policy = resolve_costs({"profile": "cn_a"})
    first, state = order_fee(policy, 10000, False, "2023-08-25")
    second, _ = order_fee(policy, 10000, False, "2023-08-28", state)
    assert first["tax"] == 10 and second["tax"] == 5


def test_explicit_zero_tax_overrides_profile_schedule():
    policy = resolve_costs({"profile": "cn_a", "sell_tax_rate": 0})
    fees, _ = order_fee(policy, 10000, False, "2026-01-05")
    assert fees["tax"] == 0
    with pytest.raises(BusinessError, match="不覆盖"):
        order_fee(policy, 100, True, "2020-01-01")


@pytest.mark.parametrize("buy", [True, False])
@pytest.mark.parametrize("mode", ["ratio", "ticks"])
def test_slippage_never_breaches_limit(buy, mode):
    policy = resolve_costs({"slippage_mode": mode, "slippage_rate": 0.01, "slippage_ticks": 1})
    assert slipped_price(10, buy, policy, limit=10) is None
    assert slipped_price(10, buy, policy) == pytest.approx(
        10.1 if buy and mode == "ratio" else 9.9 if mode == "ratio" else 10.01 if buy else 9.99
    )


def test_minimum_fee_is_included_in_affordability():
    policy = resolve_costs({"profile": "cn_a", "slippage_mode": "none"})
    assert affordable_quantity(1000, 100, 100, 10, policy, "2026-01-05") == 0
    assert affordable_quantity(1005.01, 100, 100, 10, policy, "2026-01-05") == 100


def test_rounded_sleeve_allocations_conserve_every_fee_category():
    total = {"commission": 0.02, "tax": 0.01, "transfer_fee": 0.01, "other_fee": 0.01, "total": 0.05}
    result = split_fees(total, {"a": 1, "b": 1, "c": 1, "d": 1}, 2)
    for key in total:
        assert sum(Decimal(str(row[key])) for row in result.values()) == Decimal(str(total[key]))
    assert all(value >= 0 for row in result.values() for value in row.values())


@pytest.mark.parametrize(
    "bad",
    [
        {"minimum_commission": -1},
        {"slippage_rate": float("nan")},
        {"lot_size": 1.5},
        {"other_fee_rate": 0.001},
        {"mystery_fee": 1},
    ],
)
def test_invalid_costs_and_double_regulatory_charging_are_rejected(bad):
    with pytest.raises(BusinessError):
        resolve_costs(bad)


def test_strict_mode_requires_dated_state_and_explicit_no_action_evidence():
    policy = resolve_costs({"validation_mode": "strict"})
    row = {
        "date": "2026-01-05",
        "trading_status": {
            "suspended": False,
            "tradable": True,
            "limit_up": False,
            "limit_down": False,
            "available_at": "2026-01-05T08:00:00+08:00",
        },
        "corporate_actions": [],
    }
    assert capability_gaps({"A": [row]}, policy) == []
    row["trading_status"]["available_at"] = "2026-01-05T16:00:00+08:00"
    with pytest.raises(BusinessError, match="严格"):
        capability_gaps({"A": [row]}, policy)
    row["trading_status"]["available_at"] = "2026-01-04"
    row["trading_status"]["limit_up"] = True
    assert blocked_reason(row, True, policy, "2026-01-05") == "price_limit"
    assert blocked_reason(row, False, policy, "2026-01-05") == ""


def test_composition_external_order_charges_one_minimum_across_sleeves():
    from src.engine.composition.book import PortfolioBook
    from src.engine.composition.external_fills import market_fill

    book = PortfolioBook(5000, {"left": 0.5, "right": 0.5})
    book.advance("2026-01-05")
    book.prices["A"] = 10
    policy = resolve_costs({"buy_commission_rate": 0, "minimum_commission": 5, "fee_precision": 2})
    order, _ = market_fill(book, "A", {"left": 100, "right": 100}, 200, 1, 0, 10, True, {"_cost_policy": policy}, {})
    assert order["quantity"] == 200 and order["commission"] == 5
    assert book.cash() == 2995 and book.nav() == 4995
    assert book.sleeves["left"].cash == book.sleeves["right"].cash == 1497.5
