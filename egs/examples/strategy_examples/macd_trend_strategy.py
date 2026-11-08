"""MACD line crossover trend-following example."""

from src.strategy.strategy_base import StrategyBase


class MACDTrendStrategy(StrategyBase):
    name = "MACDTrendStrategy"
    version = "v1"
    description = "Trade MACD DIF/DEA crossovers."
    params_schema = [
        {"name": "fast_window", "type": "int", "default": 12, "min": 2, "max": 60},
        {"name": "slow_window", "type": "int", "default": 26, "min": 5, "max": 120},
        {"name": "signal_window", "type": "int", "default": 9, "min": 2, "max": 60},
        {"name": "quantity", "type": "int", "default": 100, "min": 1, "max": 100000},
    ]

    def on_start(self, context):
        self.params = context.get("params") or self.params
        self._closes = {}
        self._previous = {}

    def on_bar(self, bar):
        symbol = str(bar.get("symbol") or "")
        close = float(bar.get("close") or 0)
        params = self.params or {}
        fast_window = max(2, int(params.get("fast_window", 12)))
        slow_window = max(fast_window + 1, int(params.get("slow_window", 26)))
        signal_window = max(2, int(params.get("signal_window", 9)))
        closes = self._closes.setdefault(symbol, [])
        closes.append(close)
        if len(closes) < slow_window + signal_window:
            return []
        fast = sum(closes[-fast_window:]) / fast_window
        slow = sum(closes[-slow_window:]) / slow_window
        dif = fast - slow
        dea_values = []
        for index in range(signal_window):
            end = len(closes) - index
            fast_value = sum(closes[max(0, end - fast_window) : end]) / min(fast_window, end)
            slow_value = sum(closes[max(0, end - slow_window) : end]) / min(slow_window, end)
            dea_values.append(fast_value - slow_value)
        dea = sum(dea_values) / len(dea_values)
        relation = 1 if dif > dea else -1
        previous = self._previous.get(symbol, relation)
        self._previous[symbol] = relation
        quantity = int(params.get("quantity", 100))
        if previous <= 0 < relation:
            return [{"symbol": symbol, "side": "buy", "quantity": quantity, "reason": "macd_golden_cross"}]
        if previous >= 0 > relation:
            return [{"symbol": symbol, "side": "sell", "quantity": 0, "reason": "macd_death_cross"}]
        return []
