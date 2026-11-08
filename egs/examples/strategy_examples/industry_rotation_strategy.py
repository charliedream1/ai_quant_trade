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
        self._day = ""
        self._decisions = {}
        self._seen = {}

    def on_bar(self, bar):
        day = str(bar.get("timestamp") or bar.get("date") or "")[:10]
        if not day or self._day and day < self._day:
            raise ValueError("Industry rotation requires monotonically increasing dated bars")
        if day != self._day:
            self._prepare()
            self._day = day
        symbol = str(bar.get("symbol") or "")
        close = float(bar.get("close") or 0)
        if not symbol or close <= 0:
            return []
        if self._seen.get(symbol) == day:
            return []
        self._seen[symbol] = day
        self._closes.setdefault(symbol, []).append(close)
        side = self._decisions.get(symbol)
        if side is None:
            return []
        return [
            {
                "symbol": symbol,
                "side": side,
                "quantity": int(self.params.get("quantity", 100)) if side == "buy" else 0,
                "reason": "delayed_industry_relative_strength",
            }
        ]

    def _prepare(self):
        params = self.params or {}
        lookback = max(5, int(params.get("lookback", 20)))
        scores = {
            item_symbol: values[-1] / values[-lookback - 1] - 1
            for item_symbol, values in self._closes.items()
            if len(values) >= lookback + 1 and values[-lookback - 1] > 0 and self._seen.get(item_symbol) == self._day
        }
        top_n = max(1, int(params.get("top_n", 1)))
        leaders = {key for key, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_n]}
        self._decisions = {symbol: "buy" if symbol in leaders else "sell" for symbol in scores}
