"""Stock detail analyzer."""

from typing import Any

from src.data import DataSourceManager


class StockAnalyzer:
    def __init__(self, data: DataSourceManager | None = None) -> None:
        self.data = data or DataSourceManager()

    def detail(
        self, symbol: str, sections: str = "", kline_period: str = "daily", kline_count: int = 60
    ) -> dict[str, Any]:
        return self.data.stock_detail(
            symbol=symbol,
            kline_count=kline_count,
            kline_period=kline_period,
        )
