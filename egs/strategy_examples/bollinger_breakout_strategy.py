"""Bollinger-band breakout example."""

from src.strategy.strategy_base import StrategyBase


class BollingerBreakoutStrategy(StrategyBase):
    name = "BollingerBreakoutStrategy"
    version = "v1"
    description = "Buy an upper-band breakout and exit below the middle band."
    params_schema = [
        {"name": "window", "type": "int", "default": 20, "min": 5, "max": 120},
        {"name": "deviation", "type": "float", "default": 2.0, "min": 0.5, "max": 4.0},
        {"name": "quantity", "type": "int", "default": 100, "min": 1, "max": 100000},
    ]

    def on_start(self, context):
        self.params = context.get("params") or self.params
        self._closes = {}

    def on_bar(self, bar):
        symbol = str(bar.get("symbol") or "")
        close = float(bar.get("close") or 0)
        params = self.params or {}
        window = max(5, int(params.get("window", 20)))
        closes = self._closes.setdefault(symbol, [])
        closes.append(close)
        if len(closes) < window:
            return []
        sample = closes[-window:]
        mean = sum(sample) / window
        variance = sum((value - mean) ** 2 for value in sample) / window
        deviation = float(params.get("deviation", 2.0)) * variance**0.5
        quantity = int(params.get("quantity", 100))
        if close > mean + deviation:
            return [{"symbol": symbol, "side": "buy", "quantity": quantity, "reason": "bollinger_breakout"}]
        if close < mean:
            return [{"symbol": symbol, "side": "sell", "quantity": 0, "reason": "bollinger_midline_exit"}]
        return []
