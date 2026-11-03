"""Delayed ETF trend allocation with a configurable moving-average filter."""

from src.strategy.strategy_base import StrategyBase


class ETFTrendAllocationStrategy(StrategyBase):
    name = "ETFTrendAllocationStrategy"
    version = "v1"
    description = "Allocate to ETFs whose delayed close is above its trend filter."
    params_schema = [
        {"name": "universe", "type": "str", "default": "cn_core"},
        {"name": "window", "type": "int", "default": 60, "min": 20, "max": 240},
        {"name": "min_trend_gap", "type": "float", "default": 0.0, "min": -0.5, "max": 0.5},
        {"name": "rebalance_days", "type": "int", "default": 20, "min": 5, "max": 60},
        {"name": "quantity", "type": "int", "default": 100, "min": 1, "max": 100000},
    ]

    def on_start(self, context):
        self.params = context.get("params") or self.params
        self._closes = {}
        self._decisions = {}
        self._day = ""
        self._cycles = 0
        context.setdefault("metadata", {})["asset_type"] = "etf"
        context["metadata"]["etf_strategy"] = "delayed_trend_allocation"

    def on_bar(self, bar):
        day = str(bar.get("timestamp") or bar.get("date") or "")[:10]
        if self._day and day < self._day:
            raise ValueError("ETF 趋势策略要求行情按日期递增")
        if day != self._day:
            self._prepare(day)
            self._day = day
        symbol = str(bar.get("symbol") or "")
        close = float(bar.get("close") or 0)
        if not symbol or close <= 0:
            return []
        self._closes.setdefault(symbol, []).append(close)
        decision = self._decisions.get(symbol)
        if not decision or decision["forecast_date"] >= day:
            return []
        return [
            {
                "symbol": symbol,
                "side": decision["side"],
                "quantity": int(self.params.get("quantity", 100)) if decision["side"] == "buy" else 0,
                "reason": f"etf_trend:{decision['gap']:.4f}:{decision['forecast_date']}",
                "metadata": {"asset_type": "etf", "trend_gap": decision["gap"]},
            }
        ]

    def _prepare(self, day):
        self._decisions = {}
        self._cycles += 1
        if self._cycles % max(1, int(self.params.get("rebalance_days", 20))) != 0:
            return
        forecast_date = self._day
        if not forecast_date:
            return
        window = max(2, int(self.params.get("window", 60)))
        threshold = float(self.params.get("min_trend_gap", 0.0))
        for symbol, values in self._closes.items():
            if len(values) <= window:
                continue
            moving_average = sum(values[-window - 1 : -1]) / window
            gap = values[-1] / moving_average - 1 if moving_average else 0.0
            self._decisions[symbol] = {
                "side": "buy" if gap >= threshold else "sell",
                "gap": float(gap),
                "forecast_date": forecast_date,
            }
