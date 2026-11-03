"""Market quote aggregation."""

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

    def sectors(self, board: str = "industry", sort: str = "涨跌幅", limit: int = 20) -> list[dict[str, Any]]:
        items = self.data.sectors(board=board, limit=limit)
        return sorted(items, key=lambda row: row["change_pct"], reverse=True)

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
        where = "group_id = ?" if group_id else ""
        params = (group_id,) if group_id else ()
        items = self.repo.list("watchlist", where=where, params=params, order_by="group_id ASC, sort_order ASC, id ASC")
        quotes = self.data.stock_quotes([item["symbol"] for item in items])
        return [
            dict(quote, group_id=item["group_id"], remark=item.get("remark") or "")
            for item, quote in zip(items, quotes, strict=True)
        ]
