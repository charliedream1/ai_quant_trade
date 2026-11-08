"""Delayed ETF relative-strength rotation for a configured ETF universe."""

from src.strategy.strategy_base import StrategyBase


class ETFMomentumRotationStrategy(StrategyBase):
    name = "ETFMomentumRotationStrategy"
    version = "v1"
    description = "Rotate into the strongest ETFs at a delayed rebalance date."
    params_schema = [
        {"name": "universe", "type": "str", "default": "cn_core"},
        {"name": "lookback", "type": "int", "default": 60, "min": 20, "max": 240},
        {"name": "top_n", "type": "int", "default": 1, "min": 1, "max": 10},
        {"name": "rebalance_days", "type": "int", "default": 20, "min": 5, "max": 60},
        {"name": "min_score", "type": "float", "default": 0.0, "min": -1.0, "max": 2.0},
        {"name": "quantity", "type": "int", "default": 100, "min": 1, "max": 100000},
    ]

    def on_start(self, context):
        self.params = context.get("params") or self.params
        self._closes = {}
        self._decisions = {}
        self._day = ""
        self._cycles = 0
        context.setdefault("metadata", {})["asset_type"] = "etf"
        context["metadata"]["etf_strategy"] = "delayed_relative_strength_rotation"

    def on_bar(self, bar):
        day = str(bar.get("timestamp") or bar.get("date") or "")[:10]
        if self._day and day < self._day:
            raise ValueError("ETF 轮动策略要求行情按日期递增")
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
                "reason": f"etf_rotation:{decision['score']:.4f}:{decision['forecast_date']}",
                "metadata": {"asset_type": "etf", "score": decision["score"]},
            }
        ]

    def _prepare(self, day):
        self._decisions = {}
        self._cycles += 1
        rebalance = max(1, int(self.params.get("rebalance_days", 20)))
        if self._cycles % rebalance != 0:
            return
        forecast_date = self._day
        if not forecast_date:
            return
        lookback = max(2, int(self.params.get("lookback", 60)))
        scores = {
            symbol: values[-1] / values[-lookback - 1] - 1
            for symbol, values in self._closes.items()
            if len(values) > lookback and values[-lookback - 1] > 0
        }
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        leaders = {
            symbol
            for symbol, score in ranked[: int(self.params.get("top_n", 1))]
            if score >= float(self.params.get("min_score", 0.0))
        }
        for symbol, score in scores.items():
            self._decisions[symbol] = {
                "side": "buy" if symbol in leaders else "sell",
                "score": float(score),
                "forecast_date": forecast_date,
            }
