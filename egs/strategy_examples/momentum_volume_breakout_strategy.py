"""Price and volume breakout example."""

from src.strategy.strategy_base import StrategyBase


class MomentumVolumeBreakoutStrategy(StrategyBase):
    name = "MomentumVolumeBreakoutStrategy"
    version = "v1"
    description = "Buy price highs confirmed by expanding volume and exit on a short reversal."
    params_schema = [
        {"name": "lookback", "type": "int", "default": 20, "min": 5, "max": 120},
        {"name": "volume_multiplier", "type": "float", "default": 1.2, "min": 0.5, "max": 5.0},
        {"name": "quantity", "type": "int", "default": 100, "min": 1, "max": 100000},
    ]

    def on_start(self, context):
        self.params = context.get("params") or self.params
        self._bars = {}

    def on_bar(self, bar):
        symbol = str(bar.get("symbol") or "")
        close = float(bar.get("close") or 0)
        volume = float(bar.get("volume") or 0)
        params = self.params or {}
        lookback = max(5, int(params.get("lookback", 20)))
        bars = self._bars.setdefault(symbol, [])
        bars.append((close, volume))
        if len(bars) <= lookback:
            return []
        previous = bars[-lookback - 1 : -1]
        high = max(item[0] for item in previous)
        average_volume = sum(item[1] for item in previous) / lookback
        quantity = int(params.get("quantity", 100))
        if close > high and volume >= average_volume * float(params.get("volume_multiplier", 1.2)):
            return [{"symbol": symbol, "side": "buy", "quantity": quantity, "reason": "volume_breakout"}]
        if close < sum(item[0] for item in bars[-5:]) / min(5, len(bars)):
            return [{"symbol": symbol, "side": "sell", "quantity": 0, "reason": "short_reversal"}]
        return []
