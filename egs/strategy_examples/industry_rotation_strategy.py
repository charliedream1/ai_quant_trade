"""Relative-strength rotation proxy for an industry basket."""

from src.strategy.strategy_base import StrategyBase


class IndustryRotationStrategy(StrategyBase):
    name = "IndustryRotationStrategy"
    version = "v1"
    description = "Rotate toward the strongest symbols in a configured industry proxy basket."
    params_schema = [
        {"name": "lookback", "type": "int", "default": 20, "min": 5, "max": 120},
        {"name": "top_n", "type": "int", "default": 1, "min": 1, "max": 5},
        {"name": "quantity", "type": "int", "default": 100, "min": 1, "max": 100000},
    ]

    def on_start(self, context):
        self.params = context.get("params") or self.params
        self._closes = {}

    def on_bar(self, bar):
        symbol = str(bar.get("symbol") or "")
        close = float(bar.get("close") or 0)
        params = self.params or {}
        lookback = max(5, int(params.get("lookback", 20)))
        closes = self._closes.setdefault(symbol, [])
        closes.append(close)
        if len(closes) < lookback + 1:
            return []
        scores = {
            item_symbol: values[-1] / values[-lookback - 1] - 1
            for item_symbol, values in self._closes.items()
            if len(values) >= lookback + 1 and values[-lookback - 1] > 0
        }
        if symbol not in scores:
            return []
        top_n = max(1, int(params.get("top_n", 1)))
        leaders = {key for key, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_n]}
        quantity = int(params.get("quantity", 100))
        if symbol in leaders:
            return [{"symbol": symbol, "side": "buy", "quantity": quantity, "reason": "relative_strength_leader"}]
        return [{"symbol": symbol, "side": "sell", "quantity": 0, "reason": "relative_strength_rotation"}]
