class StandardPortMomentumStrategy:
    name = "StandardPortMomentumStrategy"
    version = "v1"
    description = "Standard class-port strategy example."
    params_schema = [
        {"name": "min_change_pct", "type": "float", "default": 0.01, "min": 0.0, "max": 0.2},
        {"name": "quantity", "type": "int", "default": 100, "min": 1, "max": 100000},
    ]

    def __init__(self, params=None):
        self.params = params or {}
        self.last_signal = ""

    def on_start(self, context):
        self.last_signal = f"mode={context.get('mode', 'unknown')}"

    def handle_bar(self, bar, context):
        params = context.get("params") or self.params
        min_change_pct = float(params.get("min_change_pct", 0.01))
        quantity = int(params.get("quantity", 100))
        open_price = float(bar.get("open") or 0)
        close_price = float(bar.get("close") or 0)
        if open_price <= 0:
            return []
        change_pct = close_price / open_price - 1
        if change_pct >= min_change_pct:
            self.last_signal = "breakout"
            return [
                {
                    "symbol": bar.get("symbol"),
                    "side": "buy",
                    "quantity": quantity,
                    "reason": "momentum_breakout",
                }
            ]
        return []

    def on_stop(self, context):
        self.last_signal = "stopped"
