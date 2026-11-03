"""Financial semantics and color-scale regression coverage for the redesigned homepage."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pandas as pd
import pytest
from home_fixtures import seed_home_account

from src.core.repository import Repository
from src.frontend.service.home_charts import allocation, contribution, sector_heatmap
from src.frontend.service.home_data import HomeAccount, account_snapshot
from src.frontend.service.home_tables import home_styled_frame
from src.frontend.service.home_views import action_summary
from src.frontend.services import FrontendService


def test_home_valuation_and_details_share_quotes(client):
    _, expected = seed_home_account()
    from src.data import DataSourceManager

    manager = DataSourceManager()
    quote = Mock(wraps=manager.stock_quote)
    manager.stock_quote = quote
    with patch("src.frontend.service.home_data.DataSourceManager", return_value=manager):
        snapshot = account_snapshot("paper", force_refresh=True)
        assert quote.call_count == 3
        frontend = FrontendService()
        frontend.home_account("paper")
        risk, holdings, _ = frontend.dashboard_account("paper")
        assert quote.call_count == 3
    assert snapshot.total_asset == pytest.approx(expected["total_asset"])
    assert snapshot.total_pnl == pytest.approx(expected["total_pnl"])
    assert snapshot.daily_pnl == pytest.approx(expected["total_pnl"], abs=0.01)
    assert snapshot.cash + sum(allocation(snapshot).data[0].values[:-1]) == pytest.approx(snapshot.total_asset)
    assert sum(contribution(snapshot).data[0].x) == pytest.approx(expected["holding_pnl"])
    assert holdings.data["market_value"].sum() + snapshot.cash == pytest.approx(expected["total_asset"])
    assert risk[risk["metric"] == "总资产"].iloc[0]["value"]


def test_missing_account_and_live_config_are_not_zero_assets(client):
    assert account_snapshot("paper", True).total_asset is None
    repo = Repository()
    strategy = repo.insert(
        "strategies",
        {
            "name": "首页实盘测试策略",
            "file_path": "tests/fixtures/not_executed.py",
            "origin": "test",
            "created_at": "2026-10-17T00:00:00Z",
            "updated_at": "2026-10-17T00:00:00Z",
        },
    )
    repo.insert(
        "live_configs",
        {
            "name": "未回传实盘",
            "strategy_id": strategy["id"],
            "channel": "paper",
            "capital": 1000000,
            "status": "draft",
            "created_at": "2026-10-17T00:00:00Z",
            "updated_at": "2026-10-17T00:00:00Z",
        },
    )
    snapshot = account_snapshot("live", True)
    assert snapshot.account
    assert snapshot.total_asset is snapshot.daily_pnl is snapshot.exposure is None
    assert len(allocation(snapshot).data) == 0
    assert "broker" in allocation(snapshot).layout.annotations[0].text


def test_zero_holdings_are_cash_and_missing_history_is_not_padded(client):
    repo = Repository()
    repo.insert(
        "paper_accounts",
        {
            "name": "现金账户",
            "initial_cash": 100000,
            "current_cash": 100000,
            "status": "active",
            "created_at": "2026-10-17T00:00:00Z",
            "updated_at": "2026-10-17T00:00:00Z",
        },
    )
    snapshot = account_snapshot("paper", True)
    assert snapshot.daily_pnl is None
    assert snapshot.drawdown is None
    assert snapshot.history == []
    assert list(allocation(snapshot).data[0].labels) == ["现金"]
    assert list(allocation(snapshot).data[0].values) == [100000]


def test_missing_quotes_never_become_zero_cost_estimates(client):
    seed_home_account()
    manager = Mock()
    manager.stock_quote.side_effect = RuntimeError("offline")
    with patch("src.frontend.service.home_data.DataSourceManager", return_value=manager):
        snapshot = account_snapshot("paper", True)
    assert snapshot.total_asset is None
    assert all(row["market_value"] is None for row in snapshot.holdings)
    assert len(snapshot.warnings) == 3
    assert not contribution(snapshot).data


def test_heatmap_size_uses_amount_and_missing_values_stay_missing():
    rows = [{"name": "涨", "change_pct": 2, "amount": 100}, {"name": "跌", "change_pct": -1, "amount": 50}]
    trace = sector_heatmap(rows).data[0]
    assert list(trace.values) == [100, 50]
    assert list(trace.marker.colors) == [2, -1]
    assert trace.marker.cmin == -trace.marker.cmax
    rows[1]["amount"] = None
    assert list(sector_heatmap(rows).data[0].values) == [1, 1]
    assert len(sector_heatmap([]).data) == 0


def test_color_scales_preserve_percent_values_and_identifiers():
    frame = pd.DataFrame({"symbol": ["000001", "600519"], "change_pct": ["+1.0%", "-2.0%"], "market_value": [100, 200]})
    styled = home_styled_frame(frame)
    assert styled.data.equals(frame)
    context = styled._compute().ctx
    assert (0, 0) not in context
    assert ("--home-cell-color", "#cf4058") in context[(0, 1)]
    assert ("--home-cell-color", "#138b78") in context[(1, 1)]
    assert ("--home-cell-color", "#526fe0") in context[(0, 2)]
    assert dict(context[(0, 1)])["--home-cell-strength"] < dict(context[(1, 1)])["--home-cell-strength"]


def test_priority_is_ordered_and_no_fake_portfolio_is_drawn():
    html = action_summary([{"priority": "低", "item": "later"}, {"priority": "高", "item": "first"}])
    assert html.index("first") < html.index("later")
    assert not allocation(HomeAccount("paper")).data


def test_market_switch_does_not_reprice_cn_holdings_as_us(client):
    from src.frontend.service.foundation import switch_ui_market

    _, expected = seed_home_account()
    try:
        switch_ui_market("美股")
        assert account_snapshot("paper", True).total_asset == pytest.approx(expected["total_asset"])
    finally:
        switch_ui_market("A股")


def test_market_outage_is_explicit_and_partial_charts_are_empty(client):
    with patch("src.frontend.service.home_dashboard.QuoteService") as quotes:
        quotes.return_value.indices.side_effect = RuntimeError("offline")
        quotes.return_value.sectors.side_effect = RuntimeError("offline")
        quotes.return_value.watchlist_quotes.return_value = []
        summary, _, heatmap, _, indices, _ = FrontendService().home_market(force_refresh=True)
    assert "加载失败" in summary
    assert "缺失" in summary
    assert not heatmap.data
    assert indices.empty
