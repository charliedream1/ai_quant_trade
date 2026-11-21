"""Market quote aggregation."""

from math import isfinite
from typing import Any

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.data import DataSourceManager


class QuoteService:
    def __init__(self, repo: Repository | None = None, data: DataSourceManager | None = None) -> None:
        self.repo = repo or Repository()
        self.data = data or DataSourceManager()

    def indices(self, refresh: bool = False) -> list[dict[str, Any]]:
        return self.data.indices(refresh=refresh)

    def sectors(
        self,
        board: str = "industry",
        sort: str = "涨跌幅",
        limit: int = 20,
        direction: str = "desc",
        refresh: bool = False,
    ) -> list[dict[str, Any]]:
        if direction not in {"asc", "desc"} or sort not in {"涨跌幅", "change_pct"}:
            raise ValueError("Select change_pct sorting and asc/desc direction")
        options = {"refresh": True} if refresh else {}
        items = self.data.sectors(board=board, limit=limit, direction=direction, **options)
        items = [row for row in items if row.get("change_pct") is not None and isfinite(float(row["change_pct"]))]
        return sorted(items, key=lambda row: row["change_pct"], reverse=direction == "desc")

    def sector_rankings(self, board="industry", limit=20, selection="balanced", refresh=False):
        if selection not in {"balanced", "gainers", "decliners"}:
            raise ValueError("Unknown sector ranking selection")
        count = max(1, min(int(limit), 100))
        each = (count + 1) // 2 if selection == "balanced" else count
        rows: list[dict[str, Any]] = []
        if selection != "decliners":
            rows.extend(
                dict(row, ranking="Gainer")
                for row in self.sectors(board, limit=each, direction="desc", refresh=refresh)
                if row.get("change_pct") is not None and float(row["change_pct"]) > 0
            )
        if selection != "gainers":
            rows.extend(
                dict(row, ranking="Decliner")
                for row in self.sectors(board, limit=each, direction="asc", refresh=refresh)
                if row.get("change_pct") is not None and float(row["change_pct"]) < 0
            )
        unique = {row["code"]: row for row in rows}
        return list(unique.values())[:count]

    def sector_snapshot(self, limit: int, *, refresh: bool = False) -> tuple[list[dict], list[dict]]:
        """Use one bounded source read for rankings and a verified complete universe."""
        rows = self.data.sectors(board="industry", limit=limit, direction="desc", refresh=refresh)
        unique = {row["code"]: row for row in rows if row.get("code")}
        valid = [
            row for row in unique.values() if row.get("change_pct") is not None and isfinite(float(row["change_pct"]))
        ]
        complete = (
            bool(valid)
            and len(rows) == len(valid)
            and all(str(row.get("universe_total")) == str(len(valid)) for row in valid)
        )
        if self.data.is_mock and valid and len(valid) < limit:
            complete = True
        return valid, valid if complete else []

    def heatmap(
        self, level: str = "industry", board: str | None = None, threshold: float = 0.0
    ) -> list[dict[str, Any]]:
        return self.data.heatmap(level=level, board=board, threshold=threshold)

    def list_watchlist_groups(self) -> list[dict[str, Any]]:
        groups = self.repo.list("watchlist_group", order_by="sort_order ASC, id ASC")
        for group in groups:
            group["symbol_count"] = (
                self.repo.db.scalar("SELECT COUNT(*) AS cnt FROM watchlist WHERE group_id = ?", (group["id"],)) or 0
            )
        return groups

    def create_group(self, name: str, sort_order: int = 0) -> dict[str, Any]:
        now = utc_now_iso()
        return self.repo.insert(
            "watchlist_group", {"name": name, "sort_order": sort_order, "created_at": now, "updated_at": now}
        )

    def update_group(self, group_id: int, values: dict[str, Any]) -> dict[str, Any]:
        values["updated_at"] = utc_now_iso()
        return self.repo.update("watchlist_group", group_id, values)

    def delete_group(self, group_id: int, force: bool = False) -> None:
        count = self.repo.db.scalar("SELECT COUNT(*) AS cnt FROM watchlist WHERE group_id = ?", (group_id,)) or 0
        if count and not force:
            from src.core.exceptions import BusinessError, ErrorCode

            raise BusinessError(ErrorCode.NON_EMPTY_RESOURCE, "自选分组非空，无法删除")
        self.repo.delete("watchlist_group", group_id)

    def add_symbols(self, group_id: int, symbols: list[str]) -> dict[str, Any]:
        self.repo.get("watchlist_group", group_id)
        added = []
        now = utc_now_iso()
        for symbol in symbols:
            quote = self.data.stock_quote(symbol)
            symbol = quote.get("symbol", symbol)
            try:
                self.repo.insert(
                    "watchlist",
                    {
                        "group_id": group_id,
                        "symbol": symbol,
                        "market": quote.get("market", "CN"),
                        "name": quote.get("name", symbol),
                        "sort_order": 0,
                        "remark": "",
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                added.append(symbol)
            except Exception:
                continue
        return {
            "group_id": group_id,
            "symbol_count": self.repo.db.scalar(
                "SELECT COUNT(*) AS cnt FROM watchlist WHERE group_id = ?", (group_id,)
            ),
            "added": added,
        }

    def remove_symbol(self, group_id: int, symbol: str) -> None:
        self.repo.db.execute("DELETE FROM watchlist WHERE group_id = ? AND symbol = ?", (group_id, symbol))

    def watchlist_quotes(self, group_id: int | None = None) -> list[dict[str, Any]]:
        market_clause = "market IN ('CN', 'SH', 'SZ', 'BJ')" if self.data.market == "CN" else "market = ?"
        where = "group_id = ? AND " + market_clause if group_id else market_clause
        market_params = () if self.data.market == "CN" else (self.data.market,)
        params = (group_id, *market_params) if group_id else market_params
        items = self.repo.list("watchlist", where=where, params=params, order_by="group_id ASC, sort_order ASC, id ASC")
        quotes = self.data.stock_quotes([item["symbol"] for item in items])
        return [
            dict(quote, group_id=item["group_id"], remark=item.get("remark") or "")
            for item, quote in zip(items, quotes, strict=True)
        ]
