"""Versioned monitoring populations; current constituents are explicitly labelled."""

from __future__ import annotations

import hashlib
import importlib
import json
import re
from datetime import date
from typing import Any

from src.core.repository import Repository
from src.core.timeutil import today_date, utc_now_iso
from src.data import DataSourceManager, current_market


class MonitorUniverses:
    def __init__(self, repo: Repository, data: DataSourceManager, config: dict[str, Any]):
        self.repo, self.data, self.config = repo, data, config

    def resolve(
        self,
        text: str = "",
        universe_id: str = "custom",
        resource_id: int | None = None,
        as_of: str = "",
        membership_version: str = "",
    ) -> dict[str, Any]:
        cutoff = as_of or today_date()
        if date.fromisoformat(cutoff) > date.fromisoformat(today_date()):
            raise ValueError("观察日期不能晚于今天")
        if membership_version:
            return self._historical(membership_version, cutoff)
        definition = self.config["universes"].get(universe_id)
        if not definition:
            raise ValueError("未知监控股票池")
        symbols = self._symbols(text, definition["kind"], definition, resource_id)
        symbols = list(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))
        if not symbols:
            raise ValueError("股票池为空，请先选择或添加标的；不会自动扩展股票池")
        if len(symbols) > self.config["max_symbols"]:
            raise ValueError(f"股票池共{len(symbols)}只，超过配置上限；请调整配置或分池，不会截断")
        identity = {
            "id": universe_id,
            "resource_id": resource_id,
            "market": current_market(),
            "symbols": sorted(symbols),
        }
        version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        return {
            **identity,
            "version": version,
            "label": definition["label"],
            "kind": definition["kind"],
            "as_of": cutoff,
            "observed_at": utc_now_iso(),
            "history_policy": "模拟样本" if getattr(self.data, "is_mock", False) else "当前成分回看",
            "memberships": [],
            "data_source": self.data.source_name,
        }

    def _symbols(self, text: str, kind: str, definition: dict[str, Any], resource_id: int | None) -> list[str]:
        if kind == "custom":
            if text.strip():
                tokens = [value for value in re.split(r"[\s,，;；]+", text.strip()) if value]
                pattern = r"\d{6}" if current_market() == "CN" else r"[A-Za-z][A-Za-z0-9.-]{0,9}"
                if any(not re.fullmatch(pattern, value) for value in tokens):
                    raise ValueError("请输入当前市场标准代码，A股代码须保留六位")
                return tokens
            rows = self.repo.db.query("SELECT symbol FROM watchlist WHERE market = ? ORDER BY id", (current_market(),))
            return [row["symbol"] for row in rows] or self.config["default_universe"]
        if kind == "watchlist":
            return [row["symbol"] for row in self.repo.list("watchlist", "market = ?", (current_market(),))]
        if kind == "resource":
            if not resource_id:
                raise ValueError("请选择资源池ID")
            self.repo.get("resource_pools", resource_id)
            rows = self.repo.list("resource_pool_items", "pool_id = ?", (resource_id,))
            if {row["market"] for row in rows} - {current_market()}:
                raise ValueError("资源池含其他市场，请切换市场或分池")
            return [row["symbol"] for row in rows]
        if kind == "holdings":
            if not resource_id:
                raise ValueError("请指定模拟账户ID")
            return [
                row["symbol"]
                for row in self.repo.list("paper_positions", "account_id = ? AND quantity > 0", (resource_id,))
            ]
        if current_market() != "CN":
            raise ValueError("指数及全市场基准当前只支持A股")
        if getattr(self.data, "is_mock", False):
            return self.config["default_universe"]
        ak = importlib.import_module("akshare")

        if kind == "index":
            frame = ak.index_stock_cons_csindex(symbol=definition["code"])
            return frame["成分券代码"].astype(str).str.zfill(6).tolist()
        frame = ak.stock_info_a_code_name()
        return frame["code"].astype(str).str.zfill(6).tolist()

    def save_memberships(self, payload: dict[str, Any]) -> dict[str, Any]:
        members = payload.get("memberships") or []
        if not members or len(members) > self.config["max_symbols"]:
            raise ValueError("历史成员清单为空或超过限制")
        for row in members:
            if not re.fullmatch(r"[A-Z0-9.-]+", str(row.get("symbol", ""))):
                raise ValueError("历史成员代码不合法")
            start = date.fromisoformat(row["valid_from"])
            end = date.fromisoformat(row["valid_to"]) if row.get("valid_to") else date.max
            if start > end or start > date.fromisoformat(today_date()):
                raise ValueError("历史成员有效区间不合法")
        content = {
            "market": current_market(),
            "memberships": sorted(members, key=lambda row: (row["symbol"], row["valid_from"])),
            "source": str(payload.get("source") or "用户提供历史清单"),
        }
        version = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
        self.repo.db.execute(
            "INSERT OR IGNORE INTO monitor_universes(version, payload, observed_at) VALUES (?, ?, ?)",
            (version, json.dumps(content, ensure_ascii=False), utc_now_iso()),
        )
        return {"version": version, "members": len(members), "source": content["source"]}

    def _historical(self, version: str, cutoff: str) -> dict[str, Any]:
        row = self.repo.db.query_one("SELECT * FROM monitor_universes WHERE version = ?", (version,))
        if not row:
            raise ValueError("历史股票池版本不存在")
        content = json.loads(row["payload"])
        if content["market"] != current_market():
            raise ValueError("历史股票池市场与当前市场不一致")
        members = [item for item in content["memberships"] if item["valid_from"] <= cutoff]
        return {
            **content,
            "id": version,
            "version": version,
            "label": "历史成员清单",
            "kind": "historical",
            "as_of": cutoff,
            "history_policy": "用户提供时点成员",
            "observed_at": row["observed_at"],
            "memberships": members,
            "symbols": sorted({row["symbol"] for row in members}),
        }
