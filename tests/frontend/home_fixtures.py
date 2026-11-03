"""Seed explicit test cases in the database already selected by the test environment."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.engine.market import QuoteService
from src.frontend.service.foundation import _DAILY_UI_CACHE, _local_now


def seed_home_account() -> tuple[int, dict[str, Any]]:
    payload = yaml.safe_load(Path("tests/fixtures/home_dashboard.yaml").read_text(encoding="utf-8"))
    repo = Repository()
    now = utc_now_iso()
    account = repo.db.query_one("SELECT * FROM paper_accounts WHERE name = ?", (payload["account"]["name"],))
    if not account:
        account = repo.insert("paper_accounts", {**payload["account"], "created_at": now, "updated_at": now})
    for row in payload["holdings"]:
        if not repo.db.query_one(
            "SELECT id FROM paper_positions WHERE account_id = ? AND symbol = ?", (account["id"], row["symbol"])
        ):
            repo.insert("paper_positions", {**row, "account_id": account["id"], "updated_at": now})
    for row in payload["history"]:
        repo.insert(
            "paper_nav_history",
            {
                "account_id": account["id"],
                "nav_date": (_local_now().date() - timedelta(days=row["days_ago"])).isoformat(),
                "net_value": row["net_value"],
                "daily_return": row["daily_return"],
                "total_asset": payload["account"]["initial_cash"] * row["net_value"],
                "cash": payload["account"]["current_cash"],
                "market_value": payload["account"]["initial_cash"] * row["net_value"]
                - payload["account"]["current_cash"],
                "created_at": now,
            },
        )
    quotes = QuoteService(repo=repo)
    group = quotes.create_group(f"首页验收-{account['id']}")
    quotes.add_symbols(group["id"], [row["symbol"] for row in payload["holdings"]])
    _DAILY_UI_CACHE.clear()
    return int(account["id"]), payload["expected"]
