"""RSI oversold/overbought mean-reversion example."""

from src.strategy.strategy_base import StrategyBase


class RSIMeanReversionStrategy(StrategyBase):
    name = "RSIMeanReversionStrategy"
    version = "v1"
    description = "Buy oversold RSI and exit overbought positions."
    params_schema = [
        {"name": "rsi_window", "type": "int", "default": 14, "min": 2, "max": 60},
        {"name": "oversold", "type": "float", "default": 30.0, "min": 1.0, "max": 49.0},
        {"name": "overbought", "type": "float", "default": 70.0, "min": 51.0, "max": 99.0},
        {"name": "quantity", "type": "int", "default": 100, "min": 1, "max": 100000},
    ]

    def on_start(self, context):
        self.params = context.get("params") or self.params
        self._closes = {}

    def on_bar(self, bar):
        symbol = str(bar.get("symbol") or "")
        close = float(bar.get("close") or 0)
        params = self.params or {}
        window = max(2, int(params.get("rsi_window", 14)))
        closes = self._closes.setdefault(symbol, [])
        closes.append(close)
        if len(closes) <= window:
            return []
        changes = [closes[index] - closes[index - 1] for index in range(len(closes) - window, len(closes))]
        gains = sum(max(change, 0.0) for change in changes) / window
        losses = sum(max(-change, 0.0) for change in changes) / window
        rsi = 100.0 if losses == 0 else 100.0 - 100.0 / (1.0 + gains / losses)
        quantity = int(params.get("quantity", 100))
        if rsi <= float(params.get("oversold", 30.0)):
            return [{"symbol": symbol, "side": "buy", "quantity": quantity, "reason": "rsi_oversold"}]
        if rsi >= float(params.get("overbought", 70.0)):
            return [{"symbol": symbol, "side": "sell", "quantity": 0, "reason": "rsi_overbought"}]
        return []
