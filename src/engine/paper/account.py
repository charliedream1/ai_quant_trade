"""Paper account and order service."""

from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository
from src.core.timeutil import today_date, utc_now_iso
from src.data import DataSourceManager


class PaperAccountService:
    def __init__(self, repo: Repository | None = None, data: DataSourceManager | None = None) -> None:
        self.repo = repo or Repository()
        self.data = data or DataSourceManager()

    def list(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        result = self.repo.page("paper_accounts", page, page_size, order_by="id DESC")
        for item in result["items"]:
            item["account_id"] = item["id"]
        return result

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now_iso()
        cash = float(payload.get("initial_capital") or payload.get("initial_cash") or 1000000)
        row = self.repo.insert(
            "paper_accounts",
            {
                "name": payload["name"],
                "strategy_id": payload.get("strategy_id"),
                "initial_cash": cash,
                "current_cash": cash,
                "status": "运行中",
                "created_at": now,
                "updated_at": now,
            },
        )
        self._snapshot(row["id"])
        return self.get(row["id"])

    def get(self, account_id: int) -> dict[str, Any]:
        row = self.repo.get("paper_accounts", account_id)
        row["account_id"] = row["id"]
        return row

    def reset(self, account_id: int, initial_capital: float | None = None) -> dict[str, Any]:
        row = self.repo.get("paper_accounts", account_id)
        cash = float(initial_capital or row["initial_cash"])
        self.repo.db.execute("DELETE FROM paper_orders WHERE account_id = ?", (account_id,))
        self.repo.db.execute("DELETE FROM paper_positions WHERE account_id = ?", (account_id,))
        self.repo.db.execute("DELETE FROM paper_nav_history WHERE account_id = ?", (account_id,))
        self.repo.update(
            "paper_accounts", account_id, {"initial_cash": cash, "current_cash": cash, "updated_at": utc_now_iso()}
        )
        self._snapshot(account_id)
        return self.get(account_id)

    def overview(self, account_id: int) -> dict[str, Any]:
        account = self.get(account_id)
        positions = self.positions(account_id)
        market_value = sum(float(p["market_value"]) for p in positions)
        total_asset = float(account["current_cash"]) + market_value
        return {
            "account_id": account_id,
            "cash": account["current_cash"],
            "market_value": round(market_value, 2),
            "total_asset": round(total_asset, 2),
            "daily_pnl": 0.0,
            "total_pnl": round(total_asset - float(account["initial_cash"]), 2),
            "net_value": round(total_asset / float(account["initial_cash"]), 4),
            "position_count": len(positions),
            "status": account["status"],
        }

    def order(self, account_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        account = self.get(account_id)
        symbol = payload["symbol"]
        side = str(payload.get("side") or payload.get("direction") or "buy").lower()
        if side not in ("buy", "sell", "买", "卖"):
            raise BusinessError(ErrorCode.PAPER_ORDER_REJECTED, "委托方向非法")
        direction = "买" if side in ("buy", "买") else "卖"
        quantity = int(payload["quantity"])
        if quantity <= 0:
            raise BusinessError(ErrorCode.PAPER_ORDER_REJECTED, "委托数量必须大于 0")
        quote = self.data.stock_quote(symbol)
        if quote.get("is_stale"):
            raise BusinessError(
                ErrorCode.PAPER_ORDER_REJECTED,
                f"行情不可用于成交：{quote.get('stale_reason') or '报价未更新'}",
            )
        order_type = str(payload.get("order_type") or "market").lower()
        if order_type not in {"market", "limit", "市价", "限价"}:
            raise BusinessError(ErrorCode.PAPER_ORDER_REJECTED, "委托类型非法")
        is_market = order_type in {"market", "市价"}
        if not is_market and payload.get("price") in (None, "", 0):
            raise BusinessError(ErrorCode.PAPER_ORDER_REJECTED, "限价委托必须填写委托价格")
        raw_price = quote["latest_price"] if is_market else payload["price"]
        price = float(raw_price)
        if price <= 0:
            raise BusinessError(ErrorCode.PAPER_ORDER_REJECTED, "委托价格必须大于 0")
        amount = price * quantity
        fee = round(amount * 0.0003, 2)
        now = utc_now_iso()
        if direction == "买" and float(account["current_cash"]) < amount + fee:
            raise BusinessError(ErrorCode.PAPER_ORDER_REJECTED, "可用资金不足")
        if direction == "卖":
            position = self.repo.db.query_one(
                "SELECT * FROM paper_positions WHERE account_id = ? AND symbol = ?",
                (account_id, symbol),
            )
            if not position or int(position["available_qty"]) < quantity:
                raise BusinessError(ErrorCode.PAPER_ORDER_REJECTED, "可卖持仓不足")
        fill_now = is_market or _limit_crossed(direction, price, float(quote["latest_price"]))
        order = self.repo.insert(
            "paper_orders",
            {
                "account_id": account_id,
                "symbol": symbol,
                "market": quote.get("market", "CN"),
                "direction": direction,
                "order_type": "市价" if is_market else "限价",
                "price": price,
                "quantity": quantity,
                "filled_qty": 0,
                "avg_price": None,
                "status": "待撮合",
                "created_at": now,
                "updated_at": now,
            },
        )
        if fill_now:
            order = self._fill_order(account_id, order, quote.get("name", symbol), price, quantity, fee)
        else:
            self._snapshot(account_id)
        order["order_id"] = order["id"]
        order["accepted_status"] = "accepted"
        order["match_note"] = "已成交" if fill_now else "限价未触发，委托进入待撮合"
        return order

    def match_orders(self, account_id: int) -> dict[str, Any]:
        self.get(account_id)
        pending = self.repo.list(
            "paper_orders",
            where="account_id = ? AND status = ?",
            params=(account_id, "待撮合"),
            order_by="created_at ASC, id ASC",
            limit=100,
        )
        matched: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for order in pending:
            quote = self.data.stock_quote(order["symbol"])
            if quote.get("is_stale"):
                skipped.append({"order_id": order["id"], "reason": quote.get("stale_reason") or "行情未更新"})
                continue
            latest_price = float(quote["latest_price"])
            price = float(order["price"] or latest_price)
            if not _limit_crossed(str(order["direction"]), price, latest_price):
                skipped.append({"order_id": order["id"], "reason": "限价未触发"})
                continue
            quantity = int(order["quantity"]) - int(order.get("filled_qty") or 0)
            if quantity <= 0:
                continue
            amount = price * quantity
            fee = round(amount * 0.0003, 2)
            if str(order["direction"]) == "买" and float(self.get(account_id)["current_cash"]) < amount + fee:
                skipped.append({"order_id": order["id"], "reason": "可用资金不足"})
                continue
            if str(order["direction"]) == "卖":
                position = self.repo.db.query_one(
                    "SELECT * FROM paper_positions WHERE account_id = ? AND symbol = ?",
                    (account_id, order["symbol"]),
                )
                if not position or int(position["available_qty"]) < quantity:
                    skipped.append({"order_id": order["id"], "reason": "可卖持仓不足"})
                    continue
            filled = self._fill_order(account_id, order, quote.get("name", order["symbol"]), price, quantity, fee)
            matched.append(filled)
        self._snapshot(account_id)
        return {
            "account_id": account_id,
            "matched_count": len(matched),
            "pending_count": max(len(pending) - len(matched), 0),
            "matched_orders": [dict(item, order_id=item["id"]) for item in matched],
            "skipped": skipped,
        }

    def cancel(self, account_id: int, order_id: int) -> dict[str, Any]:
        order = self.repo.get("paper_orders", order_id)
        if order["account_id"] != account_id or order["status"] == "已成交":
            from src.core.exceptions import BusinessError, ErrorCode

            raise BusinessError(ErrorCode.ORDER_STATE_ERROR, "委托状态不允许撤单")
        row = self.repo.update("paper_orders", order_id, {"status": "已撤销", "updated_at": utc_now_iso()})
        return {"order_id": row["id"], "status": "cancelled"}

    def orders(
        self,
        account_id: int,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        where = "account_id = ?"
        params: list[Any] = [account_id]
        if status:
            where += " AND status = ?"
            params.append(status)
        result = self.repo.page("paper_orders", page, page_size, where, params, order_by="created_at DESC")
        for item in result["items"]:
            item["order_id"] = item["id"]
        return result

    def fills(
        self,
        account_id: int,
        symbol: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        where = "account_id = ?"
        params: list[Any] = [account_id]
        if symbol:
            where += " AND symbol = ?"
            params.append(symbol)
        return self.repo.page("paper_trades", page, page_size, where, params, order_by="traded_at DESC")

    def positions(self, account_id: int):
        rows = self.repo.list(
            "paper_positions", where="account_id = ? AND quantity > 0", params=(account_id,), order_by="symbol ASC"
        )
        for row in rows:
            quote = self.data.stock_quote(row["symbol"])
            row["latest_price"] = quote["latest_price"]
            row["market_value"] = round(float(quote["latest_price"]) * int(row["quantity"]), 2)
            row["float_pnl"] = round(row["market_value"] - float(row["avg_cost"]) * int(row["quantity"]), 2)
            row["float_pnl_pct"] = round(row["float_pnl"] / max(float(row["avg_cost"]) * int(row["quantity"]), 1), 4)
        return rows

    def equity_history(self, account_id: int):
        rows = self.repo.list(
            "paper_nav_history", where="account_id = ?", params=(account_id,), order_by="nav_date ASC"
        )
        return {
            "dates": [r["nav_date"] for r in rows],
            "net_values": [r["net_value"] for r in rows],
            "daily_returns": [r["daily_return"] or 0 for r in rows],
        }

    def snapshot(self, account_id: int) -> dict[str, Any]:
        self._snapshot(account_id)
        return self.overview(account_id)

    def _apply_fill(
        self,
        account_id: int,
        symbol: str,
        name: str,
        direction: str,
        price: float,
        quantity: int,
        fee: float,
    ) -> None:
        account = self.get(account_id)
        pos = self.repo.db.query_one(
            "SELECT * FROM paper_positions WHERE account_id = ? AND symbol = ?", (account_id, symbol)
        )
        amount = price * quantity
        now = utc_now_iso()
        if direction == "买":
            new_cash = float(account["current_cash"]) - amount - fee
            if pos:
                old_qty = int(pos["quantity"])
                new_qty = old_qty + quantity
                avg_cost = (float(pos["avg_cost"]) * old_qty + amount) / new_qty
                self.repo.update(
                    "paper_positions",
                    pos["id"],
                    {
                        "quantity": new_qty,
                        "available_qty": new_qty,
                        "avg_cost": avg_cost,
                        "market_value": price * new_qty,
                        "updated_at": now,
                    },
                )
            else:
                self.repo.insert(
                    "paper_positions",
                    {
                        "account_id": account_id,
                        "symbol": symbol,
                        "name": name,
                        "quantity": quantity,
                        "available_qty": quantity,
                        "avg_cost": price,
                        "market_value": amount,
                        "updated_at": now,
                    },
                )
        else:
            if pos is None:
                raise BusinessError(ErrorCode.PAPER_ORDER_REJECTED, "可卖持仓不足")
            new_cash = float(account["current_cash"]) + amount - fee
            new_qty = int(pos["quantity"]) - quantity
            self.repo.update(
                "paper_positions",
                pos["id"],
                {"quantity": new_qty, "available_qty": new_qty, "market_value": price * new_qty, "updated_at": now},
            )
        self.repo.update("paper_accounts", account_id, {"current_cash": new_cash, "updated_at": now})

    def _fill_order(
        self,
        account_id: int,
        order: dict[str, Any],
        name: str,
        price: float,
        quantity: int,
        fee: float,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        self.repo.insert(
            "paper_trades",
            {
                "account_id": account_id,
                "order_id": order["id"],
                "symbol": order["symbol"],
                "direction": order["direction"],
                "price": price,
                "quantity": quantity,
                "fee": fee,
                "traded_at": now,
            },
        )
        self._apply_fill(account_id, order["symbol"], name, order["direction"], price, quantity, fee)
        self._snapshot(account_id)
        return self.repo.update(
            "paper_orders",
            int(order["id"]),
            {
                "filled_qty": int(order.get("filled_qty") or 0) + quantity,
                "avg_price": price,
                "status": "已成交",
                "updated_at": now,
            },
        )

    def _snapshot(self, account_id: int) -> None:
        account = self.get(account_id)
        positions = self.positions(account_id)
        market_value = sum(float(p["market_value"]) for p in positions)
        total = float(account["current_cash"]) + market_value
        self.repo.db.execute(
            """INSERT OR REPLACE INTO paper_nav_history
               (account_id, nav_date, total_asset, cash, market_value, net_value, daily_return, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                account_id,
                today_date(),
                round(total, 2),
                account["current_cash"],
                round(market_value, 2),
                round(total / float(account["initial_cash"]), 4),
                0.0,
                utc_now_iso(),
            ),
        )


def _limit_crossed(direction: str, limit_price: float, latest_price: float) -> bool:
    if direction == "买":
        return limit_price >= latest_price
    return limit_price <= latest_price
