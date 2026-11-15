"""Small homepage callback facade, independent of legacy custom-dashboard services."""

from src.core.repository import Repository

from .home_actions import action_rows
from .home_dashboard import home_account, home_market, home_news, home_operations
from .shared_observations import cached_observation
from .view_primitives import _normalize_account_mode


class HomeServiceMixin:
    def home_account(self, account_mode="paper", force_refresh=False):
        return home_account(_normalize_account_mode(account_mode), force_refresh)

    def home_market(self, account_mode="paper", force_refresh=False):
        return home_market(_normalize_account_mode(account_mode), force_refresh)

    def home_news(self, account_mode="paper", force_refresh=False):
        return home_news(_normalize_account_mode(account_mode), force_refresh)

    def home_operations(self, account_mode="paper", force_refresh=False):
        repo = Repository()
        mode = _normalize_account_mode(account_mode)
        query = (
            "SELECT id FROM paper_accounts ORDER BY updated_at DESC,id DESC LIMIT 1"
            if mode == "paper"
            else "SELECT id FROM live_configs ORDER BY updated_at DESC,id DESC LIMIT 1"
        )
        account = repo.db.query_one(query)
        pending = (
            int(
                repo.db.scalar(
                    "SELECT COUNT(*) FROM paper_orders WHERE account_id=? AND status NOT IN ('已成交','已撤销')",
                    (account["id"],),
                )
                or 0
            )
            if account and mode == "paper"
            else 0
        )
        valuation = cached_observation(["account", mode]) or {}
        rows = action_rows(
            repo, mode, bool(account), valuation.get("exposure") or 0, valuation.get("concentration") or 0, pending
        )
        if account and valuation.get("total_asset") is None:
            rows.insert(
                0,
                {
                    "priority": "高",
                    "category": "账户",
                    "item": "账户估值未提供，风险无法判定",
                    "next_step": "检查账户回传或持仓行情，补齐估值来源",
                },
            )
        return home_operations(rows)
