"""Typing contracts for deliberate cross-domain frontend workflows."""

from __future__ import annotations

from typing import Any, Protocol

import pandas as pd
import plotly.graph_objects as go


class CrossDomainCallbacks(Protocol):
    """Callbacks intentionally reused by more than one frontend domain."""

    def create_backtest(
        self,
        strategy_id: Any,
        symbols: str,
        start_date: str,
        end_date: str,
        capital: Any,
        params: str,
        engine: str = "auto",
        order_type: str = "market",
        price_adjustment: str = "qfq",
        max_position_count: Any = 5,
        max_position_weight: Any = 0.3,
        lot_size: Any = 100,
        slippage_rate: Any = 0.0,
        parameter_profile: str = "",
        execution_costs: dict[str, Any] | None = None,
    ) -> tuple[str, int, pd.DataFrame, pd.DataFrame, go.Figure, pd.DataFrame, go.Figure, pd.DataFrame]: ...

    def create_note(self, title: str, category_id: Any, tags: str, content: str) -> tuple[str, pd.DataFrame]: ...

    def mcp_servers(self) -> pd.DataFrame: ...

    def skills(self) -> pd.DataFrame: ...
