"""FIFO lots and unitized sleeve books; capital transfers do not manufacture returns."""

from copy import deepcopy
from typing import Any

from src.strategy.composition.config import config, fail


class SleeveBook:
    def __init__(self, capital: float, state: dict[str, Any] | None = None):
        self.state: dict[str, Any] = (
            deepcopy(state)
            if state
            else {"cash": capital, "units": capital, "lots": {}, "unit_history": [], "realized": 0.0}
        )

    @property
    def cash(self) -> float:
        return float(self.state["cash"])

    def quantity(self, symbol: str) -> int:
        return sum(lot["quantity"] for lot in self.state["lots"].get(symbol, []))

    def available(self, symbol: str, session: int) -> int:
        return sum(lot["quantity"] for lot in self.state["lots"].get(symbol, []) if lot["unlock_session"] <= session)

    def value(self, prices: dict[str, float]) -> float:
        return self.cash + sum(self.quantity(s) * prices[s] for s in self.state["lots"])

    def transfer_cash(self, new_cash: float, prices: dict[str, float]) -> float:
        before = self.value(prices)
        units = float(self.state["units"])
        unit_price = before / units if units > 0 and before > 0 else 1.0
        difference = new_cash - self.cash
        self.state["units"] = max(0.0, units + difference / unit_price)
        self.state["cash"] = float(new_cash)
        return difference

    def fill(
        self,
        symbol: str,
        signed_quantity: int,
        price: float,
        fee: float,
        session: int,
        settlement: int,
        day: str,
        scope: str,
        costs: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        if signed_quantity == 0:
            return []
        epsilon = config()["defaults"]["epsilon"]
        if price <= 0 or fee < 0:
            raise fail("invalid", "fill")
        lots = self.state["lots"].setdefault(symbol, [])
        costs = costs or {"commission": fee, "tax": 0, "transfer_fee": 0, "other_fee": 0, "total": fee}
        if signed_quantity > 0:
            cost = signed_quantity * price + fee
            if cost > self.cash + epsilon and scope != "internal":
                raise fail("invalid", "cash deficit")
            self.state["cash"] -= cost
            lots.append(
                {
                    "quantity": signed_quantity,
                    "cost": cost,
                    "price": price,
                    "open_date": day,
                    "open_session": session,
                    "unlock_session": session + settlement,
                    "open_costs": dict(costs),
                }
            )
            return []
        quantity = -signed_quantity
        if quantity > self.available(symbol, session):
            raise fail("invalid", "unsettled position")
        remaining = quantity
        closed = []
        for lot in list(lots):
            if remaining <= 0:
                break
            if lot["unlock_session"] > session:
                continue
            take = min(lot["quantity"], remaining)
            ratio = take / lot["quantity"]
            basis = lot["cost"] * ratio
            close_fee = fee * take / quantity
            profit = take * price - close_fee - basis
            closed.append(
                {
                    "symbol": symbol,
                    "quantity": take,
                    "open_price": lot["price"],
                    "close_price": price,
                    "open_time": lot["open_date"],
                    "close_time": day,
                    "pnl": profit,
                    "pnl_pct": profit / basis if basis else 0.0,
                    "commission": float(
                        lot.get("open_costs", {}).get("commission", lot["cost"] - lot["quantity"] * lot["price"])
                    )
                    * ratio
                    + costs["commission"] * take / quantity,
                    "costs": {
                        key: float(lot.get("open_costs", {}).get(key, 0)) * ratio + value * take / quantity
                        for key, value in costs.items()
                    },
                    "holding_days": session - lot["open_session"],
                    "scope": scope,
                }
            )
            lot["quantity"] -= take
            lot["cost"] -= basis
            lot["open_costs"] = {key: value * (1 - ratio) for key, value in lot.get("open_costs", {}).items()}
            self.state["realized"] += profit
            remaining -= take
            if not lot["quantity"]:
                lots.remove(lot)
        self.state["cash"] += quantity * price - fee
        if not lots:
            self.state["lots"].pop(symbol, None)
        return closed

    def finish(self, prices: dict[str, float]) -> float:
        units = float(self.state["units"])
        value = self.value(prices) / units if units > 0 else 1.0
        self.state["unit_history"].append(value)
        return value


class PortfolioBook:
    def __init__(
        self,
        capital: float,
        budgets: dict[str, float],
        state: dict[str, Any] | None = None,
        groups: dict[str, list[str]] | None = None,
    ):
        self.capital = capital
        self.session = int((state or {}).get("session", -1))
        self.last_day = str((state or {}).get("last_day", ""))
        self.prices = dict((state or {}).get("prices") or {})
        self.reserve = float((state or {}).get("reserve", capital * (1 - sum(budgets.values()))))
        self.sleeves = {
            key: SleeveBook(capital * weight, (state or {}).get("sleeves", {}).get(key))
            for key, weight in budgets.items()
        }
        self.members = groups or {key: [key] for key in budgets}
        self.groups = deepcopy(
            (state or {}).get("groups")
            or {
                key: {"units": capital * sum(budgets[k] for k in members), "unit_history": []}
                for key, members in self.members.items()
            }
        )

    def advance(self, day: str) -> None:
        if day <= self.last_day:
            raise fail("lookahead", day)
        self.session += 1
        self.last_day = day

    def positions(self) -> dict[str, int]:
        names = {name for book in self.sleeves.values() for name in book.state["lots"]}
        return {s: sum(book.quantity(s) for book in self.sleeves.values()) for s in sorted(names)}

    def cash(self) -> float:
        return self.reserve + sum(book.cash for book in self.sleeves.values())

    def nav(self) -> float:
        return self.cash() + sum(q * self.prices[s] for s, q in self.positions().items())

    def snapshot(self) -> dict[str, Any]:
        nav = self.nav()
        return {
            "cash": self.cash(),
            "nav": nav,
            "session": self.session,
            "positions": self.positions(),
            "weights": {s: q * self.prices[s] / nav for s, q in self.positions().items()} if nav > 0 else {},
            "sleeves": {
                key: {
                    "nav": book.value(self.prices),
                    "cash": book.cash,
                    "positions": {s: book.quantity(s) for s in book.state["lots"]},
                }
                for key, book in self.sleeves.items()
            },
        }

    def rebudget_cash(
        self, budgets: dict[str, float], requested: dict[str, float] | None = None
    ) -> list[dict[str, Any]]:
        group_before = {
            key: sum(self.sleeves[k].value(self.prices) for k in members) for key, members in self.members.items()
        }
        nav = self.nav()
        available = self.cash()
        demands = {
            key: max(0.0, nav * budgets[key] - sum(book.quantity(s) * self.prices[s] for s in book.state["lots"]))
            for key, book in self.sleeves.items()
        }
        if requested is not None:
            demands = {key: max(0.0, float(requested.get(key, 0))) for key in self.sleeves}
        reserve = max(0.0, nav * (1 - sum(budgets.values())))
        investable = max(0.0, available - reserve)
        total = sum(demands.values())
        factor = min(1.0, investable / total) if total else 0.0
        flows = []
        for key, book in self.sleeves.items():
            difference = book.transfer_cash(demands[key] * factor, self.prices)
            if difference:
                flows.append({"sleeve": key, "capital_flow": difference})
        self.reserve = available - sum(book.cash for book in self.sleeves.values())
        for key, members in self.members.items():
            after = sum(self.sleeves[k].value(self.prices) for k in members)
            units = self.groups[key]["units"]
            unit_price = group_before[key] / units if units > 0 and group_before[key] > 0 else 1.0
            self.groups[key]["units"] = max(0.0, units + (after - group_before[key]) / unit_price)
        return flows

    def serialize(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "last_day": self.last_day,
            "prices": self.prices,
            "reserve": self.reserve,
            "sleeves": {key: deepcopy(book.state) for key, book in self.sleeves.items()},
            "groups": deepcopy(self.groups),
        }

    def finish(self) -> dict[str, float]:
        for sleeve in self.sleeves.values():
            sleeve.finish(self.prices)
        result = {}
        for key, members in self.members.items():
            nav = sum(self.sleeves[k].value(self.prices) for k in members)
            units = self.groups[key]["units"]
            value = nav / units if units > 0 else 1.0
            self.groups[key]["unit_history"].append(value)
            result[key] = value
        return result


class GroupView:
    """Risk view over actual leaf books, with performance corrected for budget transfers."""

    def __init__(self, book: PortfolioBook, key: str, capital: float):
        self.book, self.key, self.capital = book, key, capital
        self.sleeves = {k: book.sleeves[k] for k in book.members[key]}
        self.session = book.session
        self.prices = book.prices

    def positions(self) -> dict[str, int]:
        names = {s for b in self.sleeves.values() for s in b.state["lots"]}
        return {s: sum(b.quantity(s) for b in self.sleeves.values()) for s in names}

    def nav(self) -> float:
        return sum(b.value(self.prices) for b in self.sleeves.values())

    def snapshot(self) -> dict[str, Any]:
        nav = self.nav()
        units = self.book.groups[self.key]["units"]
        return {
            "nav": nav,
            "performance_nav": nav / units * self.capital if units > 0 else self.capital,
            "cash": sum(b.cash for b in self.sleeves.values()),
            "positions": self.positions(),
            "weights": {s: q * self.prices[s] / nav for s, q in self.positions().items()} if nav > 0 else {},
            "session": self.session,
        }
