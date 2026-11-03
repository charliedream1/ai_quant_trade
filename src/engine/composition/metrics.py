"""Account NAV metrics, distinct from virtual sleeve transfer statistics."""

from typing import Any

import numpy as np

from src.strategy.composition.config import config


def performance(curve: dict[str, list], orders: list[dict], trades: list[dict], initial: float) -> dict[str, Any]:
    equity = np.asarray(curve["equity"], dtype=float)
    periods = config()["defaults"]["annual_periods"]
    prior = np.concatenate(([initial], equity[:-1]))
    returns = equity / prior - 1
    std = float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0
    benchmark = np.asarray(curve["benchmark"], dtype=float)
    positive = [row["pnl"] for row in trades if row["pnl"] > 0]
    negative = [row["pnl"] for row in trades if row["pnl"] < 0]
    filled = [row for row in orders if row.get("quantity", 0) > 0]
    closed = len(trades)
    return {
        "total_return": float(equity[-1] / initial - 1) if len(equity) else 0.0,
        "annual_return": float((equity[-1] / initial) ** (periods / len(equity)) - 1)
        if len(equity) and equity[-1] > 0
        else 0.0,
        "max_drawdown": float(min(curve["drawdown"])) if curve["drawdown"] else 0.0,
        "sharpe_ratio": float(np.mean(returns) / std * np.sqrt(periods)) if std else 0.0,
        "annual_volatility": std * periods**0.5,
        "trade_count": len(filled),
        "order_count": len(orders),
        "closed_lot_count": closed,
        "win_rate": len(positive) / closed if closed else 0.0,
        "total_pnl": float(equity[-1] - initial) if len(equity) else 0.0,
        "total_commission": sum(float(row.get("commission", 0)) for row in orders),
        "turnover_rate": sum(float(row.get("quantity", 0)) * float(row.get("price", 0)) for row in orders) / initial,
        "profit_factor": sum(positive) / -sum(negative) if negative else None,
        "benchmark_return": float(benchmark[-1] / initial - 1) if len(benchmark) else 0.0,
        "benchmark_label": "固定股票池等权价格基准（不含成本与分红）",
        "engine_mode": "composition_batch",
        "closed_statistics_scope": "sleeve_market_fills",
        "insufficient_returns": len(returns) < 2,
    }
