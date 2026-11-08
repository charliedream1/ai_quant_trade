from src.strategy.strategy_base import StrategyBase


class DualMovingAverageStrategy(StrategyBase):
    name = "DualMovingAverageStrategy"
    version = "v1"
    description = "Example strategy that emits a buy signal when close is above open."
    params_schema = [
        {"name": "fast_window", "type": "int", "default": 5, "min": 2, "max": 60},
        {"name": "slow_window", "type": "int", "default": 20, "min": 5, "max": 240},
    ]

    def on_start(self, context):
        self.params = context.get("params") or self.params
        self._closes = {}
        self._previous_relation = {}

    def on_bar(self, bar):
        symbol = str(bar.get("symbol") or "")
        close = float(bar.get("close") or 0)
        if not symbol or close <= 0:
            return []
        closes = self._closes.setdefault(symbol, [])
        closes.append(close)
        params = self.params or {}
        fast_window = max(2, int(params.get("fast_window", 5)))
        slow_window = max(fast_window + 1, int(params.get("slow_window", 20)))
        if len(closes) < slow_window:
            return []
        fast = sum(closes[-fast_window:]) / fast_window
        slow = sum(closes[-slow_window:]) / slow_window
        relation = 1 if fast > slow else -1
        previous = self._previous_relation.get(symbol, -1)
        self._previous_relation[symbol] = relation
        if previous <= 0 < relation:
            return [{"symbol": symbol, "side": "buy", "quantity": 100, "reason": "golden_cross"}]
        if previous >= 0 > relation:
            return [{"symbol": symbol, "side": "sell", "quantity": 0, "reason": "death_cross"}]
        return []
