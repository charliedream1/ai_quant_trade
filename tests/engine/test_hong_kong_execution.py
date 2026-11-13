"""Independent dated fee and tick arithmetic; missing instrument evidence blocks execution."""

from datetime import date

import pytest

from src.core.exceptions import BusinessError
from src.data.hong_kong_calendar import sessions
from src.engine.execution.config import resolve_costs
from src.engine.execution.costs import order_fee, slipped_price
from src.engine.execution.hong_kong import dated_policy


def policy(day="2026-10-02"):
    base = resolve_costs(
        {
            "profile": "hk_cash",
            "slippage_mode": "none",
            "instruments": {
                "00700.HK": {
                    "from": "2024-01-01",
                    "lot_size": 100,
                    "source": "Explicit test-only assumption",
                    "currency": "HKD",
                    "asset_type": "stock",
                    "assumption": True,
                }
            },
        }
    )
    return dated_policy("00700.HK", day, base)


def test_hk_stamp_duty_ceiling_and_independently_rounded_regulatory_fees():
    fees, _ = order_fee(policy(), 1000.01, True, "2026-10-02")
    assert fees == {"commission": 0.3, "tax": 2, "transfer_fee": 0.04, "other_fee": 0.09, "total": 2.43}
    assert order_fee(policy(), 1000.01, False, "2026-10-02")[0] == fees


def test_hk_historical_settlement_minimum_changes_by_date():
    fees, _ = order_fee(policy("2024-01-02"), 1000, True, "2024-01-02")
    assert fees["transfer_fee"] == 2 and fees["total"] == pytest.approx(3.39)


def test_hk_cross_date_order_preserves_previously_paid_schedule():
    settings = policy("2025-06-27")
    first, state = order_fee(settings, 1000, True, "2025-06-27")
    second, _ = order_fee(settings, 1000, True, "2025-06-30", state)
    assert first["transfer_fee"] == 2
    assert second["transfer_fee"] == pytest.approx(0.04)
    assert all(value >= 0 for value in second.values())


def test_hk_paper_currency_lots_fees_and_market_persistence(client):
    from src.data import DataSourceManager
    from src.engine.paper.account import PaperAccountService

    service = PaperAccountService(data=DataSourceManager(mode="mock", market="HK"))
    settings = policy()
    account = service.create(
        {
            "name": "HK test account",
            "initial_cash": 100000,
            "market": "HK",
            "execution_costs": {"profile": "hk_cash", "instruments": settings["instruments"]},
        }
    )
    assert account["currency"] == "HKD"
    with pytest.raises(BusinessError, match="board lot"):
        service.order(account["id"], {"symbol": "00700", "side": "buy", "quantity": 1})
    service.order(account["id"], {"symbol": "00700", "side": "buy", "quantity": 100})
    service.order(account["id"], {"symbol": "00700.HK", "side": "sell", "quantity": 100})
    overview = PaperAccountService(data=DataSourceManager(mode="mock", market="CN")).overview(account["id"])
    fees = order_fee(settings, 40000, True, date.today().isoformat())[0]["total"]
    assert overview["currency"] == "HKD" and overview["cash"] == pytest.approx(100000 - 2 * fees)


@pytest.mark.parametrize(
    "day,price,expected",
    [
        ("2025-01-02", 12.001, 12.02),
        ("2025-08-04", 12.001, 12.01),
        ("2026-08-02", 4.001, 4.01),
        ("2026-08-03", 4.001, 4.005),
        ("2026-10-02", 20.001, 20.02),
    ],
)
def test_hk_dated_spread_and_price_boundaries(day, price, expected):
    assert slipped_price(price, True, policy(day)) == pytest.approx(expected)
    assert slipped_price(price, True, policy(day), limit=price) is None


def test_missing_lot_and_unverified_strict_metadata_fail():
    with pytest.raises(ValueError, match="board lot"):
        dated_policy("00700.HK", "2026-10-02", resolve_costs({"profile": "hk_cash"}))
    settings = policy()
    settings["validation_mode"] = "strict"
    with pytest.raises(ValueError, match="assumed"):
        dated_policy("00700.HK", "2026-10-02", settings)


def test_hk_board_lot_is_not_clamped_to_a_mainland_default():
    from src.engine.backtest.engines import _lot_size

    assert _lot_size({"_cost_policy": {"market": "HK", "lot_size": 15000}}) == 15000


def test_hk_calendar_keeps_october_mainland_open_days_and_hk_holidays_separate():
    assert sessions("2026-10-01", "2026-10-02") == ["2026-10-02"]
    assert sessions("2026-10-19", "2026-10-19") == []
    assert sessions("2024-01-01", "2024-01-02") is None
