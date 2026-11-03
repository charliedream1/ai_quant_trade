"""Version-pinned paper accounts with compare-and-swap state and explicit monitoring."""

import json
from typing import Any

from src.core.repository import json_loads
from src.core.timeutil import utc_now_iso

from .config import fail
from .store import PipelineStore


class PipelineAccounts:
    def __init__(self, store: PipelineStore | None = None):
        self.store = store or PipelineStore()
        self.repo = self.store.repo

    def create(self, version_id: int, name: str) -> dict[str, Any]:
        version = self.store.version(version_id, True)
        now = utc_now_iso()
        row = self.repo.insert(
            "strategy_pipeline_accounts",
            {
                "name": name or version["compiled"]["name"],
                "version_id": version_id,
                "state": json.dumps({"monitor_enabled": False, "monitor_request": {}, "audit": []}),
                "created_at": now,
                "updated_at": now,
            },
        )
        return self.detail(row["id"])

    def detail(self, account_id: int) -> dict[str, Any]:
        row = self.repo.get("strategy_pipeline_accounts", account_id)
        row["state"] = json_loads(row["state"], {})
        return row

    def list(self) -> list[dict[str, Any]]:
        return [self.detail(row["id"]) for row in self.repo.list("strategy_pipeline_accounts")]

    def monitor(self, account_id: int, enabled: bool) -> dict[str, Any]:
        row = self.detail(account_id)
        state = row["state"]
        if enabled and not state.get("monitor_request"):
            raise fail("invalid", "account must complete a paper step first")
        state["monitor_enabled"] = enabled
        state["audit"].append({"time": utc_now_iso(), "action": "monitor", "enabled": enabled})
        self.store.save_account(account_id, row["version"], state, row["last_as_of"])
        return self.detail(account_id)

    def reset_risk(self, account_id: int) -> dict[str, Any]:
        row = self.detail(account_id)
        state = row["state"]
        # Only this local paper ledger is reset; no broker order is sent.
        for risk in state.get("risk", {}).values():
            risk.update(peak=risk.get("last_nav") or 0, drawdown_latched=False, freeze_until=-1)
        state["audit"].append({"time": utc_now_iso(), "action": "reset_paper_risk"})
        self.store.save_account(account_id, row["version"], state, row["last_as_of"])
        return self.detail(account_id)
