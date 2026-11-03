"""One valuation snapshot shared by homepage KPIs, plots and holding details."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any

from src.core.logger import get_logger
from src.core.repository import Repository
from src.data import DataSourceManager

from .foundation import _daily_cached, _local_now
from .home_config import label

LOG = get_logger("frontend.home")


def number(value: Any) -> float | None:
    try:
        result = float(str(value).replace(",", "").removesuffix("%"))
        return result if isfinite(result) else None
    except (TypeError, ValueError):
        return None


@dataclass
class HomeAccount:
    mode: str
    account: dict[str, Any] = field(default_factory=dict)
    holdings: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    pending: int = 0
    cash: float | None = None
    total_asset: float | None = None
    total_pnl: float | None = None
    daily_pnl: float | None = None
    drawdown: float | None = None
    exposure: float | None = None
    concentration: float | None = None
    position_count: int | None = None
    profit_count: int | None = None
    loss_count: int | None = None
    flat_count: int | None = None
    unknown_count: int | None = None
    basis: str = ""
    warnings: list[str] = field(default_factory=list)
    valued_at: str = ""


def account_snapshot(mode: str, force_refresh: bool = False) -> HomeAccount:
    payload, _, _ = _daily_cached(
        ("home_account_snapshot", mode), lambda: _read_account(mode), force_refresh=force_refresh
    )
    return payload


def _read_account(mode: str) -> HomeAccount:
    repo = Repository()
    snapshot = HomeAccount(
        mode=mode,
        basis=label("paper_basis" if mode == "paper" else "live_basis"),
        valued_at=_local_now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    if mode != "paper":
        # The current live adapter reports configured capital and a CASH placeholder, not broker assets.
        snapshot.account = (
            repo.db.query_one("SELECT * FROM live_configs ORDER BY updated_at DESC, id DESC LIMIT 1") or {}
        )
        return snapshot
    snapshot.account = repo.db.query_one("SELECT * FROM paper_accounts ORDER BY updated_at DESC, id DESC LIMIT 1") or {}
    if not snapshot.account:
        snapshot.basis = label("empty_account")
        return snapshot
    account_id = int(snapshot.account["id"])
    positions = repo.list("paper_positions", "account_id = ? AND quantity > 0", (account_id,), "symbol ASC")
    markets = {"CN" if str(row["symbol"]).isdigit() else "US" for row in positions}
    manager = DataSourceManager(market=next(iter(markets)) if len(markets) == 1 else None)
    for position in positions:
        snapshot.holdings.append(_value_holding(position, manager, snapshot.warnings))
    pnl_values = [number(row.get("float_pnl")) for row in snapshot.holdings]
    snapshot.position_count = len(snapshot.holdings)
    snapshot.profit_count = sum(1 for value in pnl_values if value is not None and value > 0)
    snapshot.loss_count = sum(1 for value in pnl_values if value is not None and value < 0)
    snapshot.flat_count = sum(1 for value in pnl_values if value == 0)
    snapshot.unknown_count = sum(1 for value in pnl_values if value is None)
    snapshot.cash = number(snapshot.account.get("current_cash"))
    valid = all(row["market_value"] is not None for row in snapshot.holdings)
    if len(markets) > 1:
        valid = False
        snapshot.warnings.append("跨市场持仓尚无币种换算，总资产不作加总")
    if snapshot.cash is not None and valid:
        market_value = sum(float(row["market_value"]) for row in snapshot.holdings)
        snapshot.total_asset = snapshot.cash + market_value
        initial = number(snapshot.account.get("initial_cash"))
        snapshot.total_pnl = snapshot.total_asset - initial if initial is not None else None
        if snapshot.total_asset > 0:
            snapshot.exposure = market_value / snapshot.total_asset
            snapshot.concentration = (
                max((float(row["market_value"]) for row in snapshot.holdings), default=0) / snapshot.total_asset
            )
    snapshot.history = repo.list("paper_nav_history", "account_id = ?", (account_id,), "nav_date ASC")
    _history_metrics(snapshot)
    snapshot.pending = int(
        repo.db.scalar(
            "SELECT COUNT(*) FROM paper_orders WHERE account_id = ? AND status NOT IN ('已成交', '已撤销')",
            (account_id,),
        )
        or 0
    )
    return snapshot


def _value_holding(position: dict[str, Any], manager: DataSourceManager, warnings: list[str]) -> dict[str, Any]:
    symbol = str(position["symbol"])
    quote: dict[str, Any] = {}
    try:
        quote = manager.stock_quote(symbol)
    except Exception as exc:
        LOG.warning("home holding quote unavailable | symbol={} error={}", symbol, exc)
        warnings.append(f"{symbol} 行情不可用，估值缺失")
    price = number(quote.get("latest_price"))
    if price is not None and price <= 0:
        price = None
    if quote.get("is_stale"):
        warnings.append(f"{symbol} 使用滞后行情")
    quantity = number(position.get("quantity"))
    cost = number(position.get("avg_cost"))
    value = price * quantity if price is not None and quantity is not None else None
    pnl = value - cost * quantity if value is not None and cost is not None and quantity is not None else None
    return {
        "symbol": symbol,
        "name": quote.get("name") or position.get("name") or symbol,
        "quantity": quantity,
        "available_qty": position.get("available_qty"),
        "latest_price": price,
        "change_pct": number(quote.get("change_pct")),
        "market_value": value,
        "float_pnl": pnl,
        "float_pnl_pct": pnl / (cost * quantity) * 100 if pnl is not None and cost and quantity else None,
        "data_source": quote.get("data_source") or "行情不可用",
        "updated_at": quote.get("updated_at") or quote.get("timestamp") or "未提供",
    }


def _history_metrics(snapshot: HomeAccount) -> None:
    history = [
        row for row in snapshot.history if number(row.get("net_value")) is not None and float(row["net_value"]) > 0
    ]
    if not history:
        return
    values = [float(row["net_value"]) for row in history]
    snapshot.drawdown = values[-1] / max(values) - 1
    initial = number(snapshot.account.get("initial_cash"))
    today = _local_now().date().isoformat()
    if len(history) >= 2 and str(history[-1]["nav_date"])[:10] == today and initial is not None:
        snapshot.daily_pnl = (values[-1] - values[-2]) * initial
